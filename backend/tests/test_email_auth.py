"""Tests for Email + Password Auth (signup, verify, login, reset, resend)."""
import os
import re
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Direct MongoDB access for token seeding + cleanup
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
_mc = MongoClient(MONGO_URL)
_db = _mc[DB_NAME]

QA_PREFIX = "qa.email.test"
TEST_EMAILS = []


def _uniq_email(tag=""):
    e = f"{QA_PREFIX}.{tag}{secrets.token_hex(3)}@example.com"
    TEST_EMAILS.append(e)
    return e


def _seed_token(user_id: str, kind: str, hours: int = 24) -> str:
    raw = secrets.token_urlsafe(16)
    _db.auth_tokens.insert_one({
        "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "user_id": user_id, "kind": kind, "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=hours),
        "created_at": datetime.now(timezone.utc),
    })
    return raw


def _clear_rate():
    _db.rate_hits.delete_many({"key": {"$regex": "^auth_"}})
    _db.login_attempts.delete_many({})


@pytest.fixture(autouse=True)
def clear_rate_limits():
    _clear_rate()
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    yield
    # Cleanup all QA data
    users = list(_db.users.find({"email": {"$regex": f"^{re.escape(QA_PREFIX)}"}}, {"user_id": 1, "email": 1}))
    uids = [u["user_id"] for u in users]
    _db.users.delete_many({"email": {"$regex": f"^{re.escape(QA_PREFIX)}"}})
    _db.user_credentials.delete_many({"user_id": {"$in": uids}})
    _db.auth_tokens.delete_many({"user_id": {"$in": uids}})
    _db.user_sessions.delete_many({"user_id": {"$in": uids}})
    _db.login_attempts.delete_many({})
    # Also remove the pre-existing qa.email1 if we didn't need it
    # Keep as instructed


# ---------- SIGNUP ----------

class TestSignup:
    def test_signup_valid(self):
        em = _uniq_email("ok")
        r = requests.post(f"{API}/auth/signup", json={"email": em, "password": "abc12345", "name": "Qa Sister"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "confirmation" in data.get("message", "").lower() or "email" in data.get("message", "").lower()
        # Verify user was created in DB with unverified
        u = _db.users.find_one({"email": em})
        assert u is not None
        assert u.get("email_verified") is False
        assert "email" in u.get("auth_providers", [])
        # Password hash lives in user_credentials only, NOT users
        assert "password_hash" not in u
        cred = _db.user_credentials.find_one({"user_id": u["user_id"]})
        assert cred and cred["password_hash"].startswith("$2")

    def test_signup_invalid_email(self):
        r = requests.post(f"{API}/auth/signup", json={"email": "not-an-email", "password": "abc12345"})
        assert r.status_code == 400
        assert "valid email" in r.json().get("detail", "").lower()
        assert _db.users.find_one({"email": "not-an-email"}) is None

    def test_signup_weak_password_no_number(self):
        em = _uniq_email("weak1")
        r = requests.post(f"{API}/auth/signup", json={"email": em, "password": "abcdefgh"})
        assert r.status_code == 400
        assert "8 characters" in r.json().get("detail", "") or "number" in r.json().get("detail", "").lower()
        assert _db.users.find_one({"email": em}) is None

    def test_signup_weak_password_short(self):
        em = _uniq_email("weak2")
        r = requests.post(f"{API}/auth/signup", json={"email": em, "password": "ab12"})
        assert r.status_code == 400
        assert _db.users.find_one({"email": em}) is None

    def test_signup_duplicate_verified(self):
        # Use the pre-existing verified account
        r = requests.post(f"{API}/auth/signup", json={"email": "qa.email1@example.com", "password": "abc12345"})
        assert r.status_code == 409
        assert "already exists" in r.json().get("detail", "").lower()

    def test_signup_google_user_blocked(self):
        # Seed a google-only user
        em = _uniq_email("google")
        uid = f"user_qa_g_{secrets.token_hex(4)}"
        _db.users.insert_one({
            "user_id": uid, "email": em, "name": "Google Qa", "picture": "https://x.com/a.png",
            "role": "pending", "auth_providers": ["google"], "email_verified": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{API}/auth/signup", json={"email": em, "password": "abc12345"})
        assert r.status_code == 409
        assert "google" in r.json().get("detail", "").lower()


# ---------- VERIFY EMAIL ----------

class TestVerifyEmail:
    def test_verify_valid_logs_in(self):
        em = _uniq_email("verify")
        requests.post(f"{API}/auth/signup", json={"email": em, "password": "abc12345"})
        u = _db.users.find_one({"email": em})
        raw = _seed_token(u["user_id"], "verify")
        r = requests.post(f"{API}/auth/verify-email", json={"token": raw})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("email") == em
        assert body.get("email_verified") is True
        assert "password_hash" not in body
        # Cookie set
        assert "session_token" in r.cookies

    def test_verify_reused_token(self):
        em = _uniq_email("verify2")
        requests.post(f"{API}/auth/signup", json={"email": em, "password": "abc12345"})
        u = _db.users.find_one({"email": em})
        raw = _seed_token(u["user_id"], "verify")
        r1 = requests.post(f"{API}/auth/verify-email", json={"token": raw})
        assert r1.status_code == 200
        r2 = requests.post(f"{API}/auth/verify-email", json={"token": raw})
        assert r2.status_code == 400

    def test_verify_invalid_token(self):
        r = requests.post(f"{API}/auth/verify-email", json={"token": "garbage-token-xyz"})
        assert r.status_code == 400


# ---------- LOGIN ----------

class TestLogin:
    def test_login_unverified(self):
        em = _uniq_email("unver")
        requests.post(f"{API}/auth/signup", json={"email": em, "password": "abc12345"})
        r = requests.post(f"{API}/auth/login", json={"email": em, "password": "abc12345"})
        assert r.status_code == 403
        assert "confirm your email" in r.json().get("detail", "").lower()

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": "qa.email1@example.com", "password": "WRONGpass9"})
        assert r.status_code == 401
        assert "incorrect" in r.json().get("detail", "").lower()

    def test_login_success_case_insensitive(self):
        r = requests.post(f"{API}/auth/login", json={"email": "QA.email1@EXAMPLE.com", "password": "abc12345"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"].lower() == "qa.email1@example.com"
        assert "password_hash" not in data
        assert "session_token" in r.cookies

    def test_login_google_only_account(self):
        em = _uniq_email("gonly")
        uid = f"user_qa_go_{secrets.token_hex(4)}"
        _db.users.insert_one({
            "user_id": uid, "email": em, "name": "G Only",
            "role": "pending", "auth_providers": ["google"], "email_verified": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{API}/auth/login", json={"email": em, "password": "abc12345"})
        assert r.status_code == 400
        assert "google" in r.json().get("detail", "").lower()

    def test_login_lockout_after_5_fails(self):
        em = _uniq_email("lock")
        requests.post(f"{API}/auth/signup", json={"email": em, "password": "abc12345"})
        # 5 wrong attempts
        last = None
        for _ in range(5):
            last = requests.post(f"{API}/auth/login", json={"email": em, "password": "WrongPw99"})
        assert last.status_code == 401
        r = requests.post(f"{API}/auth/login", json={"email": em, "password": "WrongPw99"})
        assert r.status_code == 429
        assert "too many" in r.json().get("detail", "").lower()


# ---------- RESEND & RESET REQUEST (always 200) ----------

class TestEnumerationSafe:
    def test_resend_unknown_email(self):
        r = requests.post(f"{API}/auth/resend-verification", json={"email": "nobody.qa.email.test@example.com"})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_reset_request_unknown_email(self):
        r = requests.post(f"{API}/auth/reset-password-request", json={"email": "nobody.qa.email.test@example.com"})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_reset_request_known_email(self):
        r = requests.post(f"{API}/auth/reset-password-request", json={"email": "qa.email1@example.com"})
        assert r.status_code == 200


# ---------- RESET PASSWORD ----------

class TestResetPassword:
    def test_reset_weak_password(self):
        r = requests.post(f"{API}/auth/reset-password", json={"token": "anything", "password": "weak"})
        assert r.status_code == 400

    def test_reset_valid_flow(self):
        em = _uniq_email("rst")
        requests.post(f"{API}/auth/signup", json={"email": em, "password": "oldpass123"})
        u = _db.users.find_one({"email": em})
        # Seed verify first and verify it
        vraw = _seed_token(u["user_id"], "verify")
        requests.post(f"{API}/auth/verify-email", json={"token": vraw})
        # Create an active session (to confirm it gets invalidated)
        _db.user_sessions.insert_one({
            "user_id": u["user_id"], "session_token": "stale_tok_" + secrets.token_hex(4),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        pre_sessions = _db.user_sessions.count_documents({"user_id": u["user_id"]})
        assert pre_sessions >= 1
        rraw = _seed_token(u["user_id"], "reset", hours=1)
        r = requests.post(f"{API}/auth/reset-password", json={"token": rraw, "password": "NewPass456"})
        assert r.status_code == 200, r.text
        # Old sessions invalidated
        post_sessions = _db.user_sessions.count_documents({"user_id": u["user_id"]})
        assert post_sessions == 0
        # Old password fails
        r2 = requests.post(f"{API}/auth/login", json={"email": em, "password": "oldpass123"})
        assert r2.status_code == 401
        # New password works
        r3 = requests.post(f"{API}/auth/login", json={"email": em, "password": "NewPass456"})
        assert r3.status_code == 200
        # Token single use
        r4 = requests.post(f"{API}/auth/reset-password", json={"token": rraw, "password": "Another789"})
        assert r4.status_code == 400


# ---------- SESSION / /me / logout ----------

class TestSession:
    def test_me_and_logout(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": "qa.email1@example.com", "password": "abc12345"})
        assert r.status_code == 200
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        data = me.json()
        assert data["email"] == "qa.email1@example.com"
        assert "password_hash" not in data
        # Members me (non-member -> apply flow signal)
        mm = s.get(f"{API}/members/me")
        # Should be 200 with non-member info or 404 depending on impl, but not 500
        assert mm.status_code in (200, 403, 404)
        # Logout
        lo = s.post(f"{API}/auth/logout")
        assert lo.status_code == 200
        me2 = s.get(f"{API}/auth/me")
        assert me2.status_code == 401
