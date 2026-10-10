"""
E2E tests for iteration 10:
  - Volunteer thank-yous (once/day/email) + leaderboard opt-in
  - Story request results report
  - Program sign-up stage transitions + validation
  - Signup report contacted/enrolled percentages

Pre-req: qa_session.py up (session_token=qa_tok_123)
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO = MongoClient(os.environ["MONGO_URL"])
DB = MONGO[os.environ["DB_NAME"]]
TODAY = datetime.now(timezone.utc).date().isoformat()
YEAR = TODAY[:4]

ADMIN_COOKIES = {"session_token": "qa_tok_123"}
ADMIN_HEADERS = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def program():
    p = DB.programs.find_one({"slug": "wellness-workshops", "published": True}, {"_id": 0, "id": 1, "title": 1, "slug": 1})
    assert p, "wellness-workshops program must exist and be published"
    return p


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    # Teardown: remove @example.com test data + story seeds
    DB.volunteer_hours.delete_many({"email": {"$regex": "example.com$"}})
    DB.volunteer_thanks.delete_many({"email": {"$regex": "example.com$"}})
    DB.story_submissions.delete_many({"email": {"$regex": "example.com$"}})
    DB.submissions.delete_many({"data.email": {"$regex": "example.com$"}})


def _log_hours(name, email, program_id, leaderboard, hours=1.0):
    r = requests.post(f"{BASE}/api/volunteer-hours", json={
        "name": name, "email": email, "program_id": program_id,
        "date": TODAY, "hours": hours, "note": "QA", "leaderboard": leaderboard,
    })
    assert r.status_code == 200, r.text
    # fetch id via mongo (API doesn't return hid externally other than id)
    return r.json()["id"]


def _approve(hid):
    r = requests.post(f"{BASE}/api/admin/volunteer-hours/{hid}/approve",
                      cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
    assert r.status_code == 200, r.text


# ---------- thank-yous + leaderboard ----------
class TestThanksAndLeaderboard:
    def test_full_flow(self, program):
        email_in = f"adaeze_{uuid.uuid4().hex[:6]}@example.com"
        email_out = f"bea_{uuid.uuid4().hex[:6]}@example.com"
        hid1 = _log_hours("Adaeze Nwosu", email_in, program["id"], leaderboard=True, hours=2.0)
        hid2 = _log_hours("Bea Smith", email_out, program["id"], leaderboard=False, hours=1.5)

        _approve(hid1)
        _approve(hid2)

        # Give background task a sec
        import time; time.sleep(2)

        # volunteer_thanks: exactly one per email for today
        in_docs = list(DB.volunteer_thanks.find({"email": email_in, "day": TODAY}))
        out_docs = list(DB.volunteer_thanks.find({"email": email_out, "day": TODAY}))
        assert len(in_docs) == 1, f"opted-in email should have 1 thanks doc, got {len(in_docs)}"
        assert len(out_docs) == 1, f"non-opted email should still receive thanks doc, got {len(out_docs)}"

        # thanked:true marker on entries
        assert DB.volunteer_hours.find_one({"id": hid1})["thanked"] is True
        assert DB.volunteer_hours.find_one({"id": hid2})["thanked"] is True

        # Leaderboard shows only opted in with short name "Adaeze N."
        r = requests.get(f"{BASE}/api/volunteer-hours/leaderboard")
        assert r.status_code == 200
        items = r.json()["items"]
        names = [i["name"] for i in items]
        assert "Adaeze N." in names
        assert not any("Bea" in n for n in names), f"Non-opted volunteer must not appear: {names}"
        # hours value
        adaeze = next(i for i in items if i["name"] == "Adaeze N.")
        assert adaeze["hours"] >= 2.0

    def test_second_entry_same_day_does_not_create_second_thanks(self, program):
        email = f"carla_{uuid.uuid4().hex[:6]}@example.com"
        hid_a = _log_hours("Carla Jones", email, program["id"], leaderboard=False, hours=1.0)
        _approve(hid_a)
        import time; time.sleep(1.5)
        count_before = DB.volunteer_thanks.count_documents({"email": email, "day": TODAY})
        assert count_before == 1

        hid_b = _log_hours("Carla Jones", email, program["id"], leaderboard=False, hours=0.5)
        _approve(hid_b)
        time.sleep(1.5)
        count_after = DB.volunteer_thanks.count_documents({"email": email, "day": TODAY})
        assert count_after == 1, f"Second same-day approval must NOT create another thanks doc (got {count_after})"

        # The second entry should remain unthanked (thanked != true) until next day
        second = DB.volunteer_hours.find_one({"id": hid_b})
        assert second.get("thanked") is not True, f"Second entry thanked flag should NOT be True, got {second.get('thanked')}"


# ---------- Signup stages ----------
class TestSignupStages:
    def test_create_signup_and_transition_stages(self, program):
        email = f"signup_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(f"{BASE}/api/programs/wellness-workshops/signup", json={
            "name": "QA Signup", "email": email, "phone": "", "note": "QA"
        })
        assert r.status_code in (200, 201), r.text
        # fetch submission id
        sub = DB.submissions.find_one({"type": "program_signup", "data.email": email}, {"_id": 0, "id": 1, "stage": 1})
        assert sub, "signup submission must be created"
        sid = sub["id"]
        # default stage is 'new' (unset or 'new')
        assert sub.get("stage", "new") in (None, "new") or sub.get("stage") == "new"

        for stage in ["contacted", "enrolled"]:
            r = requests.put(f"{BASE}/api/admin/submissions/{sid}/stage",
                             json={"stage": stage}, cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
            assert r.status_code == 200, r.text
            persisted = DB.submissions.find_one({"id": sid}, {"_id": 0, "stage": 1})
            assert persisted["stage"] == stage

    def test_invalid_stage_rejected(self):
        # need a signup id
        sub = DB.submissions.find_one({"type": "program_signup", "data.email": {"$regex": "example.com$"}}, {"_id": 0, "id": 1})
        assert sub
        r = requests.put(f"{BASE}/api/admin/submissions/{sub['id']}/stage",
                         json={"stage": "bogus"}, cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400, f"expected 400 for invalid stage, got {r.status_code}"

    def test_signup_report_has_contacted_enrolled_pct(self, program):
        r = requests.get(f"{BASE}/api/admin/reports/program-signups?months=6",
                         cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        rows = data["rows"]
        ww = next((row for row in rows if row["program"] == program["title"]), None)
        assert ww, f"Wellness Workshops row missing in report"
        assert "contacted_pct" in ww and "enrolled_pct" in ww
        # Since we enrolled 1 of 1 in previous test, enrolled_pct should be 100
        assert ww["enrolled_pct"] == 100, f"expected 100% enrolled, got {ww}"
        assert ww["contacted_pct"] == 100, f"expected 100% contacted (reached=enrolled), got {ww}"


# ---------- Story request results ----------
class TestStoryRequestResults:
    def test_empty_shape(self):
        r = requests.get(f"{BASE}/api/admin/reports/story-requests",
                         cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        for k in ("invites", "submitted", "approved", "rate"):
            assert k in data

    def test_seeded_counts(self):
        email = f"story_{uuid.uuid4().hex[:6]}@example.com"
        sid = str(uuid.uuid4())
        DB.submissions.insert_one({
            "id": sid, "type": "program_signup",
            "data": {"email": email, "program": "Wellness Workshops"},
            "story_request_sent": True, "story_request_at": "2026-01-01T00:00:00+00:00",
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        DB.story_submissions.insert_one({
            "id": str(uuid.uuid4()), "email": email, "status": "approved",
            "created_at": "2026-02-01T00:00:00+00:00",
        })
        try:
            r = requests.get(f"{BASE}/api/admin/reports/story-requests",
                             cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
            data = r.json()
            assert data["invites"] >= 1
            assert data["submitted"] >= 1
            assert data["approved"] >= 1
            assert data["rate"] > 0
        finally:
            DB.submissions.delete_one({"id": sid})
            DB.story_submissions.delete_many({"email": email})


# ---------- Regression ----------
class TestRegression:
    def test_hours_summary_still_works(self):
        r = requests.get(f"{BASE}/api/volunteer-hours/summary")
        assert r.status_code == 200
        d = r.json()
        for k in ("total_hours", "volunteers", "by_program"):
            assert k in d

    def test_admin_hours_still_lists(self):
        r = requests.get(f"{BASE}/api/admin/volunteer-hours",
                         cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200
        assert "items" in r.json()
