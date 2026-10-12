"""Iter 48: password-status/set-password, verify-email welcome, admin push devices+test-member."""
import os
import hashlib
import time
import datetime as dt
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

GOOGLE_UID = "qa_iter48_google"
GOOGLE_EMAIL = "qa.iter48.google@example.com"
GOOGLE_TOKEN = "qa_iter48_g_tok"

PW_UID = "qa_iter48_pw"
PW_EMAIL = "qa.iter48.pw@example.com"
PW_TOKEN = "qa_iter48_p_tok"
PW_TOKEN2 = "qa_iter48_p_tok2"
OLD_PW = "oldpass12"
NEW_PW = "newpass34"

ADMIN_UID = "qa_iter48_admin"
ADMIN_TOKEN = "qa_iter48_admin_tok"


def _future_iso(days=30):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)).isoformat()


@pytest.fixture(scope="module", autouse=True)
def seed():
    # Clean + clear rate hits
    cleanup()
    db.rate_hits.delete_many({"key": {"$regex": "^auth_setpw"}})
    db.rate_hits.delete_many({"key": {"$regex": "^push-test"}})
    # Google-style user (no credential, active member)
    db.users.insert_one({"user_id": GOOGLE_UID, "email": GOOGLE_EMAIL, "name": "Google QA",
                         "role": "pending", "member_status": "active", "picture": "https://x/y.png",
                         "auth_providers": ["google"], "email_verified": True, "created_at": _future_iso(-1)})
    db.user_sessions.insert_one({"user_id": GOOGLE_UID, "session_token": GOOGLE_TOKEN, "expires_at": _future_iso(7)})
    # Password-only user with existing cred (bcrypt of OLD_PW)
    import bcrypt
    h = bcrypt.hashpw(OLD_PW.encode(), bcrypt.gensalt()).decode()
    db.users.insert_one({"user_id": PW_UID, "email": PW_EMAIL, "name": "Pw QA",
                         "role": "pending", "member_status": "active",
                         "auth_providers": ["email"], "email_verified": True, "created_at": _future_iso(-1)})
    db.user_credentials.insert_one({"user_id": PW_UID, "password_hash": h, "updated_at": _future_iso(-1)})
    db.user_sessions.insert_one({"user_id": PW_UID, "session_token": PW_TOKEN, "expires_at": _future_iso(7)})
    db.user_sessions.insert_one({"user_id": PW_UID, "session_token": PW_TOKEN2, "expires_at": _future_iso(7)})
    # Admin
    db.users.insert_one({"user_id": ADMIN_UID, "email": "qa.iter48.admin@example.com", "name": "Admin QA", "role": "admin"})
    db.user_sessions.insert_one({"user_id": ADMIN_UID, "session_token": ADMIN_TOKEN, "expires_at": _future_iso(7)})
    yield
    cleanup()


def cleanup():
    uids = [GOOGLE_UID, PW_UID, ADMIN_UID]
    toks = [GOOGLE_TOKEN, PW_TOKEN, PW_TOKEN2, ADMIN_TOKEN]
    db.users.delete_many({"user_id": {"$in": uids}})
    db.user_sessions.delete_many({"$or": [{"user_id": {"$in": uids}}, {"session_token": {"$in": toks}}]})
    db.user_credentials.delete_many({"user_id": {"$in": uids}})
    db.auth_tokens.delete_many({"user_id": {"$in": uids}})
    db.login_attempts.delete_many({"identifier": {"$regex": "qa.iter48"}})
    db.push_subs.delete_many({"user_id": {"$in": uids}})


def cookies(tok):
    return {"session_token": tok}


HDR = {"X-Requested-With": "XMLHttpRequest"}


# -- /auth/password-status --
class TestPasswordStatus:
    def test_401_when_logged_out(self):
        r = requests.get(f"{API}/auth/password-status")
        assert r.status_code == 401

    def test_google_user_has_no_password(self):
        r = requests.get(f"{API}/auth/password-status", cookies=cookies(GOOGLE_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["has_password"] is False
        assert d["email"] == GOOGLE_EMAIL
        assert "google" in d["providers"]

    def test_password_user_has_password(self):
        r = requests.get(f"{API}/auth/password-status", cookies=cookies(PW_TOKEN), headers=HDR)
        assert r.status_code == 200
        assert r.json()["has_password"] is True


# -- /auth/set-password: no credential (add) --
class TestSetPasswordAdd:
    def test_weak_password_400(self):
        r = requests.post(f"{API}/auth/set-password", json={"password": "short"}, cookies=cookies(GOOGLE_TOKEN), headers=HDR)
        assert r.status_code == 400
        assert "8 characters" in r.json().get("detail", "")

    def test_valid_adds_password_and_login_works(self):
        r = requests.post(f"{API}/auth/set-password", json={"password": "addedpw12"}, cookies=cookies(GOOGLE_TOKEN), headers=HDR)
        assert r.status_code == 200, r.text
        assert "Password added" in r.json()["message"]
        # user_credentials row exists
        assert db.user_credentials.find_one({"user_id": GOOGLE_UID}) is not None
        # auth_providers contains email
        u = db.users.find_one({"user_id": GOOGLE_UID})
        assert "email" in (u.get("auth_providers") or [])
        # login succeeds with new password
        lr = requests.post(f"{API}/auth/login", json={"email": GOOGLE_EMAIL, "password": "addedpw12"})
        assert lr.status_code == 200, lr.text


# -- /auth/set-password: existing credential (change) --
class TestSetPasswordChange:
    def test_wrong_current_400(self):
        r = requests.post(f"{API}/auth/set-password",
                          json={"password": NEW_PW, "current_password": "wrongpw0"},
                          cookies=cookies(PW_TOKEN), headers=HDR)
        assert r.status_code == 400
        assert "current password is incorrect" in r.json().get("detail", "")

    def test_missing_current_400(self):
        r = requests.post(f"{API}/auth/set-password",
                          json={"password": NEW_PW}, cookies=cookies(PW_TOKEN), headers=HDR)
        assert r.status_code == 400

    def test_same_as_old_400(self):
        r = requests.post(f"{API}/auth/set-password",
                          json={"password": OLD_PW, "current_password": OLD_PW},
                          cookies=cookies(PW_TOKEN), headers=HDR)
        assert r.status_code == 400
        assert "different" in r.json().get("detail", "").lower()

    def test_valid_change_rotates_sessions(self):
        # Confirm other session active before
        assert db.user_sessions.find_one({"session_token": PW_TOKEN2}) is not None
        r = requests.post(f"{API}/auth/set-password",
                          json={"password": NEW_PW, "current_password": OLD_PW},
                          cookies=cookies(PW_TOKEN), headers=HDR)
        assert r.status_code == 200, r.text
        assert "changed" in r.json()["message"].lower()
        # Current session kept
        assert db.user_sessions.find_one({"session_token": PW_TOKEN}) is not None
        # Other sessions deleted
        assert db.user_sessions.find_one({"session_token": PW_TOKEN2}) is None
        # Old password rejected
        lr_old = requests.post(f"{API}/auth/login", json={"email": PW_EMAIL, "password": OLD_PW})
        assert lr_old.status_code == 401
        # New password works
        lr_new = requests.post(f"{API}/auth/login", json={"email": PW_EMAIL, "password": NEW_PW})
        assert lr_new.status_code == 200


# -- Verify email token mint (used by frontend welcome flow) --
class TestVerifyEmailToken:
    def test_mint_and_consume(self):
        raw = "qa_iter48_verifytok"
        # Create a non-verified pending-google user with no verification yet
        uid = "qa_iter48_v"
        email = "qa.iter48.verify@example.com"
        db.users.delete_one({"user_id": uid})
        db.users.insert_one({"user_id": uid, "email": email, "name": "Verify Me",
                             "role": "pending", "member_status": "", "auth_providers": ["email"],
                             "email_verified": False, "created_at": _future_iso(-1)})
        db.auth_tokens.insert_one({"token_hash": hashlib.sha256(raw.encode()).hexdigest(),
                                   "user_id": uid, "kind": "verify", "used": False,
                                   "expires_at": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
                                   "created_at": dt.datetime.now(dt.timezone.utc)})
        try:
            r = requests.post(f"{API}/auth/verify-email", json={"token": raw})
            assert r.status_code == 200, r.text
            # Sets email_verified true
            u = db.users.find_one({"user_id": uid})
            assert u["email_verified"] is True
        finally:
            db.users.delete_one({"user_id": uid})
            db.auth_tokens.delete_many({"user_id": uid})
            db.user_sessions.delete_many({"user_id": uid})


# -- Admin push devices --
class TestAdminPushDevices:
    def test_non_admin_403(self):
        r = requests.get(f"{API}/admin/members/push/devices", cookies=cookies(GOOGLE_TOKEN))
        assert r.status_code == 403

    def test_admin_lists_rows_without_keys(self):
        # Seed one fake push_sub for GOOGLE_UID
        db.push_subs.delete_many({"user_id": GOOGLE_UID})
        db.push_subs.insert_one({
            "user_id": GOOGLE_UID,
            "endpoint": "https://fcm.googleapis.com/fcm/send/fake-android-abcdef",
            "keys": {"p256dh": "fakekey", "auth": "fakeauth"},
            "updated_at": _future_iso(-1),
        })
        r = requests.get(f"{API}/admin/members/push/devices", cookies=cookies(ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        rows = r.json()["rows"]
        # Our google user should appear with at least one device
        row = next((x for x in rows if x["user_id"] == GOOGLE_UID), None)
        assert row is not None
        assert len(row["devices"]) == 1
        # No keys leaked anywhere
        import json as _json
        assert "p256dh" not in _json.dumps(rows)
        assert "fakekey" not in _json.dumps(rows)


class TestAdminPushTestMember:
    def test_no_devices_400(self):
        db.push_subs.delete_many({"user_id": PW_UID})
        r = requests.post(f"{API}/admin/members/push/test-member/{PW_UID}", cookies=cookies(ADMIN_TOKEN), headers=HDR)
        assert r.status_code == 400
        assert "no registered devices" in r.json().get("detail", "")

    def test_with_fake_device_200(self):
        db.push_subs.delete_many({"user_id": GOOGLE_UID})
        db.push_subs.insert_one({
            "user_id": GOOGLE_UID,
            "endpoint": "https://fcm.googleapis.com/fcm/send/fake-xyz",
            "keys": {"p256dh": "ZmFrZQ==", "auth": "ZmFrZQ=="},
            "updated_at": _future_iso(-1),
        })
        r = requests.post(f"{API}/admin/members/push/test-member/{GOOGLE_UID}", cookies=cookies(ADMIN_TOKEN), headers=HDR)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "sent" in d and "devices" in d
        assert d["devices"] >= 1
        # Allow a moment for _deliver to finish
        time.sleep(1.0)
        sub = db.push_subs.find_one({"user_id": GOOGLE_UID})
        # Fake endpoint should fail delivery → last_fail_at set
        assert sub.get("last_fail_at"), f"expected last_fail_at, got: {sub}"
