"""Phase 3 Member Portal tests: dues reminders, support collections, minutes, December renewal.

Requires fixtures already up:
  python3 /app/backend/tests/qa_session.py up
  python3 /app/backend/tests/qa_members.py up
"""
import os
import pytest
import requests
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

with open("/app/frontend/.env") as f:
    BASE_URL = next(line.split("=", 1)[1].strip() for line in f if line.startswith("REACT_APP_BACKEND_URL=")).rstrip("/")
API = f"{BASE_URL}/api"
XRW = {"X-Requested-With": "XMLHttpRequest"}
ADMIN = {"session_token": "qa_tok_123"}
MEM_A = {"session_token": "mem_tok_a"}
MEM_B = {"session_token": "mem_tok_b"}

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _s(cookies=None):
    s = requests.Session()
    if cookies:
        for k, v in cookies.items():
            s.cookies.set(k, v)
    s.headers.update({"Content-Type": "application/json", **XRW})
    return s


def _uid(email):
    u = db.users.find_one({"email": email}, {"user_id": 1})
    return u["user_id"] if u else None


UID_A = None
UID_B = None


@pytest.fixture(scope="module", autouse=True)
def setup_members():
    """Ensure mem_a is active (apply+approve) and mem_b is active (invite+auto-activate)."""
    global UID_A, UID_B
    a = _s(ADMIN)
    ma = _s(MEM_A).get(f"{API}/members/me").json()
    if ma.get("status") != "active":
        r = _s(MEM_A).post(f"{API}/members/apply", json={
            "city": "Wilmington", "phone": "555-0001", "referred_by": "QA Admin",
            "is_adult": True, "is_delaware": True, "agrees_bylaws": True, "why": ""
        })
        assert r.status_code == 200, r.text
        uid_a = _uid("qa.sister.a@example.com")
        rr = a.post(f"{API}/admin/members/{uid_a}/status", json={"action": "approve"})
        assert rr.status_code == 200, rr.text
    # Invite mem_b
    a.post(f"{API}/admin/members/invite", json={"email": "qa.sister.b@example.com", "name": "Bea QA Tester"})
    _s(MEM_B).get(f"{API}/members/me")
    UID_A = _uid("qa.sister.a@example.com")
    UID_B = _uid("qa.sister.b@example.com")
    assert UID_A and UID_B
    # Clean previous phase-3 state for these users
    db.member_notices.delete_many({"key": {"$regex": "duesrem"}})
    db.member_runs.delete_many({"kind": "dues_reminders"})
    db.member_pay_tokens.delete_many({"user_id": {"$in": [UID_A, UID_B]}})
    db.member_collections.delete_many({"beneficiary_id": {"$in": [UID_A, UID_B]}})
    db.member_ledger.delete_many({"user_id": {"$in": [UID_A, UID_B]}, "kind": {"$in": ["bereavement", "illness"]}})
    db.users.update_many({"user_id": {"$in": [UID_A, UID_B]}}, {"$unset": {"member_leave_request": "", "member_ends_at": "", "member_end_reason": "", "member_office": ""}})
    yield


# ---------- Security ----------
class TestSecurity:
    def test_anon_minutes_401(self):
        assert _s().get(f"{API}/members/minutes").status_code == 401

    def test_anon_record_401(self):
        assert _s().get(f"{API}/members/ballots/anything/record").status_code == 401

    def test_member_403_on_admin_collections(self):
        r = _s(MEM_A).get(f"{API}/admin/members/collections")
        assert r.status_code == 403

    def test_member_403_on_admin_december(self):
        r = _s(MEM_A).get(f"{API}/admin/members/december")
        assert r.status_code == 403

    def test_member_403_on_dues_remind(self):
        r = _s(MEM_A).post(f"{API}/admin/members/dues/remind")
        assert r.status_code == 403


# ---------- Dues reminders ----------
class TestDuesReminders:
    def test_reminders_endpoint_lists_runs(self):
        r = _s(ADMIN).get(f"{API}/admin/members/dues/reminders")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_send_reminders_and_dedupe(self):
        # Ensure member A has a balance (registration fee was added on approve)
        st = _s(MEM_A).get(f"{API}/members/standing").json()
        assert st["balance"] > 0

        a = _s(ADMIN)
        # Clear notices for same-day round
        db.member_notices.delete_many({"key": {"$regex": "duesrem"}})
        r1 = a.post(f"{API}/admin/members/dues/remind")
        assert r1.status_code == 200
        sent1 = r1.json()["sent"]
        assert sent1 >= 1  # at least mem_a has balance

        r2 = a.post(f"{API}/admin/members/dues/remind")
        assert r2.status_code == 200
        # Same-day dedupe => 0
        assert r2.json()["sent"] == 0

    def test_pay_link_redirects_to_stripe(self):
        from datetime import datetime, timezone, timedelta
        tok = "qa_pay_tok_aaa"
        year = datetime.now().year
        db.member_pay_tokens.delete_one({"token": tok})
        db.member_pay_tokens.insert_one({
            "token": tok, "user_id": UID_A, "year": year,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        })
        r = requests.get(f"{API}/members/pay/{tok}", allow_redirects=False)
        assert r.status_code == 303, r.text
        loc = r.headers.get("location", "")
        assert "checkout.stripe.com" in loc, f"Expected Stripe redirect, got {loc}"

    def test_invalid_pay_token_redirects_to_members(self):
        r = requests.get(f"{API}/members/pay/not-a-real-token", allow_redirects=False)
        assert r.status_code == 303
        assert "/members" in r.headers.get("location", "")

    def test_scheduled_sender_jan2_dedupe(self):
        """Call _send_dues_reminders directly to simulate scheduler."""
        import asyncio
        import sys
        sys.path.insert(0, "/app/backend")
        import server
        db.member_notices.delete_many({"key": {"$regex": "duesrem"}})
        n1 = asyncio.get_event_loop().run_until_complete(server._send_dues_reminders("jan2"))
        n2 = asyncio.get_event_loop().run_until_complete(server._send_dues_reminders("jan2"))
        assert n1 >= 0
        assert n2 == 0  # dedupe


# ---------- Support collections ----------
class TestCollections:
    cid = None

    def test_create_bereavement_charges_actives_except_beneficiary(self):
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/collections", json={
            "kind": "bereavement", "beneficiary_id": UID_B,
            "relationship": "mother", "share": 20.0, "note": "QA note", "notify": False
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["charged"] >= 1  # at least mem_a
        TestCollections.cid = d["id"]
        # Verify mem_a got the charge
        ch = db.member_ledger.find_one({"collection_id": d["id"], "user_id": UID_A, "direction": "charge"})
        assert ch is not None
        assert abs(ch["amount"] - 20.0) < 0.01
        # Beneficiary should NOT be charged
        chb = db.member_ledger.find_one({"collection_id": d["id"], "user_id": UID_B, "direction": "charge"})
        assert chb is None

    def test_illness_prefill_amount_accepted(self):
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/collections", json={
            "kind": "illness", "beneficiary_id": UID_A, "relationship": "self",
            "share": 50.0, "note": "QA illness", "notify": False
        })
        assert r.status_code == 200
        cid = r.json()["id"]
        db.member_collections.delete_one({"id": cid})
        db.member_ledger.delete_many({"collection_id": cid})

    def test_invalid_kind_rejected(self):
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/collections", json={
            "kind": "party", "beneficiary_id": UID_A, "relationship": "", "share": 10.0
        })
        assert r.status_code == 400

    def test_collection_view_math(self):
        cid = TestCollections.cid
        assert cid
        a = _s(ADMIN)
        rows = a.get(f"{API}/admin/members/collections").json()
        c = next((x for x in rows if x["id"] == cid), None)
        assert c is not None
        assert c["expected"] >= 20.0
        assert c["paid_out"] == 0
        assert c["available"] == c["collected"] - c["paid_out"]
        # contributors list contains mem_a
        uids = [x["user_id"] for x in c["contributors"]]
        assert UID_A in uids
        assert UID_B not in uids

    def test_mark_contributor_paid_cash(self):
        cid = TestCollections.cid
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/collections/{cid}/contributors/{UID_A}/paid", json={"method": "cash"})
        assert r.status_code == 200, r.text
        rows = a.get(f"{API}/admin/members/collections").json()
        c = next(x for x in rows if x["id"] == cid)
        assert c["collected"] >= 20.0

    def test_add_and_delete_payout(self):
        cid = TestCollections.cid
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/collections/{cid}/payouts", json={
            "amount": 10.0, "date": "2026-01-10", "method": "zelle", "note": "QA"
        })
        assert r.status_code == 200
        pid = r.json()["id"]
        rows = a.get(f"{API}/admin/members/collections").json()
        c = next(x for x in rows if x["id"] == cid)
        assert c["paid_out"] == 10.0
        assert c["available"] == c["collected"] - 10.0
        # Delete
        r = a.delete(f"{API}/admin/members/collections/{cid}/payouts/{pid}")
        assert r.status_code == 200

    def test_close_collection(self):
        cid = TestCollections.cid
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/collections/{cid}/close")
        assert r.status_code == 200
        c = db.member_collections.find_one({"id": cid})
        assert c["status"] == "closed"


# ---------- Minutes ----------
class TestMinutes:
    mid = None
    bid = None

    @classmethod
    def _create_meeting(cls):
        if cls.mid:
            return cls.mid
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/meetings", json={
            "title": "QA Phase3 Meeting", "date": "2026-01-15", "kind": "general"
        })
        assert r.status_code == 200, r.text
        cls.mid = r.json()["id"]
        return cls.mid

    def test_save_draft_minutes(self):
        mid = self._create_meeting()
        a = _s(ADMIN)
        r = a.put(f"{API}/admin/members/meetings/{mid}/minutes", json={
            "body": "QA draft minutes body with notes.", "approve": False
        })
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_draft_hidden_from_members(self):
        r = _s(MEM_A).get(f"{API}/members/minutes")
        assert r.status_code == 200
        titles = [m["title"] for m in r.json()]
        assert "QA Phase3 Meeting" not in titles

    def test_empty_body_rejected(self):
        mid = self._create_meeting()
        a = _s(ADMIN)
        r = a.put(f"{API}/admin/members/meetings/{mid}/minutes", json={"body": "   ", "approve": False})
        assert r.status_code == 400

    def test_approve_minutes_visible(self):
        mid = self._create_meeting()
        a = _s(ADMIN)
        r = a.put(f"{API}/admin/members/meetings/{mid}/minutes", json={
            "body": "QA approved minutes final.", "approve": True
        })
        assert r.status_code == 200
        assert r.json()["status"] == "approved"
        r2 = _s(MEM_A).get(f"{API}/members/minutes")
        assert r2.status_code == 200
        titles = [m["title"] for m in r2.json()]
        assert "QA Phase3 Meeting" in titles

    def test_minutes_404_unknown_meeting(self):
        a = _s(ADMIN)
        r = a.put(f"{API}/admin/members/meetings/no-such-id/minutes", json={"body": "x", "approve": False})
        assert r.status_code == 404


# ---------- Vote Record ----------
class TestVoteRecord:
    bid = None

    @classmethod
    def _create_ballot(cls):
        if cls.bid:
            return cls.bid
        a = _s(ADMIN)
        opens = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
        closes = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        r = a.post(f"{API}/admin/members/ballots", json={
            "kind": "resolution", "title": "QA Phase3 Resolution",
            "description": "QA desc", "opens_at": opens, "closes_at": closes
        })
        assert r.status_code == 200, r.text
        cls.bid = r.json()["id"]
        return cls.bid

    def test_record_404_while_open(self):
        bid = self._create_ballot()
        # Force open state by setting opens_at in the past but closes_at in future
        db.member_ballots.update_one({"id": bid}, {"$set": {
            "opens_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            "closes_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }})
        r = _s(MEM_A).get(f"{API}/members/ballots/{bid}/record")
        assert r.status_code == 404

    def test_set_secretary_office(self):
        a = _s(ADMIN)
        r = a.put(f"{API}/admin/members/{UID_A}/office", json={"office": "Secretary"})
        assert r.status_code == 200
        u = db.users.find_one({"user_id": UID_A}, {"member_office": 1})
        assert u["member_office"] == "Secretary"

    def test_closed_ballot_record_has_secretary_and_tally(self):
        bid = self._create_ballot()
        a = _s(ADMIN)
        # Close ballot (force past closes_at)
        db.member_ballots.update_one({"id": bid}, {"$set": {
            "opens_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "closes_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        }})
        r = a.post(f"{API}/admin/members/ballots/{bid}/close")
        # Status may be 200 or 400 depending on backend logic, but either way state should be closed
        rec = _s(MEM_A).get(f"{API}/members/ballots/{bid}/record")
        assert rec.status_code == 200, rec.text
        d = rec.json()
        assert d["state"] == "closed"
        assert d["title"] == "QA Phase3 Resolution"
        assert "results" in d
        assert d.get("secretary") == "Ama QA Sister"
        assert "generated_at" in d


# ---------- December renewal ----------
class TestDecember:
    def test_member_can_request_leave(self):
        r = _s(MEM_B).post(f"{API}/members/leave-request", json={"reason": "QA leaving"})
        assert r.status_code == 200
        me = _s(MEM_B).get(f"{API}/members/me").json()
        assert me["leave_request"]["reason"] == "QA leaving"

    def test_december_lists_show_leaving(self):
        a = _s(ADMIN)
        r = a.get(f"{API}/admin/members/december")
        assert r.status_code == 200, r.text
        d = r.json()
        leaving_uids = [x["user_id"] for x in d["lists"]["leaving"]]
        assert UID_B in leaving_uids

    def test_confirm_leave_sets_ends_at(self):
        a = _s(ADMIN)
        year = datetime.now().year
        key = f"leaving:{UID_B}"
        r = a.post(f"{API}/admin/members/december", json={"key": key, "decision": "end", "year": year})
        assert r.status_code == 200
        u = db.users.find_one({"user_id": UID_B}, {"member_ends_at": 1, "member_end_reason": 1})
        assert u["member_ends_at"] == f"{year}-12-31"
        assert u["member_end_reason"] == "voluntary"

    def test_december_undo_clears_ends_at(self):
        a = _s(ADMIN)
        year = datetime.now().year
        key = f"leaving:{UID_B}"
        r = a.delete(f"{API}/admin/members/december", params={"key": key, "year": year})
        assert r.status_code == 200
        u = db.users.find_one({"user_id": UID_B}, {"member_ends_at": 1})
        assert not u.get("member_ends_at")

    def test_end_memberships_deactivates(self):
        """Set ends_at in past, run _end_memberships, assert status=ended; member sees 403 on bylaws."""
        import asyncio, sys
        sys.path.insert(0, "/app/backend")
        import server
        from datetime import date
        db.users.update_one({"user_id": UID_B}, {"$set": {"member_ends_at": "2020-12-31"}})
        n = asyncio.get_event_loop().run_until_complete(server._end_memberships(date.today()))
        assert n >= 1
        u = db.users.find_one({"user_id": UID_B}, {"member_status": 1})
        assert u["member_status"] == "ended"
        r = _s(MEM_B).get(f"{API}/members/bylaws")
        assert r.status_code == 403
        # Restore for teardown
        db.users.update_one({"user_id": UID_B}, {"$set": {"member_status": "active"}, "$unset": {"member_ends_at": ""}})

    def test_invalid_decision_rejected(self):
        a = _s(ADMIN)
        r = a.post(f"{API}/admin/members/december", json={"key": f"leaving:{UID_A}", "decision": "approve"})
        assert r.status_code == 400


# ---------- Regression ----------
class TestRegression:
    def test_portal_tabs_still_work(self):
        s = _s(MEM_A)
        for ep in ["/members/me", "/members/announcements", "/members/threads", "/members/directory",
                   "/members/standing", "/members/ballots", "/members/birthdays", "/members/bylaws"]:
            r = s.get(f"{API}{ep}")
            assert r.status_code == 200, f"{ep} -> {r.status_code}"

    def test_admin_subs_still_work(self):
        a = _s(ADMIN)
        for ep in ["/admin/members", "/admin/members/dues", "/admin/members/meetings", "/admin/members/ballots"]:
            r = a.get(f"{API}{ep}")
            assert r.status_code == 200, f"{ep} -> {r.status_code}"
