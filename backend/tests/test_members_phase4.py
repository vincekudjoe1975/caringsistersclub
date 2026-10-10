"""Phase 4 member portal tests: treasurer report, agendas + reminders, anniversaries, referrer notices."""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests

sys.path.insert(0, '/app/backend')

from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
XRW = {"X-Requested-With": "XMLHttpRequest"}
ADMIN = {"session_token": "qa_tok_123"}
MEM_A = {"session_token": "mem_tok_a"}
MEM_B = {"session_token": "mem_tok_b"}


def _url(p):
    return f"{BASE}/api{p}"


# ---------- Setup fixture: apply mem_a, approve, invite + activate mem_b ----------
@pytest.fixture(scope="module", autouse=True)
def setup_members():
    # mem_a applies with referred_by "Bea QA Tester" (fuzzy match for mem_b)
    r = requests.post(_url("/members/apply"), cookies=MEM_A, headers=XRW,
                      json={"phone": "555-1", "city": "Dover", "referred_by": "Bea QA Testr",
                            "why": "QA", "is_adult": True, "is_delaware": True, "agrees_bylaws": True})
    assert r.status_code in (200, 400)  # may already be applied

    # admin approves
    r = requests.post(_url("/admin/members/qa_mem_a/status"), cookies=ADMIN, headers=XRW, json={"action": "approve"})
    assert r.status_code == 200

    # invite mem_b (idempotent: if already active, skip)
    r = requests.post(_url("/admin/members/invite"), cookies=ADMIN, headers=XRW,
                      json={"email": "qa.sister.b@example.com", "name": "Bea QA Tester"})
    assert r.status_code in (200, 400), r.text

    # mem_b GET /members/me activates her
    r = requests.get(_url("/members/me"), cookies=MEM_B)
    assert r.status_code == 200
    assert r.json()["status"] == "active", r.json()

    # Record a few payments for mem_a (this month, year)
    today = datetime.now().date()
    for amt, method, kind in [(50, "cash", "dues"), (30, "zelle", "dues"), (10, "check", "registration"), (5, "card", "fine")]:
        r = requests.post(_url(f"/admin/members/qa_mem_a/payments"), cookies=ADMIN, headers=XRW,
                          json={"amount": amt, "method": method, "kind": kind, "year": today.year})
        assert r.status_code == 200, r.text
    yield


# ---------- Security ----------
class TestSecurity:
    def test_admin_treasurer_requires_admin(self):
        assert requests.get(_url("/admin/members/treasurer")).status_code == 401
        assert requests.get(_url("/admin/members/treasurer"), cookies=MEM_A).status_code == 403

    def test_treasurer_share_requires_admin(self):
        assert requests.post(_url("/admin/members/treasurer/share"), cookies=MEM_A, headers=XRW,
                             json={"year": 2026, "month": 1}).status_code == 403

    def test_referrers_requires_admin(self):
        assert requests.get(_url("/admin/members/referrers")).status_code == 401
        assert requests.get(_url("/admin/members/referrers"), cookies=MEM_A).status_code == 403

    def test_referrers_preview_requires_admin(self):
        assert requests.get(_url("/admin/members/referrers/preview"), cookies=MEM_A).status_code == 403

    def test_joined_requires_admin(self):
        assert requests.put(_url("/admin/members/qa_mem_a/joined"), cookies=MEM_A, headers=XRW,
                            json={"date": "2024-01-01"}).status_code == 403

    def test_member_endpoints_require_member(self):
        for p in ["/members/next-meeting", "/members/anniversaries", "/members/treasurer-reports"]:
            assert requests.get(_url(p)).status_code == 401

    def test_agenda_admin_only(self):
        assert requests.put(_url("/admin/members/meetings/x/agenda"), cookies=MEM_A, headers=XRW,
                            json={"body": "x"}).status_code == 403
        assert requests.put(_url("/admin/members/meetings/x/agenda"), headers=XRW,
                            json={"body": "x"}).status_code == 401


# ---------- Treasurer report ----------
class TestTreasurer:
    def test_treasurer_totals(self):
        today = datetime.now()
        r = requests.get(_url(f"/admin/members/treasurer?year={today.year}&month={today.month}"), cookies=ADMIN)
        assert r.status_code == 200
        d = r.json()
        assert d["money_in"]["total"] >= 95.0  # 50+30+10+5
        assert d["money_in"]["by_kind"]["dues"] >= 80.0
        assert d["money_in"]["by_kind"]["registration"] >= 10.0
        assert d["money_in"]["by_kind"]["fine"] >= 5.0
        assert d["money_in"]["by_method"]["cash"] >= 50.0
        assert d["money_in"]["by_method"]["zelle"] >= 30.0
        assert d["money_in"]["by_method"]["check"] >= 10.0
        assert d["money_in"]["by_method"]["card"] >= 5.0
        assert d["money_in"]["payments"] >= 4
        assert "ytd" in d and d["ytd"]["money_in"] >= d["money_in"]["total"]
        assert "outstanding" in d
        assert d["shared"] is None

    def test_share_and_unshare(self):
        today = datetime.now()
        y, m = today.year, today.month
        # share
        r = requests.post(_url("/admin/members/treasurer/share"), cookies=ADMIN, headers=XRW,
                          json={"year": y, "month": m})
        assert r.status_code == 200
        rid = r.json()["id"]

        # member can see
        r2 = requests.get(_url("/members/treasurer-reports"), cookies=MEM_A)
        assert r2.status_code == 200
        rows = r2.json()
        assert any(x["id"] == rid for x in rows), rows

        # member can view snapshot
        r3 = requests.get(_url(f"/members/treasurer-reports/{rid}"), cookies=MEM_A)
        assert r3.status_code == 200
        assert r3.json()["year"] == y

        # unshare
        r4 = requests.delete(_url(f"/admin/members/treasurer/share?year={y}&month={m}"), cookies=ADMIN, headers=XRW)
        assert r4.status_code == 200
        r5 = requests.get(_url("/members/treasurer-reports"), cookies=MEM_A).json()
        assert not any(x["id"] == rid for x in r5)
        # 404 for the snapshot
        assert requests.get(_url(f"/members/treasurer-reports/{rid}"), cookies=MEM_A).status_code == 404


# ---------- Agendas ----------
class TestAgenda:
    @pytest.fixture(scope="class")
    def meeting_id(self):
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        r = requests.post(_url("/admin/members/meetings"), cookies=ADMIN, headers=XRW,
                          json={"title": "QA Phase4 Meeting", "date": tomorrow, "kind": "general"})
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        yield mid
        requests.delete(_url(f"/admin/members/meetings/{mid}"), cookies=ADMIN, headers=XRW)

    def test_draft_not_visible(self, meeting_id):
        r = requests.put(_url(f"/admin/members/meetings/{meeting_id}/agenda"), cookies=ADMIN, headers=XRW,
                         json={"body": "Opening prayer\nTreasurer\nOld business", "time": "18:30", "location": "Zoom", "publish": False})
        assert r.status_code == 200
        assert r.json()["status"] == "draft"
        # member sees nothing
        assert requests.get(_url("/members/next-meeting"), cookies=MEM_A).json() is None

    def test_empty_body_rejected(self, meeting_id):
        assert requests.put(_url(f"/admin/members/meetings/{meeting_id}/agenda"), cookies=ADMIN, headers=XRW,
                            json={"body": "  "}).status_code == 400

    def test_publish_visible(self, meeting_id):
        r = requests.put(_url(f"/admin/members/meetings/{meeting_id}/agenda"), cookies=ADMIN, headers=XRW,
                         json={"body": "Opening prayer\nTreasurer\nOld business", "time": "18:30", "location": "Zoom", "publish": True})
        assert r.status_code == 200
        assert r.json()["status"] == "published"
        nm = requests.get(_url("/members/next-meeting"), cookies=MEM_A).json()
        assert nm and nm["id"] == meeting_id
        assert nm["title"] == "QA Phase4 Meeting"
        assert "Opening prayer" in nm["agenda"]

    def test_suggestion_approve(self, meeting_id):
        r = requests.post(_url(f"/members/meetings/{meeting_id}/suggestions"), cookies=MEM_A, headers=XRW,
                         json={"text": "QA Discuss parking"})
        assert r.status_code == 200
        # Fetch meeting as admin to find sid
        r2 = requests.get(_url("/admin/members/meetings"), cookies=ADMIN).json()
        meeting = next(m for m in r2["meetings"] if m["id"] == meeting_id)
        sid = next(s["id"] for s in meeting["suggestions"] if s["text"] == "QA Discuss parking")
        # approve
        r3 = requests.post(_url(f"/admin/members/meetings/{meeting_id}/suggestions/{sid}"), cookies=ADMIN, headers=XRW,
                           json={"action": "approve"})
        assert r3.status_code == 200
        nm = requests.get(_url("/members/next-meeting"), cookies=MEM_A).json()
        assert "QA Discuss parking" in nm["approved_items"]

    def test_agenda_reminder_dedupe(self, meeting_id):
        import server, asyncio
        today = server._today_et()
        n1 = asyncio.get_event_loop().run_until_complete(server._send_agenda_reminders(today))
        n2 = asyncio.get_event_loop().run_until_complete(server._send_agenda_reminders(today))
        # First may be >=0 (emails to example.com might 422 but reminder_sent_at is still set), second must be 0.
        assert n2 == 0
        # Check reminder_sent_at set
        r2 = requests.get(_url("/admin/members/meetings"), cookies=ADMIN).json()
        meeting = next(m for m in r2["meetings"] if m["id"] == meeting_id)
        assert "reminder_sent_at" in meeting.get("agenda", {})


# ---------- Anniversaries ----------
class TestAnniversaries:
    def test_future_join_rejected(self):
        future = (datetime.now().date() + timedelta(days=30)).isoformat()
        r = requests.put(_url("/admin/members/qa_mem_b/joined"), cookies=ADMIN, headers=XRW,
                         json={"date": future})
        assert r.status_code == 400

    def test_invalid_date_rejected(self):
        assert requests.put(_url("/admin/members/qa_mem_b/joined"), cookies=ADMIN, headers=XRW,
                            json={"date": "not-a-date"}).status_code == 400

    def test_anniversary_today(self):
        today = datetime.now().date()
        anniv = today.replace(year=today.year - 3).isoformat()
        r = requests.put(_url("/admin/members/qa_mem_b/joined"), cookies=ADMIN, headers=XRW,
                         json={"date": anniv})
        assert r.status_code == 200
        rows = requests.get(_url("/members/anniversaries"), cookies=MEM_A).json()
        row = next((x for x in rows if x["user_id"] == "qa_mem_b"), None)
        assert row, rows
        assert row["years"] == 3
        assert row["today"] is True

    def test_anniversary_email_dedupe(self):
        import server, asyncio
        today = server._today_et()
        asyncio.get_event_loop().run_until_complete(server._send_member_anniversaries(today))
        n2 = asyncio.get_event_loop().run_until_complete(server._send_member_anniversaries(today))
        assert n2 == 0


# ---------- Referrers ----------
class TestReferrers:
    def test_fuzzy_suggestion(self):
        d = requests.get(_url("/admin/members/referrers"), cookies=ADMIN).json()
        a_row = next(r for r in d["rows"] if r["user_id"] == "qa_mem_a")
        # a applied with "Bea QA Testr" -> suggest "Bea QA Tester"
        assert a_row["suggestion"], a_row
        assert a_row["suggestion"]["user_id"] == "qa_mem_b"
        assert a_row["suggestion"]["score"] >= 0.6

    def test_self_link_rejected(self):
        r = requests.put(_url("/admin/members/qa_mem_a/referrer"), cookies=ADMIN, headers=XRW,
                         json={"referrer_id": "qa_mem_a"})
        assert r.status_code == 400

    def test_bogus_link_rejected(self):
        r = requests.put(_url("/admin/members/qa_mem_a/referrer"), cookies=ADMIN, headers=XRW,
                         json={"referrer_id": "no_such_user"})
        assert r.status_code == 400

    def test_link_and_preview(self):
        r = requests.put(_url("/admin/members/qa_mem_a/referrer"), cookies=ADMIN, headers=XRW,
                         json={"referrer_id": "qa_mem_b"})
        assert r.status_code == 200
        # Preview — current year works too
        y = datetime.now().year
        p = requests.get(_url(f"/admin/members/referrers/preview?year={y}"), cookies=ADMIN).json()
        assert p["year"] == y
        # groups structure
        assert isinstance(p.get("groups"), list)

    def test_notify_dedupe(self):
        y = datetime.now().year
        r1 = requests.post(_url("/admin/members/referrers/notify"), cookies=ADMIN, headers=XRW, json={"year": y})
        assert r1.status_code == 200
        r2 = requests.post(_url("/admin/members/referrers/notify"), cookies=ADMIN, headers=XRW, json={"year": y})
        assert r2.status_code == 200
        # second call same day → 0 sent (dedupe) OR original 0 if no unpaid balance
        assert r2.json()["sent"] == 0


# ---------- Regression: earlier admin tabs still work ----------
class TestRegression:
    @pytest.mark.parametrize("path", [
        "/admin/members",
        "/admin/members/meetings",
        "/admin/members/dues",
        "/admin/members/ballots",
        "/admin/members/collections",
        "/admin/members/december",
    ])
    def test_admin_tabs(self, path):
        assert requests.get(_url(path), cookies=ADMIN).status_code == 200

    @pytest.mark.parametrize("path", [
        "/members/me",
        "/members/announcements",
        "/members/threads",
        "/members/minutes",
        "/members/ballots",
        "/members/directory",
    ])
    def test_member_tabs(self, path):
        assert requests.get(_url(path), cookies=MEM_A).status_code == 200
