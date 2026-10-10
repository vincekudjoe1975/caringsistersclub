"""
Iter-19: Attendance, seat release, low-rating alerts, program ratings.

Pre: `python3 /app/backend/tests/qa_session.py up` (cookie session_token=qa_tok_123).
Mutating admin requests use header X-Requested-With: XMLHttpRequest.
"""
import os
import sys
import uuid
import asyncio
import importlib
import time
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


QA_PID = "qa19-prog-" + uuid.uuid4().hex[:8]
QA_SLUG = "qa19-session-" + uuid.uuid4().hex[:6]
QA_PROG_BASE = {
    "id": QA_PID, "slug": QA_SLUG, "title": "QA19 Session Program",
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
    MDB.programs.delete_many({"id": {"$regex": "^qa19-"}})
    MDB.programs.delete_many({"slug": {"$regex": "^qa19-"}})
    MDB.submissions.delete_many({"data.email": {"$regex": "qa19.*@example.com$"}})
    MDB.submissions.delete_many({"program_id": {"$regex": "^qa19-"}})
    MDB.session_reminders.delete_many({"program_id": {"$regex": "^qa19-"}})
    MDB.session_feedback.delete_many({"program_id": {"$regex": "^qa19-"}})
    MDB.settings.update_one({"key": "site"}, {"$set": {"fb_alert_threshold": 2, "staff_notify_email": "caringsistersclub@gmail.com"}}, upsert=True)


def _set_dates(start=None, end=None):
    MDB.programs.update_one({"id": QA_PID}, {"$set": {"start_date": start or "", "end_date": end or "", "schedule": "Tue 6-8pm"}})


def _seed_sub(email, name, waitlist=False, stage=None):
    doc = {
        "id": "qa19-sub-" + uuid.uuid4().hex[:8], "type": "program_signup",
        "program_id": QA_PID, "waitlist": waitlist,
        "data": {"name": name, "email": email, "program": "QA19", "program_slug": QA_SLUG},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if stage:
        doc["stage"] = stage
    MDB.submissions.insert_one(doc)
    return doc["id"]


# =============== Attendance ===============
class TestAttendance:
    @pytest.fixture(autouse=True)
    def _reset(self):
        MDB.submissions.delete_many({"program_id": QA_PID})
        _set_dates(start=(date.today() + timedelta(days=5)).isoformat(),
                   end=(date.today() + timedelta(days=5)).isoformat())
        self.sid1 = _seed_sub("qa19.a@example.com", "Alice Att")
        self.sid2 = _seed_sub("qa19.b@example.com", "Bob Att")
        self.sid3 = _seed_sub("qa19.c@example.com", "Carla Att")
        self.wid = _seed_sub("qa19.wait@example.com", "Wait Att", waitlist=True)
        yield

    def test_get_attendance_returns_seated_only(self, api):
        r = api.get(f"{BASE}/api/admin/programs/{QA_PID}/attendance")
        assert r.status_code == 200
        d = r.json()
        assert d["program"] == "QA19 Session Program"
        assert len(d["items"]) == 3
        emails = {i["email"] for i in d["items"]}
        assert "qa19.wait@example.com" not in emails
        for i in d["items"]:
            assert i["attendance"] is None
            assert set(["id", "name", "email", "attendance"]).issubset(i.keys())

    def test_post_attendance_updates_valid(self, api):
        body = {"updates": {self.sid1: "attended", self.sid2: "no_show"}}
        r = api.post(f"{BASE}/api/admin/programs/{QA_PID}/attendance", json=body)
        assert r.status_code == 200
        assert r.json()["updated"] == 2
        # Verify persistence via GET
        d = api.get(f"{BASE}/api/admin/programs/{QA_PID}/attendance").json()
        m = {i["id"]: i["attendance"] for i in d["items"]}
        assert m[self.sid1] == "attended"
        assert m[self.sid2] == "no_show"
        assert m[self.sid3] is None

    def test_post_attendance_invalid_value_400(self, api):
        r = api.post(f"{BASE}/api/admin/programs/{QA_PID}/attendance",
                     json={"updates": {self.sid1: "maybe"}})
        assert r.status_code == 400

    def test_post_attendance_all_attended(self, api):
        r = api.post(f"{BASE}/api/admin/programs/{QA_PID}/attendance", json={"all": "attended"})
        assert r.status_code == 200
        assert r.json()["updated"] >= 3
        d = api.get(f"{BASE}/api/admin/programs/{QA_PID}/attendance").json()
        for i in d["items"]:
            assert i["attendance"] == "attended"

    def test_post_attendance_clears_with_null(self, api):
        api.post(f"{BASE}/api/admin/programs/{QA_PID}/attendance",
                 json={"updates": {self.sid1: "attended"}})
        r = api.post(f"{BASE}/api/admin/programs/{QA_PID}/attendance",
                     json={"updates": {self.sid1: None}})
        assert r.status_code == 200
        d = api.get(f"{BASE}/api/admin/programs/{QA_PID}/attendance").json()
        m = {i["id"]: i["attendance"] for i in d["items"]}
        assert m[self.sid1] is None

    def test_attendance_report_row(self, api):
        api.post(f"{BASE}/api/admin/programs/{QA_PID}/attendance",
                 json={"updates": {self.sid1: "attended", self.sid2: "no_show"}})
        r = api.get(f"{BASE}/api/admin/reports/attendance")
        assert r.status_code == 200
        rows = {x["id"]: x for x in r.json()["items"]}
        assert QA_PID in rows
        row = rows[QA_PID]
        assert row["seated"] == 3
        assert row["attended"] == 1
        assert row["no_show"] == 1
        assert row["unmarked"] == 1
        assert row["attendance_pct"] == 50


# =============== Feedback respects attendance ===============
class TestFeedbackAttendanceFilter:
    def test_feedback_only_to_attended_when_marked(self, api):
        MDB.submissions.delete_many({"program_id": QA_PID})
        MDB.session_feedback.delete_many({"program_id": QA_PID})
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        _set_dates(start=yesterday, end=yesterday)
        s1 = _seed_sub("qa19.att1@example.com", "A1")
        s2 = _seed_sub("qa19.ns1@example.com", "A2")
        _seed_sub("qa19.un1@example.com", "A3")
        api.post(f"{BASE}/api/admin/programs/{QA_PID}/attendance",
                 json={"updates": {s1: "attended", s2: "no_show"}})
        _run(server._send_session_feedback())
        docs = list(MDB.session_feedback.find({"program_id": QA_PID}, {"_id": 0, "submission_id": 1}))
        assert len(docs) == 1
        assert docs[0]["submission_id"] == s1

    def test_feedback_to_all_seated_when_no_attendance(self, api):
        # Second program, no attendance marked
        pid = "qa19-prog2-" + uuid.uuid4().hex[:6]
        slug = "qa19-s2-" + uuid.uuid4().hex[:4]
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        MDB.programs.insert_one({**QA_PROG_BASE, "id": pid, "slug": slug,
                                 "start_date": yesterday, "end_date": yesterday})
        for e in ["qa19.p2a@example.com", "qa19.p2b@example.com"]:
            MDB.submissions.insert_one({
                "id": "qa19-s-" + uuid.uuid4().hex[:8], "type": "program_signup",
                "program_id": pid, "waitlist": False,
                "data": {"name": "N", "email": e, "program": "x", "program_slug": slug},
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        _run(server._send_session_feedback())
        n = MDB.session_feedback.count_documents({"program_id": pid})
        assert n == 2


# =============== Seat release ===============
class TestSeatRelease:
    def test_release_full_flow(self, api):
        MDB.submissions.delete_many({"program_id": QA_PID})
        MDB.session_reminders.delete_many({"program_id": QA_PID})
        today = datetime.now(timezone.utc).date()
        _set_dates(start=(today + timedelta(days=2)).isoformat(),
                   end=(today + timedelta(days=2)).isoformat())
        MDB.programs.update_one({"id": QA_PID}, {"$set": {"capacity": 1}})
        seated_id = _seed_sub("qa19.rel@example.com", "Rel Seat")
        wait_id = _seed_sub("qa19.wl@example.com", "Wl Seat", waitlist=True)
        # Reminders assign a release_token on seated submissions
        _run(server._send_session_reminders())
        sub = MDB.submissions.find_one({"id": seated_id}, {"_id": 0})
        tok = sub.get("release_token")
        assert tok and len(tok) > 20

        # GET info
        r = requests.get(f"{BASE}/api/seat-release", params={"token": tok})
        assert r.status_code == 200
        d = r.json()
        assert d["program"] == "QA19 Session Program"
        assert d["released"] is False
        assert d["name"] == "Rel"

        # Bad token -> 404
        r = requests.get(f"{BASE}/api/seat-release", params={"token": "bogus-token-xxx"})
        assert r.status_code == 404

        # POST release
        r = requests.post(f"{BASE}/api/seat-release", json={"token": tok})
        assert r.status_code == 200
        assert r.json()["released"] is True
        s2 = MDB.submissions.find_one({"id": seated_id}, {"_id": 0})
        assert s2["released"] is True
        assert s2["stage"] == "not_fit"
        assert s2["data"]["list"] == "Cancelled by sister"

        # Idempotent repeat
        r2 = requests.post(f"{BASE}/api/seat-release", json={"token": tok})
        assert r2.status_code == 200
        assert r2.json()["released"] is True

        # Waitlist offered seat via _fill_seats (claim mode -> open offer)
        time.sleep(3)
        w = MDB.submissions.find_one({"id": wait_id}, {"_id": 0})
        # Offer indicated by offer_status (open) OR waitlist flipped. Check offer_status.
        assert w.get("offer_status") == "open", f"expected open offer, got {w}"


# =============== Low-rating alerts ===============
class TestFeedbackAlerts:
    def test_get_default_threshold_2(self, api):
        # Ensure default
        MDB.settings.update_one({"key": "site"}, {"$set": {"fb_alert_threshold": 2}}, upsert=True)
        r = api.get(f"{BASE}/api/admin/feedback-alert-settings")
        assert r.status_code == 200
        assert r.json()["threshold"] == 2

    def test_put_threshold_3_ok(self, api):
        r = api.put(f"{BASE}/api/admin/feedback-alert-settings", json={"threshold": 3})
        assert r.status_code == 200
        assert r.json()["threshold"] == 3

    def test_put_threshold_4_bad_request(self, api):
        r = api.put(f"{BASE}/api/admin/feedback-alert-settings", json={"threshold": 4})
        assert r.status_code == 400

    def test_feedback_alert_fires_once(self, api):
        # Reset threshold to 2
        api.put(f"{BASE}/api/admin/feedback-alert-settings", json={"threshold": 2})
        MDB.session_feedback.delete_many({"program_id": QA_PID})

        # Case 1: rating 2 -> alerted
        tok1 = "qa19tok-" + uuid.uuid4().hex[:16]
        MDB.session_feedback.insert_one({
            "id": str(uuid.uuid4()), "token": tok1, "submission_id": "x1",
            "program_id": QA_PID, "email": "qa19.fb1@example.com",
            "name": "Fb One", "sent_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{BASE}/api/feedback", json={"token": tok1, "rating": 2, "recommend": True, "comment": "meh"})
        assert r.status_code == 200
        time.sleep(1)
        d = MDB.session_feedback.find_one({"token": tok1}, {"_id": 0})
        assert d.get("alerted") is True

        # Case 2: rating 5, recommend True -> NOT alerted
        tok2 = "qa19tok-" + uuid.uuid4().hex[:16]
        MDB.session_feedback.insert_one({
            "id": str(uuid.uuid4()), "token": tok2, "submission_id": "x2",
            "program_id": QA_PID, "email": "qa19.fb2@example.com",
            "name": "Fb Two", "sent_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{BASE}/api/feedback", json={"token": tok2, "rating": 5, "recommend": True})
        assert r.status_code == 200
        d = MDB.session_feedback.find_one({"token": tok2}, {"_id": 0})
        assert not d.get("alerted")

        # Case 3: rating 5, recommend False -> alerted
        tok3 = "qa19tok-" + uuid.uuid4().hex[:16]
        MDB.session_feedback.insert_one({
            "id": str(uuid.uuid4()), "token": tok3, "submission_id": "x3",
            "program_id": QA_PID, "email": "qa19.fb3@example.com",
            "name": "Fb Three", "sent_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{BASE}/api/feedback", json={"token": tok3, "rating": 5, "recommend": False})
        assert r.status_code == 200
        d = MDB.session_feedback.find_one({"token": tok3}, {"_id": 0})
        assert d.get("alerted") is True

        # Case 4: re-submit case 1 -> alerted stays True, no new alert fires (still just one)
        r = requests.post(f"{BASE}/api/feedback", json={"token": tok1, "rating": 1, "recommend": False})
        assert r.status_code == 200
        d = MDB.session_feedback.find_one({"token": tok1}, {"_id": 0})
        assert d.get("alerted") is True  # unchanged


# =============== Program ratings ===============
class TestProgramRatings:
    def test_ratings_shown_at_min_3(self, api):
        MDB.session_feedback.delete_many({"program_id": {"$regex": "^qa19-"}})
        # Create cloned program sharing root QA_PID
        clone_pid = "qa19-clone-" + uuid.uuid4().hex[:6]
        clone_slug = "qa19-clone-" + uuid.uuid4().hex[:4]
        MDB.programs.insert_one({**QA_PROG_BASE, "id": clone_pid, "slug": clone_slug,
                                 "title": "QA19 Clone", "cloned_from": QA_PID})

        # Only 2 ratings -> not shown
        for rating in [5, 4]:
            MDB.session_feedback.insert_one({
                "id": str(uuid.uuid4()), "token": "t-" + uuid.uuid4().hex,
                "program_id": QA_PID, "email": "x@example.com", "name": "X",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "rating": rating,
            })
        r = requests.get(f"{BASE}/api/programs/{QA_SLUG}")
        assert r.status_code == 200
        d = r.json()
        assert "rating_avg" not in d
        assert "rating_count" not in d

        # Add 3rd rating under clone -> family total 3 -> fields present
        MDB.session_feedback.insert_one({
            "id": str(uuid.uuid4()), "token": "t-" + uuid.uuid4().hex,
            "program_id": clone_pid, "email": "y@example.com", "name": "Y",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "rating": 5,
        })

        # Both root and clone programs should show rating_avg 4.7, count 3
        r1 = requests.get(f"{BASE}/api/programs/{QA_SLUG}").json()
        assert r1.get("rating_count") == 3
        assert r1.get("rating_avg") == 4.7

        r2 = requests.get(f"{BASE}/api/programs/{clone_slug}").json()
        assert r2.get("rating_count") == 3
        assert r2.get("rating_avg") == 4.7

        # /api/programs listing also carries it
        items = requests.get(f"{BASE}/api/programs").json()["items"]
        for p in items:
            if p["id"] in (QA_PID, clone_pid):
                assert p.get("rating_count") == 3
                assert p.get("rating_avg") == 4.7

        MDB.programs.delete_one({"id": clone_pid})
