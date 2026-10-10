"""Iteration 15: Session cloning, forecast history, badge wall, appeal comparison."""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
TOK = "qa_tok_123"
HEADERS = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "Cookie": f"session_token={TOK}"}
GET_HEADERS = {"Cookie": f"session_token={TOK}"}

_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def base_program():
    """Use wellness-workshops as base; reset to capacity=1, claim mode."""
    p = _db.programs.find_one({"slug": "wellness-workshops"}, {"_id": 0})
    assert p, "wellness-workshops program is required"
    _db.programs.update_one(
        {"id": p["id"]},
        {"$set": {"capacity": 1, "waitlist_mode": "claim"},
         "$unset": {"priority_until": "", "transfer_from": "", "transfer_mode": "", "transfer_done": "",
                    "transferred_count": "", "season_started_at": ""}},
    )
    yield _db.programs.find_one({"id": p["id"]}, {"_id": 0})
    # final cleanup done in cleanup_all


@pytest.fixture(scope="module", autouse=True)
def cleanup_all():
    created_program_ids = set()
    seeded_submission_ids = set()
    seeded_sub_tags = {"qa_iter15"}
    yield {"programs": created_program_ids, "subs": seeded_submission_ids, "tags": seeded_sub_tags}
    # Teardown
    for pid in list(created_program_ids):
        _db.programs.delete_one({"id": pid})
        _db.submissions.delete_many({"program_id": pid})
        _db.program_snapshots.delete_many({"program_id": pid})
    # cleanup QA submissions on any program
    _db.submissions.delete_many({"data.email": {"$regex": "qa.iter15.*@example.com$"}})
    _db.submissions.delete_many({"qa_tag": {"$in": list(seeded_sub_tags)}})
    _db.volunteer_milestones.delete_many({"email": {"$regex": "qa.iter15.*@example.com$"}})
    _db.volunteer_hours.delete_many({"email": {"$regex": "qa.iter15.*@example.com$"}})
    _db.segment_emails.delete_many({"id": "qa-appeal-1"})
    _db.yir_emails.delete_many({"id": "qa-yir"})
    _db.payment_transactions.delete_many({"session_id": "qa_sess_ap"})
    _db.payment_transactions.delete_many({"donor_email": "qa.ap@example.com"})
    # reset wellness-workshops
    _db.programs.update_one(
        {"slug": "wellness-workshops"},
        {"$set": {"capacity": 0, "waitlist_mode": "claim"},
         "$unset": {"priority_until": "", "transfer_from": "", "transfer_mode": "", "transfer_done": "",
                    "transferred_count": "", "season_started_at": ""}},
    )
    # reset badge wall mode
    _db.settings.update_one({"key": "site"}, {"$set": {"badge_wall_mode": "optin"}}, upsert=True)
    # clean season snapshots we created
    _db.program_snapshots.delete_many({"label": "QA Spring"})


# ---------- Helpers ----------
def _program_in_payload(p: dict, **overrides) -> dict:
    out = {
        "title": p.get("title", ""),
        "category": p.get("category", ""),
        "image_url": p.get("image_url", ""),
        "summary": p.get("summary", ""),
        "body": p.get("body", ""),
        "goals": p.get("goals", []),
        "impact": p.get("impact", []),
        "cta_text": p.get("cta_text") or "Get Involved",
        "cta_link": p.get("cta_link") or "/volunteer",
        "published": p.get("published", True),
        "capacity": p.get("capacity", 0),
        "waitlist_mode": p.get("waitlist_mode") or "claim",
        "gallery": p.get("gallery", []),
        "testimonials": p.get("testimonials", []),
        "home_testimonial_ids": p.get("home_testimonial_ids", []),
    }
    out.update(overrides)
    return out


def _seed_waitlist(pid: str, slug: str, title: str, n: int, email_prefix: str):
    """Insert n waitlisted submissions directly."""
    base_t = datetime.now(timezone.utc) - timedelta(hours=24)
    for i in range(n):
        sub = {
            "id": str(uuid.uuid4()),
            "type": "program_signup",
            "program_id": pid,
            "waitlist": True,
            "read": False,
            "created_at": (base_t + timedelta(seconds=i)).isoformat(),
            "qa_tag": "qa_iter15",
            "data": {"name": f"QA Iter15 {email_prefix}{i}", "email": f"qa.iter15.{email_prefix}{i}@example.com",
                     "program": title, "program_slug": slug},
        }
        _db.submissions.insert_one(dict(sub))


# ---------- Tests: Clone endpoint basics ----------
class TestCloneBasics:
    def test_clone_invalid_transfer_400(self, base_program):
        r = requests.post(f"{API}/admin/programs/{base_program['id']}/clone",
                          json={"capacity": 2, "transfer": "bogus"}, headers=HEADERS)
        assert r.status_code == 400

    def test_clone_creates_hidden_session_2(self, base_program, cleanup_all):
        r = requests.post(f"{API}/admin/programs/{base_program['id']}/clone",
                          json={"capacity": 2, "transfer": "claim"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["published"] is False
        assert data["title"] == f"{base_program['title']} (Session 2)"
        assert data["cloned_from"] == base_program["id"]
        assert data["transfer_from"] == base_program["id"]
        assert data["transfer_mode"] == "claim"
        assert data["transfer_done"] is False
        assert "source_waitlist" in data
        cleanup_all["programs"].add(data["id"])

    def test_clone_of_clone_yields_session_3(self, base_program, cleanup_all):
        # find session 2
        clone2 = _db.programs.find_one({"cloned_from": base_program["id"], "title": {"$regex": r"\(Session 2\)$"}}, {"_id": 0})
        assert clone2
        r = requests.post(f"{API}/admin/programs/{clone2['id']}/clone",
                          json={"capacity": 1, "transfer": "none"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["title"] == f"{base_program['title']} (Session 3)"
        # no transfer_from when transfer=none
        assert "transfer_from" not in d or not d.get("transfer_from")
        cleanup_all["programs"].add(d["id"])


# ---------- Tests: Clone claim transfer ----------
class TestCloneClaimTransfer:
    def test_claim_publish_transfers_waitlist(self, base_program, cleanup_all):
        pid = base_program["id"]
        # seed 1 enrolled signup + 3 waitlisted
        _db.submissions.delete_many({"program_id": pid, "qa_tag": "qa_iter15"})
        enrolled = {
            "id": str(uuid.uuid4()), "type": "program_signup", "program_id": pid, "waitlist": False, "read": False,
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(), "qa_tag": "qa_iter15",
            "data": {"name": "QA Enrolled", "email": "qa.iter15.enroll@example.com", "program": base_program["title"],
                     "program_slug": base_program["slug"]},
        }
        _db.submissions.insert_one(dict(enrolled))
        _seed_waitlist(pid, base_program["slug"], base_program["title"], 3, "wl")

        # Clone capacity=2 claim
        r = requests.post(f"{API}/admin/programs/{pid}/clone",
                          json={"capacity": 2, "transfer": "claim"}, headers=HEADERS)
        assert r.status_code == 200
        clone = r.json()
        cleanup_all["programs"].add(clone["id"])

        # Publish clone (full payload)
        payload = _program_in_payload(clone, published=True)
        r = requests.put(f"{API}/admin/programs/{clone['id']}", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        time.sleep(2)

        # Clone should have waitlist offers: 2 copies with waitlist=True + offer_override True + offer_status=open
        copied = list(_db.submissions.find({"program_id": clone["id"]}, {"_id": 0}))
        assert len(copied) == 2, copied
        for c in copied:
            assert c.get("waitlist") is True
            assert c.get("offer_status") == "open"
            assert c.get("offer_override") is True
            assert c.get("offer_expires")
            # ~48h from now
            exp = datetime.fromisoformat(c["offer_expires"])
            delta_h = (exp - datetime.now(timezone.utc)).total_seconds() / 3600
            assert 46 <= delta_h <= 50, f"expiry delta {delta_h}h"

        # Originals: 2 oldest marked transferred=True
        originals_transferred = _db.submissions.count_documents({"program_id": pid, "transferred": True})
        assert originals_transferred == 2

        # GET admin waitlist on orig -> 1 remaining
        r = requests.get(f"{API}/admin/programs/{pid}/waitlist", headers=GET_HEADERS)
        assert r.status_code == 200
        wl = r.json()
        assert len(wl["items"]) == 1

        # Clone has priority_until ~48h
        clone_doc = _db.programs.find_one({"id": clone["id"]}, {"_id": 0})
        assert clone_doc.get("priority_until")
        assert clone_doc.get("transfer_done") is True

        # Public GET clone -> full:true (during priority window), seats_left 0 effectively? capacity=2, taken=0 but priority_until>now
        r = requests.get(f"{API}/programs/{clone['slug']}")
        assert r.status_code == 200
        public = r.json()
        assert public.get("full") is True, public

        # Public signup during priority window -> waitlist True
        r = requests.post(f"{API}/programs/{clone['slug']}/signup",
                          json={"name": "QA Public", "email": "qa.iter15.pub@example.com", "phone": ""})
        if r.status_code == 429:
            pytest.skip("rate limited; retry later")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("waitlist") is True

        # Claim one offer
        tok = copied[0]["offer_token"]
        r = requests.post(f"{API}/waitlist/claim", json={"token": tok})
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "claimed"

        # Re-publish -> should NOT re-transfer (transfer_done already True)
        payload["published"] = True
        r = requests.put(f"{API}/admin/programs/{clone['id']}", json=payload, headers=HEADERS)
        assert r.status_code == 200
        time.sleep(1)
        # still 2 copies on clone (one claimed, no new copies)
        copies_count = _db.submissions.count_documents({"program_id": clone["id"], "transferred_from": {"$exists": True}})
        assert copies_count == 2


# ---------- Tests: Clone auto transfer ----------
class TestCloneAutoTransfer:
    def test_auto_publish_moves_waitlist_as_seats(self, base_program, cleanup_all):
        pid = base_program["id"]
        # fresh setup: clear QA submissions and seed waitlisted
        _db.submissions.delete_many({"program_id": pid, "qa_tag": "qa_iter15"})
        # reset base_program fields
        _db.programs.update_one({"id": pid}, {"$unset": {"priority_until": "", "transfer_from": "", "transfer_mode": "",
                                                         "transfer_done": "", "transferred_count": ""}})
        _seed_waitlist(pid, base_program["slug"], base_program["title"], 3, "wla")

        r = requests.post(f"{API}/admin/programs/{pid}/clone",
                          json={"capacity": 2, "transfer": "auto"}, headers=HEADERS)
        assert r.status_code == 200
        clone = r.json()
        cleanup_all["programs"].add(clone["id"])

        payload = _program_in_payload(clone, published=True)
        r = requests.put(f"{API}/admin/programs/{clone['id']}", json=payload, headers=HEADERS)
        assert r.status_code == 200
        time.sleep(2)

        copied = list(_db.submissions.find({"program_id": clone["id"]}, {"_id": 0}))
        assert len(copied) == 2
        for c in copied:
            assert c.get("waitlist") is False

        # public GET clone -> seats_left 0 (capacity 2, 2 taken)
        r = requests.get(f"{API}/programs/{clone['slug']}")
        assert r.status_code == 200
        pub = r.json()
        assert pub.get("seats_left") == 0

        # originals marked transferred
        assert _db.submissions.count_documents({"program_id": pid, "transferred": True}) >= 2


# ---------- Tests: Forecast history ----------
class TestForecastHistory:
    def test_history_endpoint_and_close_season(self, base_program, cleanup_all):
        pid = base_program["id"]
        # Reset to clean state capacity=1
        _db.submissions.delete_many({"program_id": pid, "qa_tag": "qa_iter15"})
        _db.programs.update_one({"id": pid}, {"$set": {"capacity": 1, "season_started_at": _now()},
                                              "$unset": {"priority_until": "", "transfer_from": "", "transfer_mode": "",
                                                         "transfer_done": "", "transferred_count": ""}})
        # Seed 1 enrolled signup
        _db.submissions.insert_one({
            "id": str(uuid.uuid4()), "type": "program_signup", "program_id": pid, "waitlist": False, "read": False,
            "created_at": _now(), "qa_tag": "qa_iter15",
            "data": {"name": "QA H1", "email": "qa.iter15.h1@example.com", "program": base_program["title"],
                     "program_slug": base_program["slug"]},
        })

        r = requests.get(f"{API}/admin/programs/{pid}/history", headers=GET_HEADERS)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["program"] == base_program["title"]
        assert "season_started_at" in d
        assert isinstance(d["monthly"], list)
        assert isinstance(d["seasons"], list)
        cur = d["current"]
        assert cur["capacity"] == 1
        assert cur["taken"] >= 1
        assert isinstance(cur["days_to_fill"], int)

        # Close season
        r = requests.post(f"{API}/admin/programs/{pid}/close-season",
                          json={"label": "QA Spring"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        res = r.json()
        assert res["snapshot"]["kind"] == "season"
        assert res["snapshot"]["label"] == "QA Spring"
        assert res["archived"] >= 1
        time.sleep(1)

        # Seats reopen on base program (capacity=1, taken should be 0 now; seats_left = 1)
        r = requests.get(f"{API}/programs/{base_program['slug']}")
        assert r.status_code == 200
        pub = r.json()
        assert pub.get("seats_left") == 1

        # seasons list contains 'QA Spring'
        r = requests.get(f"{API}/admin/programs/{pid}/history", headers=GET_HEADERS)
        d = r.json()
        labels = [s.get("label") for s in d["seasons"]]
        assert "QA Spring" in labels


# ---------- Tests: Badge wall ----------
class TestBadgeWall:
    def _seed_milestone(self, email: str, name: str, opt: bool, threshold: int = 50):
        _db.volunteer_hours.insert_one({
            "id": str(uuid.uuid4()), "email": email, "name": name, "hours": threshold,
            "status": "approved", "leaderboard": opt, "date": "2025-05-01",
            "created_at": _now(), "program_id": "", "note": "",
        })
        _db.volunteer_milestones.insert_one({
            "id": str(uuid.uuid4()), "email": email, "threshold": threshold, "scope": "all",
            "label": f"{threshold} Hours All-Time", "awarded_at": _now(),
            "share_token": f"qa_iter15_{email.split('@')[0]}",
        })

    def test_badge_wall_optin_default(self):
        # ensure default
        _db.settings.update_one({"key": "site"}, {"$set": {"badge_wall_mode": "optin"}}, upsert=True)
        self._seed_milestone("qa.iter15.bopt@example.com", "Opt In Volunteer", True)
        self._seed_milestone("qa.iter15.bnon@example.com", "Non Opt Volunteer", False)
        r = requests.get(f"{API}/volunteer-hours/badge-wall")
        assert r.status_code == 200
        items = r.json()["items"]
        emails = {i.get("share_token") for i in items if i.get("share_token")}
        # Only the opted-in volunteer should appear among our two
        names = [i["name"] for i in items]
        # short name form: 'Opt I.' etc
        assert any(n.startswith("Opt ") for n in names)
        assert not any(n.startswith("Non ") for n in names)
        # No email field in any item
        for i in items:
            assert "email" not in i
            assert "threshold" in i and "label" in i and "awarded_at" in i and "share_token" in i

    def test_admin_badge_wall_setters(self):
        # Unauth
        r = requests.get(f"{API}/admin/badge-wall")
        assert r.status_code in (401, 403)
        # Get
        r = requests.get(f"{API}/admin/badge-wall", headers=GET_HEADERS)
        assert r.status_code == 200
        assert r.json()["mode"] in ("optin", "all")
        # Set invalid
        r = requests.put(f"{API}/admin/badge-wall", json={"mode": "bogus"}, headers=HEADERS)
        assert r.status_code == 400
        # Set 'all'
        r = requests.put(f"{API}/admin/badge-wall", json={"mode": "all"}, headers=HEADERS)
        assert r.status_code == 200
        # Public should now include non-opted
        r = requests.get(f"{API}/volunteer-hours/badge-wall")
        names = [i["name"] for i in r.json()["items"]]
        assert any(n.startswith("Non ") for n in names)
        # Reset
        requests.put(f"{API}/admin/badge-wall", json={"mode": "optin"}, headers=HEADERS)


# ---------- Tests: Appeal comparison ----------
class TestAppealComparison:
    def test_unauth(self):
        r = requests.get(f"{API}/admin/reports/appeal-comparison")
        assert r.status_code in (401, 403)

    def test_appeal_and_yir_rows(self):
        now = _now()
        _db.segment_emails.delete_many({"id": "qa-appeal-1"})
        _db.payment_transactions.delete_many({"session_id": "qa_sess_ap"})
        _db.yir_emails.delete_many({"id": "qa-yir"})
        _db.segment_emails.insert_one({
            "id": "qa-appeal-1", "subject": "QA Appeal", "segment": "all", "recipients": 10, "sent": 10,
            "clicks": 4, "kind": "scheduled", "sent_at": now,
        })
        _db.payment_transactions.insert_one({
            "appeal_id": "qa-appeal-1", "amount": 50, "payment_status": "paid",
            "donor_email": "qa.ap@example.com", "created_at": now, "session_id": "qa_sess_ap",
        })
        _db.yir_emails.insert_one({
            "id": "qa-yir", "year": 2025, "recipients": 5, "sent": 5, "status": "done",
            "trigger": "manual", "started_at": now,
        })

        r = requests.get(f"{API}/admin/reports/appeal-comparison", headers=GET_HEADERS)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        ap = next((x for x in items if x["id"] == "qa-appeal-1"), None)
        assert ap is not None, items
        assert ap["kind"] == "scheduled"
        assert ap["recipients"] == 10
        assert ap["clicks"] == 4
        assert ap["click_rate"] == 40.0
        assert ap["gifts"] == 1
        assert ap["raised"] == 50.0
        assert ap["per_recipient"] == 5.0

        yir = next((x for x in items if x["id"] == "yir-2025"), None)
        assert yir is not None
        assert yir["kind"] == "year_in_review"
        assert yir["recipients"] == 5
