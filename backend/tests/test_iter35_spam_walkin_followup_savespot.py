"""Iteration 35: spam-card data, walk-ins, session absent follow-ups, save-my-spot, session insights/report walk-ins."""
import os
import sys
import uuid
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

sys.path.insert(0, "/app/backend")

ADMIN_COOKIE = {"session_token": "qa_tok_123"}
ADMIN_HEADERS = {"X-Requested-With": "XMLHttpRequest"}
QA_EMAIL_PREFIX = "qa.person"


# --------------------------- fixtures ---------------------------
@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def program(db):
    """Pick an existing published program for seeding sessions."""
    p = db.programs.find_one({"published": True}, {"_id": 0})
    assert p, "No published program found"
    return p


@pytest.fixture(scope="module")
def cleanup(db):
    yield
    db.submissions.delete_many({"data.email": {"$regex": "^qa.person"}})
    db.submissions.delete_many({"data.email": {"$regex": "^qa.rl@example.com$"}})
    db.program_sessions.delete_many({"location": "QA Hall"})
    db.noshow_emails.delete_many({"email": {"$regex": "^qa.person"}})
    db.spot_tokens.delete_many({"token": {"$regex": "^qa-"}})
    db.rate_hits.delete_many({"key": {"$regex": "^checkout:"}})
    db.blocked_attempts.delete_many({"bucket": "checkout"})
    db.payment_transactions.delete_many({"donor_email": "qa.rl@example.com"})


# --------------------------- Spam summary ---------------------------
class TestSpamSummary:
    def test_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/admin/security/spam")
        assert r.status_code in (401, 403)

    def test_generate_blocks_and_summary(self, db, cleanup):
        # clear baseline so counts are predictable
        db.rate_hits.delete_many({"key": {"$regex": "^checkout:"}})
        before = db.blocked_attempts.count_documents({"bucket": "checkout"})
        payload = {"amount": 5, "frequency": "one-time",
                   "origin_url": BASE_URL, "donor_email": "qa.rl@example.com"}
        statuses = []
        for _ in range(10):
            r = requests.post(f"{BASE_URL}/api/payments/checkout", json=payload)
            statuses.append(r.status_code)
        assert 429 in statuses, f"Expected a 429 among {statuses}"
        after = db.blocked_attempts.count_documents({"bucket": "checkout"})
        assert after > before, "blocked_attempts not logged"

        r = requests.get(f"{BASE_URL}/api/admin/security/spam", cookies=ADMIN_COOKIE)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "days" in d and len(d["days"]) == 7
        for day in d["days"]:
            assert "date" in day and "count" in day
        assert isinstance(d["today"], int)
        assert isinstance(d["week_total"], int)
        assert d["week_total"] >= (after - before)
        assert d["today"] >= 1
        assert d["top_form"] is not None
        # checkout bucket maps to a human label; just assert it has one
        assert "label" in d["top_form"] and "count" in d["top_form"]
        assert d["top_form"]["count"] >= 1


# --------------------------- Walk-ins ---------------------------
@pytest.fixture(scope="module")
def future_session(db, program, cleanup):
    sid = str(uuid.uuid4())
    date = (datetime.utcnow() + timedelta(days=14)).date().isoformat()
    db.program_sessions.insert_one({
        "id": sid, "program_id": program["id"], "date": date,
        "start_time": "10:00", "end_time": "11:00",
        "location": "QA Hall", "seats": 1, "notes": "", "created_at": datetime.utcnow().isoformat()
    })
    return sid


class TestWalkIn:
    def test_requires_admin(self, future_session):
        r = requests.post(f"{BASE_URL}/api/admin/sessions/{future_session}/walkin",
                          json={"name": "Anon"})
        assert r.status_code in (401, 403)

    def test_name_required(self, future_session):
        r = requests.post(f"{BASE_URL}/api/admin/sessions/{future_session}/walkin",
                          json={"name": "   "}, cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_invalid_email_rejected(self, future_session):
        r = requests.post(f"{BASE_URL}/api/admin/sessions/{future_session}/walkin",
                          json={"name": "QA Walkin", "email": "notanemail"},
                          cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_walkin_added_even_when_full(self, db, future_session):
        # fill the 1-seat session with a regular signup first
        db.submissions.insert_one({
            "id": str(uuid.uuid4()), "type": "program_signup",
            "program_id": db.program_sessions.find_one({"id": future_session})["program_id"],
            "session_id": future_session, "waitlist": False, "read": False,
            "data": {"name": "QA Full", "email": "qa.person0@example.com"},
            "created_at": datetime.utcnow().isoformat()
        })
        # now session is full - walk-in should still succeed
        r = requests.post(f"{BASE_URL}/api/admin/sessions/{future_session}/walkin",
                          json={"name": "Walker One", "email": "qa.person1@example.com",
                                "phone": "555-1212"},
                          cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "Walker One"
        assert data["email"] == "qa.person1@example.com"
        assert data["attendance"] == "attended"
        assert data["walk_in"] is True

        # verify persistence
        row = db.submissions.find_one({"id": data["id"]}, {"_id": 0})
        assert row is not None
        assert row["walk_in"] is True
        assert row["attendance"] == "attended"
        assert row["session_id"] == future_session

    def test_walkin_without_email(self, db, future_session):
        r = requests.post(f"{BASE_URL}/api/admin/sessions/{future_session}/walkin",
                          json={"name": "No Email Walker"},
                          cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ""
        assert d["walk_in"] is True

    def test_404_for_bad_session(self):
        r = requests.post(f"{BASE_URL}/api/admin/sessions/does-not-exist/walkin",
                          json={"name": "X"}, cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r.status_code == 404

    def test_session_report_counts_walkins(self, db, program, future_session):
        r = requests.get(f"{BASE_URL}/api/admin/programs/{program['id']}/session-report",
                         cookies=ADMIN_COOKIE)
        assert r.status_code == 200
        row = next((s for s in r.json()["sessions"] if s["id"] == future_session), None)
        assert row is not None
        # 2 walk-ins added above
        assert row["walk_ins"] >= 2
        # walk-ins count as attended
        assert row["attended"] >= 2


# --------------------------- Save-my-spot & follow-ups ---------------------------
@pytest.fixture(scope="module")
def past_session_with_absents(db, program):
    """Past session (2 days ago) with 2 no-show sign-ups."""
    sid = str(uuid.uuid4())
    date = (datetime.utcnow() - timedelta(days=2)).date().isoformat()
    db.program_sessions.insert_one({
        "id": sid, "program_id": program["id"], "date": date,
        "start_time": "10:00", "end_time": "11:00",
        "location": "QA Hall", "seats": 10, "notes": "",
        "created_at": datetime.utcnow().isoformat()
    })
    for i in (2, 3):
        db.submissions.insert_one({
            "id": str(uuid.uuid4()), "type": "program_signup",
            "program_id": program["id"], "session_id": sid, "waitlist": False,
            "read": True, "attendance": "no_show",
            "data": {"name": f"QA Absent {i}", "email": f"qa.person{i}@example.com"},
            "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
        })
    return sid


@pytest.fixture(scope="module")
def future_open_session_same_program(db, program):
    sid = str(uuid.uuid4())
    date = (datetime.utcnow() + timedelta(days=10)).date().isoformat()
    db.program_sessions.insert_one({
        "id": sid, "program_id": program["id"], "date": date,
        "start_time": "10:00", "end_time": "11:00",
        "location": "QA Hall", "seats": 10, "notes": "",
        "created_at": datetime.utcnow().isoformat()
    })
    return sid


class TestFollowUps:
    def test_direct_call_sends_once_per_person(self, db, program, past_session_with_absents,
                                               future_open_session_same_program, monkeypatch):
        import server
        # clear any prior noshow records for these qa persons
        db.noshow_emails.delete_many({"email": {"$regex": "^qa.person"}})
        sent_to = []

        async def fake_send_email(**kw):
            sent_to.append(kw.get("to"))

        monkeypatch.setattr(server, "send_email", fake_send_email)
        today = datetime.utcnow().date()
        n = asyncio.get_event_loop().run_until_complete(
            server._send_session_absent_followups(today)
        )
        assert n >= 2, f"Expected 2+ emails, got {n}"
        qa = [e for e in sent_to if e and e.startswith("qa.person")]
        assert len(qa) >= 2
        # idempotent - second call should send 0 for these submissions
        sent_to.clear()
        n2 = asyncio.get_event_loop().run_until_complete(
            server._send_session_absent_followups(today)
        )
        qa2 = [e for e in sent_to if e and e.startswith("qa.person")]
        assert len(qa2) == 0, f"Expected idempotent, got {qa2}"
        # spot tokens were created for the next session
        tokens = list(db.spot_tokens.find(
            {"session_id": future_open_session_same_program}, {"_id": 0}))
        assert len(tokens) >= 2

    def test_program_noshow_excludes_session_signups(self, db, program, past_session_with_absents, monkeypatch):
        """_noshow_for_program must skip submissions that have a session_id."""
        import server
        sent_to = []

        async def fake_send_email(**kw):
            sent_to.append(kw.get("to"))

        monkeypatch.setattr(server, "send_email", fake_send_email)
        # Pre-mark all noshow_emails cleared for qa.person4 at program-level
        db.noshow_emails.delete_many({"email": "qa.person4@example.com"})
        # Insert a program-level (no session_id) no_show
        prog_sub_id = str(uuid.uuid4())
        db.submissions.insert_one({
            "id": prog_sub_id, "type": "program_signup",
            "program_id": program["id"], "waitlist": False, "attendance": "no_show",
            "read": True, "data": {"name": "QA Prog", "email": "qa.person4@example.com"},
            "created_at": datetime.utcnow().isoformat()
        })
        asyncio.get_event_loop().run_until_complete(
            server._noshow_for_program(program)
        )
        # Session sign-ups (qa.person2,3) should NOT be in sent_to from _noshow_for_program
        # Only qa.person4 (program-level) should be in sent_to
        assert "qa.person4@example.com" in sent_to
        assert "qa.person2@example.com" not in sent_to
        assert "qa.person3@example.com" not in sent_to


class TestSaveSpot:
    def test_bad_token_404(self):
        r = requests.get(f"{BASE_URL}/api/sessions/save-spot?token=nope-not-real")
        assert r.status_code == 404

    def test_info_and_claim_flow(self, db, future_open_session_same_program):
        tok = list(db.spot_tokens.find(
            {"session_id": future_open_session_same_program, "used": False},
            {"_id": 0}))
        if not tok:
            pytest.skip("No spot token available (followup didn't run)")
        token = tok[0]["token"]
        r = requests.get(f"{BASE_URL}/api/sessions/save-spot", params={"token": token})
        assert r.status_code == 200, r.text
        info = r.json()
        assert info["used"] is False
        assert info["full"] is False
        assert info["past"] is False
        assert "label" in info and "program" in info

        r = requests.post(f"{BASE_URL}/api/sessions/save-spot", json={"token": token})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d.get("already") in (None, False)
        # verify submission created
        sub = db.submissions.find_one({"session_id": future_open_session_same_program,
                                       "from_submission": {"$exists": True}}, {"_id": 0})
        assert sub is not None
        assert sub["source"] == "save_spot"

        # second use → already
        r2 = requests.post(f"{BASE_URL}/api/sessions/save-spot", json={"token": token})
        assert r2.status_code == 200
        assert r2.json().get("already") is True

    def test_past_session_token_returns_unavailable(self, db, past_session_with_absents):
        # Insert a submission + spot_token that targets the PAST session
        sub_id = str(uuid.uuid4())
        db.submissions.insert_one({"id": sub_id, "type": "program_signup",
                                    "program_id": db.program_sessions.find_one(
                                        {"id": past_session_with_absents})["program_id"],
                                    "session_id": past_session_with_absents,
                                    "waitlist": False, "read": True,
                                    "data": {"name": "QA Past", "email": "qa.person9@example.com"},
                                    "created_at": datetime.utcnow().isoformat()})
        tok = "qa-" + uuid.uuid4().hex
        db.spot_tokens.insert_one({"token": tok, "submission_id": sub_id,
                                   "session_id": past_session_with_absents, "used": False,
                                   "created_at": datetime.utcnow().isoformat()})
        r = requests.get(f"{BASE_URL}/api/sessions/save-spot", params={"token": tok})
        assert r.status_code == 200
        assert r.json()["past"] is True
        r2 = requests.post(f"{BASE_URL}/api/sessions/save-spot", json={"token": tok})
        assert r2.status_code == 400
