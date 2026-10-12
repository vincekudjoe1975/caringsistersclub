"""Iter50: Staff vs member signup separation & staff reset creates admin.

Covers:
- /api/auth/signup with a team email -> 409 "staff team" (no user created)
- /api/auth/reset-password-request for team email with NO user record -> 200, users doc created with role 'admin' and auth_providers []
- Mint reset token -> /api/auth/reset-password -> 200 -> login -> /auth/me shows role admin
- Regular member signup + verify -> role stays 'pending', verify returns session
"""
import os
import re
import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

QA_STAFF_EMAIL = f"qa.staff.{uuid.uuid4().hex[:6]}@example.com"
QA_MEMBER_EMAIL = f"qa.member.{uuid.uuid4().hex[:6]}@example.com"
QA_SIGNUP_BLOCK_EMAIL = f"qa.block.{uuid.uuid4().hex[:6]}@example.com"
PW_A = "Secret12345"
PW_NEW = "NewPass9876"


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup():
    # Seed: insert allowed_emails for QA_STAFF_EMAIL and QA_SIGNUP_BLOCK_EMAIL
    db.allowed_emails.insert_one({"email": QA_STAFF_EMAIL})
    db.allowed_emails.insert_one({"email": QA_SIGNUP_BLOCK_EMAIL})
    # Clear rate limits
    db.rate_hits.delete_many({"key": {"$regex": "^auth_"}})
    yield
    # Cleanup
    db.allowed_emails.delete_many({"email": {"$in": [QA_STAFF_EMAIL, QA_SIGNUP_BLOCK_EMAIL]}})
    uids = [u["user_id"] for u in db.users.find({"email": {"$in": [QA_STAFF_EMAIL, QA_MEMBER_EMAIL, QA_SIGNUP_BLOCK_EMAIL]}}, {"user_id": 1})]
    db.users.delete_many({"user_id": {"$in": uids}})
    db.user_credentials.delete_many({"user_id": {"$in": uids}})
    db.auth_tokens.delete_many({"user_id": {"$in": uids}})
    db.user_sessions.delete_many({"user_id": {"$in": uids}})
    db.login_attempts.delete_many({"identifier": {"$regex": re.escape(QA_STAFF_EMAIL) + "$|" + re.escape(QA_MEMBER_EMAIL) + "$"}})
    db.rate_hits.delete_many({"key": {"$regex": "^auth_"}})


def test_signup_with_team_email_blocked():
    r = requests.post(f"{BASE_URL}/api/auth/signup", json={"name": "QA", "email": QA_SIGNUP_BLOCK_EMAIL, "password": PW_A})
    assert r.status_code == 409, r.text
    detail = r.json().get("detail", "")
    assert "staff team" in detail.lower() or "staff login" in detail.lower(), detail
    # No user created
    assert db.users.find_one({"email": QA_SIGNUP_BLOCK_EMAIL}) is None


def test_reset_request_for_team_email_creates_admin_then_login():
    # No existing user
    assert db.users.find_one({"email": QA_STAFF_EMAIL}) is None
    r = requests.post(f"{BASE_URL}/api/auth/reset-password-request", json={"email": QA_STAFF_EMAIL})
    assert r.status_code == 200, r.text
    # Verify user doc created with role=admin and auth_providers=[]
    u = db.users.find_one({"email": QA_STAFF_EMAIL})
    assert u is not None
    assert u.get("role") == "admin", u
    assert u.get("auth_providers") == [], u
    assert u.get("email_verified") is False

    # Mint reset token
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    db.auth_tokens.insert_one({
        "token_hash": token_hash,
        "user_id": u["user_id"],
        "kind": "reset",
        "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "created_at": datetime.now(timezone.utc),
    })

    # Reset-password
    r2 = requests.post(f"{BASE_URL}/api/auth/reset-password", json={"token": raw, "password": PW_NEW})
    assert r2.status_code == 200, r2.text

    # Login
    s = requests.Session()
    r3 = s.post(f"{BASE_URL}/api/auth/login", json={"email": QA_STAFF_EMAIL, "password": PW_NEW})
    assert r3.status_code == 200, r3.text
    # /auth/me
    r4 = s.get(f"{BASE_URL}/api/auth/me")
    assert r4.status_code == 200
    me = r4.json()
    assert me["role"] == "admin"
    assert me["email"] == QA_STAFF_EMAIL


def test_regular_member_signup_role_pending_and_verify():
    r = requests.post(f"{BASE_URL}/api/auth/signup", json={"name": "QA Member", "email": QA_MEMBER_EMAIL, "password": PW_A})
    assert r.status_code == 200, r.text
    u = db.users.find_one({"email": QA_MEMBER_EMAIL})
    assert u is not None
    assert u.get("role") == "pending"
    assert u.get("email_verified") is False

    # Mint a verify token
    raw = secrets.token_urlsafe(32)
    db.auth_tokens.delete_many({"user_id": u["user_id"], "kind": "verify"})
    db.auth_tokens.insert_one({
        "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "user_id": u["user_id"],
        "kind": "verify",
        "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        "created_at": datetime.now(timezone.utc),
    })
    s = requests.Session()
    r2 = s.post(f"{BASE_URL}/api/auth/verify-email", json={"token": raw})
    assert r2.status_code == 200, r2.text
    data = r2.json()
    # role should remain pending (no promotion)
    assert data.get("role") == "pending", data
    assert data.get("email_verified") is True

    # Login works
    s2 = requests.Session()
    r3 = s2.post(f"{BASE_URL}/api/auth/login", json={"email": QA_MEMBER_EMAIL, "password": PW_A})
    assert r3.status_code == 200
    me = s2.get(f"{BASE_URL}/api/auth/me").json()
    assert me["role"] == "pending"
