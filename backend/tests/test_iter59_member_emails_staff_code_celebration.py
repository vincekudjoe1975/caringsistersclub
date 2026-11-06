# Iteration 59: editable welcome/approval emails, staff email-code on Admin sign-in, install celebration flag
import os
import time
import uuid
import hashlib
from datetime import datetime, timezone, timedelta

import bcrypt
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
RUN = uuid.uuid4().hex[:8]
H = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}
PW = "QaPass1234"
IDS = {"admin": f"test59_admin_{RUN}", "staff": f"test59_staff_{RUN}", "mem": f"test59_mem_{RUN}", "appl": f"test59_appl_{RUN}"}
EMAILS = {k: f"test59.{k}.{RUN}@example.com" for k in IDS}


def _now(d=timedelta()):
    return (datetime.now(timezone.utc) + d).isoformat()


def _sess(tok=None):
    s = requests.Session(); s.headers.update(H)
    if tok:
        s.cookies.set("session_token", tok)
    return s


def _set_code(uid, code="123456"):
    db.auth_tokens.update_many({"user_id": uid, "kind": "staff_code"}, {"$set": {"token_hash": hashlib.sha256(f"{uid}:{code}".encode()).hexdigest()}})


@pytest.fixture(scope="module", autouse=True)
def seed():
    orig = {k: db.member_settings.find_one({"key": k}) for k in ("welcome", "approval_email")}
    db.users.insert_many([
        {"user_id": IDS["admin"], "email": EMAILS["admin"], "name": "TEST_ Admin", "role": "admin", "created_at": _now()},
        {"user_id": IDS["staff"], "email": EMAILS["staff"], "name": "TEST_ Staff", "role": "admin", "email_verified": True,
         "auth_providers": ["email"], "require_login_code": True, "created_at": _now()},
        {"user_id": IDS["mem"], "email": EMAILS["mem"], "name": "TEST_Mem Sister", "role": "member", "member_status": "active",
         "portal_welcome_seen_at": _now(), "created_at": _now()},
        {"user_id": IDS["appl"], "email": EMAILS["appl"], "name": "TEST_Appl Sister", "role": "pending", "member_status": "applied", "created_at": _now()},
    ])
    db.user_credentials.insert_one({"user_id": IDS["staff"], "password_hash": bcrypt.hashpw(PW.encode(), bcrypt.gensalt()).decode()})
    db.user_sessions.insert_many([
        {"session_token": f"t59_admin_{RUN}", "user_id": IDS["admin"], "expires_at": _now(timedelta(days=1))},
        {"session_token": f"t59_mem_{RUN}", "user_id": IDS["mem"], "expires_at": _now(timedelta(days=1))},
    ])
    yield
    uids = list(IDS.values())
    for coll in ("users", "user_sessions", "auth_tokens", "user_credentials", "member_ledger", "ledger", "push_subscriptions"):
        db[coll].delete_many({"user_id": {"$in": uids}})
    db.rate_hits.delete_many({"key": {"$regex": RUN}})
    db.rate_hits.delete_many({"key": {"$regex": "^(member_email_test|staff_code)"}})
    db.login_attempts.delete_many({"identifier": {"$regex": RUN}})
    for k, doc in orig.items():
        if doc:
            db.member_settings.replace_one({"key": k}, doc, upsert=True)
        else:
            db.member_settings.delete_one({"key": k})


# ---- Member emails ----
class TestMemberEmails:
    def test_get_both_kinds(self):
        s = _sess(f"t59_admin_{RUN}")
        for k in ("welcome", "approval"):
            r = s.get(f"{BASE_URL}/api/admin/member-emails/{k}")
            assert r.status_code == 200, r.text
            d = r.json()
            for f in ("subject", "greeting", "message"):
                assert isinstance(d[f], str) and d[f]
                assert d["defaults"][f]

    def test_unknown_kind_404(self):
        s = _sess(f"t59_admin_{RUN}")
        assert s.get(f"{BASE_URL}/api/admin/member-emails/bogus").status_code == 404
        assert s.put(f"{BASE_URL}/api/admin/member-emails/bogus", json={"subject": "a", "greeting": "b", "message": "c"}).status_code == 404
        assert s.post(f"{BASE_URL}/api/admin/member-emails/bogus/preview", json={"subject": "a", "greeting": "b", "message": "c"}).status_code == 404

    def test_non_admin_forbidden(self):
        assert requests.get(f"{BASE_URL}/api/admin/member-emails/welcome").status_code == 401
        assert _sess(f"t59_mem_{RUN}").get(f"{BASE_URL}/api/admin/member-emails/welcome").status_code == 403
        assert _sess(f"t59_mem_{RUN}").put(f"{BASE_URL}/api/admin/member-emails/approval",
                                           json={"subject": "x", "greeting": "y", "message": "z"}).status_code == 403

    def test_put_validation_and_persist(self):
        s = _sess(f"t59_admin_{RUN}")
        r = s.put(f"{BASE_URL}/api/admin/member-emails/approval", json={"subject": "  ", "greeting": "g", "message": "m"})
        assert r.status_code == 400
        body = {"subject": "TEST_ Approved {first}", "greeting": "TEST_ Hi {first}", "message": "TEST_ approval body"}
        assert s.put(f"{BASE_URL}/api/admin/member-emails/approval", json=body).status_code == 200
        d = s.get(f"{BASE_URL}/api/admin/member-emails/approval").json()
        assert d["subject"] == body["subject"] and d["greeting"] == body["greeting"] and d["message"] == body["message"]

    def test_preview_replaces_first(self):
        s = _sess(f"t59_admin_{RUN}")
        r = s.post(f"{BASE_URL}/api/admin/member-emails/approval/preview",
                   json={"subject": "Yay {first}", "greeting": "Hey {first}!", "message": "TEST_ msg"})
        assert r.status_code == 200
        d = r.json()
        assert d["subject"] == "Yay TEST_"  # name "TEST_ Admin" -> first token
        assert "Hey TEST_!" in d["html"] and "TEST_ msg" in d["html"] and "{first}" not in d["html"]
        w = s.post(f"{BASE_URL}/api/admin/member-emails/welcome/preview", json={"subject": "W {first}", "greeting": "G {first}", "message": "TEST_ w"}).json()
        assert "G TEST_" in w["html"] and "/app" in w["html"]

    def test_preview_blank_falls_back_to_defaults(self):
        s = _sess(f"t59_admin_{RUN}")
        d = s.post(f"{BASE_URL}/api/admin/member-emails/approval/preview", json={"subject": "", "greeting": "", "message": ""}).json()
        assert d["subject"].startswith("You're approved")

    def test_send_test(self):
        s = _sess(f"t59_admin_{RUN}")
        r = s.post(f"{BASE_URL}/api/admin/member-emails/welcome/test", json={"subject": "S", "greeting": "G", "message": "M"})
        assert r.status_code in (200, 502), r.text
        if r.status_code == 200:
            assert r.json()["sent_to"] == EMAILS["admin"]

    def test_legacy_welcome_endpoints(self):
        s = _sess(f"t59_admin_{RUN}")
        r = s.get(f"{BASE_URL}/api/admin/members/welcome")
        assert r.status_code == 200 and "subject" in r.json()
        assert s.put(f"{BASE_URL}/api/admin/members/welcome", json={"subject": "TEST_ legacy {first}", "message": "TEST_ legacy body"}).status_code == 200
        d = s.get(f"{BASE_URL}/api/admin/member-emails/welcome").json()
        assert d["subject"] == "TEST_ legacy {first}" and d["greeting"]  # greeting kept / defaulted
        assert s.post(f"{BASE_URL}/api/admin/members/welcome/preview", json={"subject": "a", "message": "b"}).status_code == 200

    def test_approve_member(self):
        s = _sess(f"t59_admin_{RUN}")
        r = s.post(f"{BASE_URL}/api/admin/members/{IDS['appl']}/status", json={"action": "approve"})
        assert r.status_code == 200 and r.json()["status"] == "active"


# ---- Staff email code ----
class TestStaffCode:
    def _login(self):
        s = _sess()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAILS["staff"], "password": PW})
        assert r.status_code == 200, r.text
        assert r.json()["code_pending"] is True
        time.sleep(2.5)  # background _send_staff_code issues the code
        return s

    def test_pending_blocks_admin_then_verify(self):
        s = self._login()
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        assert me["role"] == "pending" and me["code_pending"] is True
        assert s.get(f"{BASE_URL}/api/admin/member-emails/welcome").status_code == 403
        assert s.get(f"{BASE_URL}/api/auth/staff-code/pref").status_code == 403
        mm = s.get(f"{BASE_URL}/api/members/me").json()
        assert mm["is_admin"] is False
        _set_code(IDS["staff"])
        assert s.post(f"{BASE_URL}/api/auth/staff-code/verify", json={"code": "000000"}).status_code == 400
        r = s.post(f"{BASE_URL}/api/auth/staff-code/verify", json={"code": "123456"})
        assert r.status_code == 200
        assert s.get(f"{BASE_URL}/api/auth/me").json()["role"] == "admin"
        assert s.get(f"{BASE_URL}/api/admin/member-emails/welcome").status_code == 200
        # replay of used code on a new pending session should fail
        s2 = self._login()
        db.auth_tokens.update_many({"user_id": IDS["staff"], "kind": "staff_code"}, {"$set": {"used": True}})
        assert s2.post(f"{BASE_URL}/api/auth/staff-code/verify", json={"code": "123456"}).status_code == 400

    def test_five_wrong_attempts_lock(self):
        s = self._login()
        _set_code(IDS["staff"])
        codes = [s.post(f"{BASE_URL}/api/auth/staff-code/verify", json={"code": "999999"}).status_code for _ in range(5)]
        assert codes == [400] * 5
        r = s.post(f"{BASE_URL}/api/auth/staff-code/verify", json={"code": "123456"})
        assert r.status_code == 429, r.text
        assert s.get(f"{BASE_URL}/api/admin/member-emails/welcome").status_code == 403

    def test_code_verify_session_not_pending(self):
        db.auth_tokens.insert_one({"token_hash": hashlib.sha256(f"{IDS['staff']}:654321".encode()).hexdigest(), "user_id": IDS["staff"],
                                   "kind": "code", "used": False, "attempts": 0, "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)})
        s = _sess()
        r = s.post(f"{BASE_URL}/api/auth/code-verify", json={"email": EMAILS["staff"], "code": "654321"})
        assert r.status_code == 200, r.text
        assert r.json()["code_pending"] is False
        assert s.get(f"{BASE_URL}/api/admin/member-emails/welcome").status_code == 200

    def test_pref_toggle_and_normal_login(self):
        s = _sess(f"t59_admin_{RUN}")
        assert s.get(f"{BASE_URL}/api/auth/staff-code/pref").json()["enabled"] is False
        assert s.put(f"{BASE_URL}/api/auth/staff-code/pref", json={"enabled": True}).json()["enabled"] is True
        assert db.users.find_one({"user_id": IDS["admin"]})["require_login_code"] is True
        assert s.put(f"{BASE_URL}/api/auth/staff-code/pref", json={"enabled": False}).status_code == 200
        db.users.update_one({"user_id": IDS["staff"]}, {"$set": {"require_login_code": False}})
        s2 = _sess()
        r = s2.post(f"{BASE_URL}/api/auth/login", json={"email": EMAILS["staff"], "password": PW})
        assert r.status_code == 200 and r.json()["code_pending"] is False
        assert s2.get(f"{BASE_URL}/api/admin/member-emails/welcome").status_code == 200
        db.users.update_one({"user_id": IDS["staff"]}, {"$set": {"require_login_code": True}})

    def test_pref_requires_admin(self):
        assert _sess(f"t59_mem_{RUN}").put(f"{BASE_URL}/api/auth/staff-code/pref", json={"enabled": True}).status_code == 403


# ---- App celebration ----
class TestCelebration:
    def test_app_celebrated(self):
        s = _sess(f"t59_mem_{RUN}")
        me = s.get(f"{BASE_URL}/api/members/me").json()
        assert me["app_celebrated"] is False and me["welcome_seen"] is True
        assert s.post(f"{BASE_URL}/api/members/app-celebrated").status_code == 200
        me = s.get(f"{BASE_URL}/api/members/me").json()
        assert me["app_celebrated"] is True and me["app_installed"] is True
        assert requests.post(f"{BASE_URL}/api/members/app-celebrated").status_code == 401
