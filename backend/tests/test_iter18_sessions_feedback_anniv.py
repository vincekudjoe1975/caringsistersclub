"""
Iter-18: Session calendar files, session reminders, session feedback, anniversary shout-outs.

Preconditions: `python3 /app/backend/tests/qa_session.py up` (admin cookie session_token=qa_tok_123).
Mutating admin requests require header X-Requested-With: XMLHttpRequest.
"""
import os
import sys
import uuid
import asyncio
import importlib
from datetime import datetime, date, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MDB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
COOKIES = {"session_token": "qa_tok_123"}
HDR = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}

sys.path.insert(0, "/app/backend")
server = importlib.import_module("server")

_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


def _run(coro):
    return _LOOP.run_until_complete(coro)


# A dedicated QA program slug + id so we don't touch real ones
QA_PID = "qa18-prog-" + uuid.uuid4().hex[:8]
QA_SLUG = "qa18-session-" + uuid.uuid4().hex[:6]
QA_PROG_BASE = {
    "id": QA_PID, "slug": QA_SLUG, "title": "QA18 Session Program",
    "category": "QA", "summary": "qa", "body": "", "goals": [], "impact": [],
    "cta_text": "Join", "cta_link": "/volunteer", "image_url": "",
    "published": True, "gallery": [], "testimonials": [],
    "home_testimonial_ids": [], "capacity": 10, "waitlist_mode": "claim",
    "start_date": "", "end_date": "", "schedule": "",
}


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update(HDR)
    s.cookies.update(COOKIES)
    return s


@pytest.fixture(scope="module", autouse=True)
def qa_program():
    MDB.programs.delete_one({"id": QA_PID})
    MDB.programs.insert_one({**QA_PROG_BASE})
    yield
    # Full cleanup
    MDB.programs.delete_one({"id": QA_PID})
    MDB.submissions.delete_many({"program_id": QA_PID})
    MDB.submissions.delete_many({"data.email": {"$regex": "qa18.*@example.com$"}})
    MDB.session_reminders.delete_many({"program_id": QA_PID})
    MDB.session_feedback.delete_many({"program_id": QA_PID})
    MDB.volunteer_hours.delete_many({"email": {"$regex": "qa18.*@example.com$"}})
    MDB.settings.update_one({"key": "site"}, {"$set": {"badge_wall_mode": "optin"}}, upsert=True)


def _set_dates(start=None, end=None):
    MDB.programs.update_one({"id": QA_PID}, {"$set": {"start_date": start or "", "end_date": end or "", "schedule": "Tue 6-8pm"}})


def _seed_sub(email, name, waitlist=False, stage=None):
    doc = {
        "id": "qa18-sub-" + uuid.uuid4().hex[:8], "type": "program_signup",
        "program_id": QA_PID, "waitlist": waitlist,
        "data": {"name": name, "email": email, "program": "QA18", "program_slug": QA_SLUG},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if stage:
        doc["stage"] = stage
    MDB.submissions.insert_one(doc)
    return doc["id"]


# ======= Public session calendar files =======
class TestSessionCalendarFiles:
    def test_sessions_ics_includes_future_published(self, api):
        _set_dates(start=(date.today() + timedelta(days=10)).isoformat(),
                   end=(date.today() + timedelta(days=12)).isoformat())
        r = api.get(f"{BASE}/api/sessions.ics")
        assert r.status_code == 200
        assert "text/calendar" in r.headers.get("content-type", "")
        txt = r.text
        assert "BEGIN:VCALENDAR" in txt and "END:VCALENDAR" in txt
        assert "X-WR-CALNAME" in txt
        # VEVENT for our program
        assert f"session-{QA_PID}@caringsistersclub" in txt
        # DTSTART all-day & DTEND = end+1
        s = (date.today() + timedelta(days=10)).strftime("%Y%m%d")
        e_plus = (date.today() + timedelta(days=13)).strftime("%Y%m%d")
        assert f"DTSTART;VALUE=DATE:{s}" in txt
        assert f"DTEND;VALUE=DATE:{e_plus}" in txt

    def test_sessions_ics_excludes_undated_and_unpublished(self, api):
        # Make another QA program with no dates - should NOT appear
        pid2 = "qa18-prog2-" + uuid.uuid4().hex[:6]
        MDB.programs.insert_one({**QA_PROG_BASE, "id": pid2, "slug": "qa18-s2-" + uuid.uuid4().hex[:4], "start_date": ""})
        # Unpublished with dates - should NOT appear
        pid3 = "qa18-prog3-" + uuid.uuid4().hex[:6]
        MDB.programs.insert_one({**QA_PROG_BASE, "id": pid3, "slug": "qa18-s3-" + uuid.uuid4().hex[:4],
                                 "published": False, "start_date": (date.today() + timedelta(days=5)).isoformat()})
        try:
            r = api.get(f"{BASE}/api/sessions.ics")
            txt = r.text
            assert f"session-{pid2}" not in txt
            assert f"session-{pid3}" not in txt
        finally:
            MDB.programs.delete_one({"id": pid2})
            MDB.programs.delete_one({"id": pid3})

    def test_single_session_calendar_file(self, api):
        r = api.get(f"{BASE}/api/sessions/{QA_SLUG}/calendar.ics")
        assert r.status_code == 200
        assert "text/calendar" in r.headers.get("content-type", "")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd and ".ics" in cd
        assert "BEGIN:VEVENT" in r.text

    def test_undated_slug_returns_404(self, api):
        # temp program with no dates
        pid = "qa18-nod-" + uuid.uuid4().hex[:6]
        slug = "qa18-nod-" + uuid.uuid4().hex[:6]
        MDB.programs.insert_one({**QA_PROG_BASE, "id": pid, "slug": slug, "start_date": ""})
        try:
            r = api.get(f"{BASE}/api/sessions/{slug}/calendar.ics")
            assert r.status_code == 404
        finally:
            MDB.programs.delete_one({"id": pid})


# ======= Session reminders =======
class TestSessionReminders:
    def test_2day_reminder_only_for_seated(self):
        # cleanup
        MDB.submissions.delete_many({"program_id": QA_PID})
        MDB.session_reminders.delete_many({"program_id": QA_PID})
        today = datetime.now(timezone.utc).date()
        _set_dates(start=(today + timedelta(days=2)).isoformat(),
                   end=(today + timedelta(days=2)).isoformat())
        seated = _seed_sub("qa18.seat@example.com", "Qa Seat")
        _seed_sub("qa18.wait@example.com", "Qa Wait", waitlist=True)
        _seed_sub("qa18.notfit@example.com", "Qa NotFit", stage="not_fit")

        n = _run(server._send_session_reminders())
        rems = list(MDB.session_reminders.find({"program_id": QA_PID, "kind": "2day"}))
        assert len(rems) == 1
        assert rems[0]["submission_id"] == seated

        # idempotent
        _run(server._send_session_reminders())
        rems2 = list(MDB.session_reminders.find({"program_id": QA_PID, "kind": "2day"}))
        assert len(rems2) == 1

    def test_dayof_only_after_11utc(self):
        today = datetime.now(timezone.utc).date()
        _set_dates(start=today.isoformat(), end=today.isoformat())
        MDB.session_reminders.delete_many({"program_id": QA_PID, "kind": "dayof"})

        # hour 8 -> no dayof
        _run(server._send_session_reminders(now=datetime(today.year, today.month, today.day, 8, 0, tzinfo=timezone.utc)))
        assert MDB.session_reminders.count_documents({"program_id": QA_PID, "kind": "dayof"}) == 0

        # hour 12 -> dayof for seated only
        _run(server._send_session_reminders(now=datetime(today.year, today.month, today.day, 12, 0, tzinfo=timezone.utc)))
        rems = list(MDB.session_reminders.find({"program_id": QA_PID, "kind": "dayof"}))
        assert len(rems) == 1
        sub = MDB.submissions.find_one({"id": rems[0]["submission_id"]})
        assert sub["data"]["email"] == "qa18.seat@example.com"


# ======= Session feedback =======
class TestSessionFeedback:
    @pytest.fixture(scope="class", autouse=True)
    def _seed(self):
        # Clear earlier reminders-era subs
        MDB.submissions.delete_many({"program_id": QA_PID})
        MDB.session_feedback.delete_many({"program_id": QA_PID})
        today = datetime.now(timezone.utc).date()
        _set_dates(start=(today - timedelta(days=2)).isoformat(),
                   end=(today - timedelta(days=1)).isoformat())
        self._sid = _seed_sub("qa18.fb@example.com", "Qa Feedback")
        yield

    def test_send_creates_feedback_doc(self, api):
        _run(server._send_session_feedback())
        docs = list(MDB.session_feedback.find({"program_id": QA_PID}))
        assert len(docs) == 1
        assert docs[0].get("token")
        # rerun -> idempotent
        _run(server._send_session_feedback())
        assert MDB.session_feedback.count_documents({"program_id": QA_PID}) == 1

    def test_get_feedback_token(self, api):
        tok = MDB.session_feedback.find_one({"program_id": QA_PID})["token"]
        r = api.get(f"{BASE}/api/feedback?token={tok}")
        assert r.status_code == 200
        data = r.json()
        assert data["submitted"] is False
        assert "program" in data and "name" in data

    def test_bad_token_404(self, api):
        r = api.get(f"{BASE}/api/feedback?token=NOPE_NOPE")
        assert r.status_code == 404

    def test_submit_bad_rating(self, api):
        tok = MDB.session_feedback.find_one({"program_id": QA_PID})["token"]
        r = api.post(f"{BASE}/api/feedback", json={"token": tok, "rating": 0, "recommend": True, "comment": ""})
        assert r.status_code == 400

    def test_submit_success_and_reflect(self, api):
        tok = MDB.session_feedback.find_one({"program_id": QA_PID})["token"]
        r = api.post(f"{BASE}/api/feedback", json={"token": tok, "rating": 5, "recommend": True, "comment": "Loved it"})
        assert r.status_code == 200
        r2 = api.get(f"{BASE}/api/feedback?token={tok}")
        assert r2.json()["submitted"] is True

    def test_admin_report_no_pii(self, api):
        r = api.get(f"{BASE}/api/admin/reports/session-feedback")
        assert r.status_code == 200
        rows = r.json()["items"]
        row = next((x for x in rows if x["program_id"] == QA_PID), None)
        assert row is not None, "row for QA program missing"
        assert row["sent"] == 1
        assert row["responses"] == 1
        assert row["response_rate"] == 100.0
        assert row["avg_rating"] == 5
        assert row["recommend_pct"] == 100
        assert row["comments"] and "id" in row["comments"][0]
        # no PII leak
        import json as _json
        serialized = _json.dumps(row)
        assert "email" not in serialized.lower()
        assert "token" not in serialized.lower()
        assert "qa18.fb@example.com" not in serialized

    def test_feature_as_testimonial(self, api):
        row = next(x for x in api.get(f"{BASE}/api/admin/reports/session-feedback").json()["items"] if x["program_id"] == QA_PID)
        cid = row["comments"][0]["id"]
        r = api.post(f"{BASE}/api/admin/feedback/{cid}/feature")
        assert r.status_code == 200, r.text
        p = MDB.programs.find_one({"id": QA_PID}, {"testimonials": 1})
        assert any(t.get("quote") == "Loved it" for t in p.get("testimonials") or [])
        # second call -> 409
        r2 = api.post(f"{BASE}/api/admin/feedback/{cid}/feature")
        assert r2.status_code == 409
        # unknown id -> 404
        r3 = api.post(f"{BASE}/api/admin/feedback/does-not-exist/feature")
        assert r3.status_code == 404


# ======= Anniversary shout-outs =======
class TestAnniversaries:
    @pytest.fixture(scope="class", autouse=True)
    def _seed(self):
        MDB.volunteer_hours.delete_many({"email": {"$regex": "qa18.*@example.com$"}})
        today = date.today()
        # 1 year ago same month, leaderboard True
        d1 = date(today.year - 1, today.month, min(today.day, 28)).isoformat()
        # 3 years ago same month, leaderboard False
        d3 = date(today.year - 3, today.month, min(today.day, 28)).isoformat()
        MDB.volunteer_hours.insert_many([
            {"id": "qa18-vh-1", "email": "qa18.anniv.opt@example.com", "name": "Alice QA18",
             "status": "approved", "date": d1, "hours": 5, "leaderboard": True,
             "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": "qa18-vh-2", "email": "qa18.anniv.no@example.com", "name": "Bea QA18",
             "status": "approved", "date": d3, "hours": 4, "leaderboard": False,
             "created_at": datetime.now(timezone.utc).isoformat()},
        ])
        MDB.settings.update_one({"key": "site"}, {"$set": {"badge_wall_mode": "optin"}}, upsert=True)
        yield

    def test_optin_mode_only_shows_optin(self, api):
        r = api.get(f"{BASE}/api/volunteer-hours/anniversaries")
        assert r.status_code == 200
        data = r.json()
        assert data["month"] == date.today().strftime("%B")
        names = [a["name"] for a in data["items"]]
        assert any("Alice" in n for n in names)
        assert not any("Bea" in n for n in names)
        for a in data["items"]:
            assert "email" not in a
            assert "years" in a and "day" in a

    def test_all_mode_shows_everyone(self, api):
        r = api.put(f"{BASE}/api/admin/badge-wall", json={"mode": "all"})
        assert r.status_code == 200
        r2 = api.get(f"{BASE}/api/volunteer-hours/anniversaries")
        names = [a["name"] for a in r2.json()["items"]]
        assert any("Alice" in n for n in names)
        assert any("Bea" in n for n in names)
        # reset
        api.put(f"{BASE}/api/admin/badge-wall", json={"mode": "optin"})
