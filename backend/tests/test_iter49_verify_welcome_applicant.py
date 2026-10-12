"""Iter 49: /verify-email tap-to-confirm + 409 reuse + 400 invalid, members/apply alert path,
members/me welcome_seen, members/welcome-seen setter, admin deep-link applicant."""
import hashlib
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
DB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
HDR = {"Content-Type": "application/json", "x-requested-with": "XMLHttpRequest"}


def _sha(t):
    return hashlib.sha256(t.encode()).hexdigest()


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def qa_user():
    uid = f"user_iter49_{int(time.time())}"
    email = f"qa_iter49_{int(time.time())}@example.com"
    DB.users.insert_one({
        "user_id": uid, "email": email, "name": "Zoe QA Iter49",
        "role": "pending", "auth_providers": ["email"], "email_verified": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    DB.user_credentials.insert_one({"user_id": uid, "password_hash": "x"})
    yield {"user_id": uid, "email": email}
    # cleanup
    DB.users.delete_one({"user_id": uid})
    DB.user_credentials.delete_many({"user_id": uid})
    DB.user_sessions.delete_many({"user_id": uid})
    DB.auth_tokens.delete_many({"user_id": uid})


@pytest.fixture(scope="module")
def active_member():
    uid = f"user_iter49m_{int(time.time())}"
    email = f"qa_iter49m_{int(time.time())}@example.com"
    tok = f"iter49_sess_{int(time.time())}"
    DB.users.insert_one({
        "user_id": uid, "email": email, "name": "Mabel QA Active",
        "role": "pending", "member_status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    DB.user_sessions.insert_one({
        "user_id": uid, "session_token": tok,
        "expires_at": "2099-01-01T00:00:00+00:00",
    })
    yield {"user_id": uid, "email": email, "token": tok}
    DB.users.delete_one({"user_id": uid})
    DB.user_sessions.delete_one({"session_token": tok})


# ---------- /verify-email ----------
def _mint_verify(uid):
    raw = f"iter49tok_{int(time.time()*1000)}"
    DB.auth_tokens.delete_many({"user_id": uid, "kind": "verify", "used": False})
    DB.auth_tokens.insert_one({
        "token_hash": _sha(raw), "user_id": uid, "kind": "verify",
        "used": False, "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        "created_at": datetime.now(timezone.utc),
    })
    return raw


class TestVerifyEmail:
    def test_valid_token_logs_in_and_marks_used(self, qa_user):
        raw = _mint_verify(qa_user["user_id"])
        # Precondition: token still unused in db (sanity for FE claim that page doesn't auto-POST)
        row = DB.auth_tokens.find_one({"token_hash": _sha(raw)})
        assert row and row["used"] is False
        r = requests.post(f"{BASE}/api/auth/verify-email", json={"token": raw}, headers=HDR)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user_id"] == qa_user["user_id"]
        # Token is now used
        row = DB.auth_tokens.find_one({"token_hash": _sha(raw)})
        assert row and row["used"] is True
        # User marked verified
        u = DB.users.find_one({"user_id": qa_user["user_id"]})
        assert u.get("email_verified") is True

    def test_reusing_same_token_returns_409_already_confirmed(self, qa_user):
        # Reuse same raw by re-inserting (same hash would already be used - but code looks up by
        # used:False first, else finds used:True + user is verified => 409).
        # Mint again then consume twice.
        raw = _mint_verify(qa_user["user_id"])
        r1 = requests.post(f"{BASE}/api/auth/verify-email", json={"token": raw}, headers=HDR)
        assert r1.status_code == 200
        r2 = requests.post(f"{BASE}/api/auth/verify-email", json={"token": raw}, headers=HDR)
        assert r2.status_code == 409
        assert "already confirmed" in r2.json().get("detail", "").lower()

    def test_random_invalid_token_returns_400(self):
        r = requests.post(
            f"{BASE}/api/auth/verify-email",
            json={"token": "this-is-not-a-real-token-xyz-abc"},
            headers=HDR,
        )
        assert r.status_code == 400
        assert "invalid or has expired" in r.json().get("detail", "").lower()


# ---------- /members/apply + staff alert ----------
class TestMemberApplyAlert:
    def test_apply_triggers_alert_path(self):
        """Create a fresh non-member user with a session, POST apply, expect status=applied
        and no exception bubbled up (background alert task failures are logged)."""
        uid = f"user_iter49a_{int(time.time())}"
        email = f"qa_iter49a_{int(time.time())}@example.com"
        tok = f"iter49_apply_{int(time.time())}"
        DB.users.insert_one({
            "user_id": uid, "email": email, "name": "Nora QA Applicant",
            "role": "pending", "auth_providers": ["email"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        DB.user_sessions.insert_one({
            "user_id": uid, "session_token": tok,
            "expires_at": "2099-01-01T00:00:00+00:00",
        })
        try:
            payload = {
                "phone": "555-0100", "city": "Wilmington", "referred_by": "QA Sister",
                "why": "testing", "is_adult": True, "is_delaware": True, "agrees_bylaws": True,
            }
            r = requests.post(
                f"{BASE}/api/members/apply", json=payload,
                headers={**HDR, "Cookie": f"session_token={tok}"},
            )
            assert r.status_code == 200, r.text
            assert r.json().get("status") == "applied"
            # Verify persistence
            u = DB.users.find_one({"user_id": uid})
            assert u["member_status"] == "applied"
            assert u["member_application"]["city"] == "Wilmington"
            # allow background task to run
            time.sleep(1.0)
        finally:
            DB.users.delete_one({"user_id": uid})
            DB.user_sessions.delete_one({"session_token": tok})


# ---------- /members/me welcome_seen + setter ----------
class TestWelcomeSeen:
    def test_me_welcome_seen_false_then_true(self, active_member):
        # Ensure no portal_welcome_seen_at
        DB.users.update_one({"user_id": active_member["user_id"]}, {"$unset": {"portal_welcome_seen_at": ""}})
        r = requests.get(
            f"{BASE}/api/members/me",
            headers={**HDR, "Cookie": f"session_token={active_member['token']}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "active"
        assert data["welcome_seen"] is False
        # POST welcome-seen
        r2 = requests.post(
            f"{BASE}/api/members/welcome-seen",
            headers={**HDR, "Cookie": f"session_token={active_member['token']}"},
        )
        assert r2.status_code == 200
        # GET again -> true
        r3 = requests.get(
            f"{BASE}/api/members/me",
            headers={**HDR, "Cookie": f"session_token={active_member['token']}"},
        )
        assert r3.status_code == 200
        assert r3.json()["welcome_seen"] is True

    def test_welcome_seen_is_idempotent(self, active_member):
        # Second call shouldn't error
        r = requests.post(
            f"{BASE}/api/members/welcome-seen",
            headers={**HDR, "Cookie": f"session_token={active_member['token']}"},
        )
        assert r.status_code == 200


# ---------- Startup migration ----------
class TestMigration:
    def test_welcome_note_migrated_marker_exists(self):
        row = DB.settings.find_one({"key": "welcome_note_migrated"})
        assert row is not None, "startup migration marker missing"
