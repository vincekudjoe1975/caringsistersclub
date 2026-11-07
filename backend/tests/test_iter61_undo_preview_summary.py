# Iteration 61: staff-log Undo, owner Preview-as-level, Monday staff summary (settings + cron)
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
CRON = os.environ.get('WEBHOOK_CRON_SECRET')
OWNER_EMAIL = "vincekudjoe@gmail.com"
FUT = "2099-01-01T00:00:00+00:00"
E1, E2, E3 = "test.qa61.s1@example.com", "test.qa61.s2@example.com", "test.qa61.s3@example.com"
EPRE = "test.qa61.pre@example.com"
EMAILS = [E1, E2, E3, EPRE, "qa@example.com"]
CRON_KEY = f"TEST_qa61_{uuid.uuid4().hex[:8]}"


def _now(d=0):
    return (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()


@pytest.fixture(scope="module", autouse=True)
def setup():
    owner = db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "user_id": 1})
    db.user_sessions.insert_one({"session_token": "qa_owner_tok", "user_id": owner["user_id"], "expires_at": FUT})
    db.users.insert_one({"user_id": "qa_user", "email": "qa@example.com", "name": "QA", "role": "admin"})
    db.user_sessions.insert_one({"session_token": "qa_tok_123", "user_id": "qa_user", "expires_at": FUT})
    db.users.insert_one({"user_id": "TEST_qa61_s1", "email": E1, "name": "TEST S1", "role": "admin", "staff_level": "full", "created_at": FUT})
    db.users.insert_one({"user_id": "TEST_qa61_s2", "email": E2, "name": "TEST S2", "role": "admin", "staff_level": "full", "created_at": FUT})
    db.users.insert_one({"user_id": "TEST_qa61_s3", "email": E3, "name": "TEST S3", "role": "admin", "staff_level": "content", "created_at": FUT})
    db.user_sessions.insert_one({"session_token": "TEST_qa61_tok_s3", "user_id": "TEST_qa61_s3", "expires_at": FUT})
    yield owner
    db.user_sessions.delete_many({"session_token": {"$in": ["qa_owner_tok", "qa_tok_123", "TEST_qa61_tok_s3"]}})
    db.users.delete_many({"user_id": {"$in": ["qa_user", "TEST_qa61_s1", "TEST_qa61_s2", "TEST_qa61_s3"]}})
    db.staff_log.delete_many({"target.email": {"$in": EMAILS}})
    db.staff_log.delete_many({"id": {"$regex": "^TEST_qa61"}})
    db.allowed_emails.delete_many({"email": {"$in": EMAILS}})
    db.scheduled_runs.delete_many({"key": f"staff_summary:{CRON_KEY}"})


def S(tok, **hdr):
    s = requests.Session()
    s.cookies.set("session_token", tok)
    s.headers.update({"X-Requested-With": "XMLHttpRequest", **hdr})
    return s


def log_for(email):
    r = S("qa_tok_123").get(f"{API}/admin/team/log")
    assert r.status_code == 200
    rows = [e for e in r.json() if e["target"]["email"] == email]
    for e in rows:
        assert "before" not in e and "_id" not in e
    return rows


class TestUndo:
    def test_level_undo_chain(self):
        s = S("qa_tok_123")
        assert s.post(f"{API}/admin/team/TEST_qa61_s1/level", json={"level": "money"}).status_code == 200
        assert s.post(f"{API}/admin/team/TEST_qa61_s1/level", json={"level": "members"}).status_code == 200
        rows = log_for(E1)
        assert [r["action"] for r in rows] == ["level", "level"]
        newest, older = rows
        assert newest["undo_block"] == "" and "newer change" in older["undo_block"]
        r = s.post(f"{API}/admin/team/log/{older['id']}/undo")
        assert r.status_code == 400 and "newer change" in r.json()["detail"]
        assert s.post(f"{API}/admin/team/log/{newest['id']}/undo").status_code == 200
        assert db.users.find_one({"user_id": "TEST_qa61_s1"})["staff_level"] == "money"
        rows = log_for(E1)
        assert rows[0]["action"] == "undo" and rows[0]["undid"]["id"] == newest["id"]
        n = next(x for x in rows if x["id"] == newest["id"])
        assert n["undone_at"] and n["undone_by"]["email"] == "qa@example.com" and n["undo_block"] == "Already undone."
        o = next(x for x in rows if x["id"] == older["id"])
        assert o["undo_block"] == ""
        assert s.post(f"{API}/admin/team/log/{older['id']}/undo").status_code == 200
        assert db.users.find_one({"user_id": "TEST_qa61_s1"})["staff_level"] == "full"
        r = s.post(f"{API}/admin/team/log/{newest['id']}/undo")
        assert r.status_code == 400 and r.json()["detail"] == "Already undone."

    def test_undo_restores_role_and_member_status(self):
        # manual 'granted' row: before = pending, no member_status  (undo -> pending, no alert)
        db.users.update_one({"user_id": "TEST_qa61_s2"}, {"$set": {"member_status": "active"}})
        rid = f"TEST_qa61_{uuid.uuid4().hex[:6]}"
        db.staff_log.insert_one({"id": rid, "at": _now(), "action": "granted", "level": "full", "by": {"email": "qa@example.com", "name": "QA"},
                                 "target": {"email": E2, "name": "TEST S2", "user_id": "TEST_qa61_s2"},
                                 "before": {"role": "pending", "staff_level": None, "member_status": None, "member_since": None, "require_login_code": None}})
        r = S("qa_tok_123").post(f"{API}/admin/team/log/{rid}/undo")
        assert r.status_code == 200, r.text
        u = db.users.find_one({"user_id": "TEST_qa61_s2"})
        assert u["role"] == "pending" and "member_status" not in u and "staff_level" not in u

    def test_old_entry_blocked(self):
        rid = f"TEST_qa61_{uuid.uuid4().hex[:6]}"
        db.staff_log.insert_one({"id": rid, "at": _now(8), "action": "level", "level": "money", "by": {"email": "qa@example.com", "name": "QA"},
                                 "target": {"email": E3, "name": "TEST S3", "user_id": "TEST_qa61_s3"}, "before": {"role": "admin", "staff_level": "full"}})
        row = next(x for x in log_for(E3) if x["id"] == rid)
        assert "7 days" in row["undo_block"]
        r = S("qa_tok_123").post(f"{API}/admin/team/log/{rid}/undo")
        assert r.status_code == 400 and "7 days" in r.json()["detail"]
        assert db.users.find_one({"user_id": "TEST_qa61_s3"})["staff_level"] == "content"

    def test_preapproval_undo_both_ways(self):
        s = S("qa_tok_123")
        db.allowed_emails.insert_one({"email": EPRE})
        rid = f"TEST_qa61_{uuid.uuid4().hex[:6]}"
        db.staff_log.insert_one({"id": rid, "at": _now(0.01), "action": "preapproved", "level": "full", "by": {"email": "qa@example.com", "name": "QA"},
                                 "target": {"email": EPRE, "name": "pre", "user_id": None}})
        assert s.post(f"{API}/admin/team/revoke-email", json={"email": EPRE}).status_code == 200
        assert not db.allowed_emails.find_one({"email": EPRE})
        rows = log_for(EPRE)
        assert rows[0]["action"] == "preapproval_removed" and rows[0]["undo_block"] == ""
        assert s.post(f"{API}/admin/team/log/{rows[0]['id']}/undo").status_code == 200
        assert db.allowed_emails.find_one({"email": EPRE})
        row = next(x for x in log_for(EPRE) if x["id"] == rid)
        assert row["undo_block"] == ""
        assert s.post(f"{API}/admin/team/log/{rid}/undo").status_code == 200
        assert not db.allowed_emails.find_one({"email": EPRE})

    def test_owner_and_self_and_404(self, setup):
        s = S("qa_tok_123")
        rid = f"TEST_qa61_own_{uuid.uuid4().hex[:6]}"
        db.staff_log.insert_one({"id": rid, "at": _now(), "action": "level", "level": "money", "by": {"email": "qa@example.com", "name": "QA"},
                                 "target": {"email": OWNER_EMAIL, "name": "Owner", "user_id": setup["user_id"]}, "before": {"role": "admin", "staff_level": "full"}})
        try:
            r = s.post(f"{API}/admin/team/log/{rid}/undo")
            assert r.status_code == 400 and "Owner" in r.json()["detail"]
        finally:
            db.staff_log.delete_one({"id": rid})
        rid2 = f"TEST_qa61_{uuid.uuid4().hex[:6]}"
        db.staff_log.insert_one({"id": rid2, "at": _now(), "action": "level", "level": "money", "by": {"email": "x@example.com", "name": "X"},
                                 "target": {"email": "qa@example.com", "name": "QA", "user_id": "qa_user"}, "before": {"role": "admin", "staff_level": "full"}})
        r = s.post(f"{API}/admin/team/log/{rid2}/undo")
        assert r.status_code == 400 and "your own" in r.json()["detail"]
        assert s.post(f"{API}/admin/team/log/nope_{uuid.uuid4().hex}/undo").status_code == 404

    def test_restricted_staff_cannot_undo(self):
        r = S("TEST_qa61_tok_s3").get(f"{API}/admin/team/log")
        assert r.status_code == 403


class TestPreview:
    def test_owner_content_preview_reads(self):
        s = S("qa_owner_tok", **{"X-Preview-Level": "content", "X-Preview-Mode": "look"})
        assert s.get(f"{API}/admin/gallery").status_code == 200
        r = s.get(f"{API}/admin/donations")
        assert r.status_code == 403 and "Content only" in r.json()["detail"]
        assert S("qa_owner_tok").get(f"{API}/admin/donations").status_code == 200

    def test_owner_look_only_blocks_writes(self):
        s = S("qa_owner_tok", **{"X-Preview-Level": "members", "X-Preview-Mode": "look"})
        r = s.put(f"{API}/admin/team/summary-settings", json={"quiet_weeks": True})
        assert r.status_code == 403 and r.json()["detail"] == "You're previewing in look-only mode, so nothing was saved."

    def test_owner_working_mode_level_enforced(self):
        s = S("qa_owner_tok", **{"X-Preview-Level": "money", "X-Preview-Mode": "working"})
        r = s.put(f"{API}/admin/team/summary-settings", json={"quiet_weeks": True})
        assert r.status_code == 403 and "Money only" in r.json()["detail"]
        assert s.get(f"{API}/admin/donations").status_code == 200
        assert s.get(f"{API}/admin/gallery").status_code == 403

    def test_non_owner_header_ignored(self):
        s = S("qa_tok_123", **{"X-Preview-Level": "content", "X-Preview-Mode": "look"})
        assert s.get(f"{API}/admin/donations").status_code == 200
        r = s.put(f"{API}/admin/team/summary-settings", json={"quiet_weeks": True})
        assert r.status_code == 200

    def test_me_has_is_owner(self):
        assert S("qa_owner_tok").get(f"{API}/auth/me").json()["is_owner"] is True
        assert S("qa_tok_123").get(f"{API}/auth/me").json()["is_owner"] is False


class TestSummary:
    def test_settings_roundtrip(self):
        s = S("qa_tok_123")
        g = s.get(f"{API}/admin/team/summary-settings").json()
        assert g["quiet_weeks"] is True and OWNER_EMAIL in g["recipients"]
        assert s.put(f"{API}/admin/team/summary-settings", json={"quiet_weeks": False}).json() == {"quiet_weeks": False}
        assert s.get(f"{API}/admin/team/summary-settings").json()["quiet_weeks"] is False
        assert s.put(f"{API}/admin/team/summary-settings", json={"quiet_weeks": True}).status_code == 200
        assert s.put(f"{API}/admin/team/summary-settings", json={"quiet_weeks": "x"}).status_code == 422

    def test_cron_auth_and_dedupe(self):
        assert requests.post(f"{API}/cron/staff-summary", json={}).status_code == 401
        assert requests.post(f"{API}/cron/staff-summary", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
        h = {"Authorization": f"Bearer {CRON}", "X-Webhook-Id": CRON_KEY}
        r1 = requests.post(f"{API}/cron/staff-summary", json={}, headers=h)
        assert r1.status_code == 200 and r1.json() == {"ok": True}
        r2 = requests.post(f"{API}/cron/staff-summary", json={}, headers=h)
        assert r2.status_code == 200 and r2.json().get("duplicate") is True
