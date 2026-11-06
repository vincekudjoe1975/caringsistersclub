# Iteration 58: App QR, app-install stats & nudges, email one-time sign-in code, app block in emails
import os
import sys
import uuid
import hashlib
import asyncio
from datetime import datetime, timezone, timedelta

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


def _now(delta=timedelta()):
    return (datetime.now(timezone.utc) + delta).isoformat()


def _clear_code_rate():
    db.rate_hits.delete_many({"key": {"$regex": "^(auth_code|app-nudge)"}})


@pytest.fixture(scope="module")
def seed():
    ids = {
        "admin": f"test58_admin_{RUN}", "member": f"test58_mem_{RUN}",
        "a": f"test58_a_{RUN}", "b": f"test58_b_{RUN}", "c": f"test58_c_{RUN}", "code": f"test58_code_{RUN}",
    }
    db.users.insert_many([
        {"user_id": ids["admin"], "email": f"test58.admin.{RUN}@example.com", "name": "TEST_ Admin", "role": "admin", "created_at": _now()},
        {"user_id": ids["member"], "email": f"test58.mem.{RUN}@example.com", "name": "TEST_ Member", "role": "member", "member_status": "active", "created_at": _now(), "app_installed_at": _now()},
        {"user_id": ids["a"], "email": f"test58.a.{RUN}@example.com", "name": "TEST_ Alpha", "role": "member", "member_status": "active", "created_at": _now()},
        {"user_id": ids["b"], "email": f"test58.b.{RUN}@example.com", "name": "TEST_ Beta", "role": "member", "member_status": "active", "created_at": _now(), "app_nudged_at": _now(-timedelta(days=2))},
        {"user_id": ids["c"], "email": f"test58.c.{RUN}@example.com", "name": "TEST_ Gamma", "role": "member", "member_status": "active", "created_at": _now(), "app_nudged_at": _now(-timedelta(days=9))},
        {"user_id": ids["code"], "email": f"test58.code.{RUN}@example.com", "name": "TEST_ Code", "role": "pending", "created_at": _now(), "email_verified": False},
    ])
    db.user_sessions.insert_many([
        {"session_token": f"t58_admin_{RUN}", "user_id": ids["admin"], "expires_at": _now(timedelta(days=1))},
        {"session_token": f"t58_mem_{RUN}", "user_id": ids["member"], "expires_at": _now(timedelta(days=1))},
    ])
    _clear_code_rate()
    yield ids
    db.users.delete_many({"user_id": {"$in": list(ids.values())}})
    db.user_sessions.delete_many({"user_id": {"$in": list(ids.values())}})
    db.auth_tokens.delete_many({"user_id": {"$in": list(ids.values())}})
    _clear_code_rate()


def admin_s(seed):
    s = requests.Session(); s.headers.update(H); s.cookies.set("session_token", f"t58_admin_{RUN}"); return s


def mem_s(seed):
    s = requests.Session(); s.headers.update(H); s.cookies.set("session_token", f"t58_mem_{RUN}"); return s


# --- QR ---
def test_qr_png():
    r = requests.get(f"{BASE_URL}/api/qr/app.png")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    try:
        from PIL import Image
        import io
        from pyzbar.pyzbar import decode  # optional
        txt = decode(Image.open(io.BytesIO(r.content)))[0].data.decode()
        assert txt == "https://caringsistersclub.org/app"
    except ImportError:
        pass


# --- Email html includes app block ---
def test_email_app_block_in_welcome_and_approval():
    sys.path.insert(0, '/app/backend')
    import server
    blk = server._app_block_html()
    assert "/app\"" in blk and "/api/qr/app.png" in blk and "Get the app" in blk
    html = server._member_email_html("x", "y", "z", "Open", "/members", blk)
    assert blk in html
    w = asyncio.new_event_loop().run_until_complete(server._welcome_html({"name": "Test Sister", "email": "x@example.com", "user_id": "x"}, {"message": "Hello"}))
    assert "/api/qr/app.png" in w and f"{server.PUBLIC_APP_URL}/app" in w
    import inspect
    src = inspect.getsource(server._send_approved_alert)
    assert "_app_block_html()" in src


# --- App installs stats ---
def test_app_installs_admin(seed):
    r = admin_s(seed).get(f"{BASE_URL}/api/admin/members/app-installs")
    assert r.status_code == 200
    d = r.json()
    ids = {x["user_id"]: x for x in d["rows"]}
    for k in ("member", "a", "b", "c"):
        assert seed[k] in ids
    assert seed["admin"] not in ids and seed["code"] not in ids
    assert d["total"] == len(d["rows"])
    assert d["installed"] == sum(1 for x in d["rows"] if x.get("app_installed_at"))
    assert "_id" not in d["rows"][0]


def test_app_installs_forbidden_for_member(seed):
    assert mem_s(seed).get(f"{BASE_URL}/api/admin/members/app-installs").status_code == 403
    assert requests.get(f"{BASE_URL}/api/admin/members/app-installs").status_code == 401


def test_app_nudge_user_ids_and_repeat(seed):
    s = admin_s(seed)
    r = s.post(f"{BASE_URL}/api/admin/members/app-nudge", json={"user_ids": [seed["a"], seed["b"], seed["c"], seed["member"]]})
    assert r.status_code == 200, r.text
    assert r.json()["sent"] == 2  # a (never) + c (9 days ago); b recent, member installed
    ua, ub, uc, um = (db.users.find_one({"user_id": seed[k]}) for k in ("a", "b", "c", "member"))
    assert ua.get("app_nudged_at") and uc["app_nudged_at"] > _now(-timedelta(minutes=5))
    assert ub["app_nudged_at"] < _now(-timedelta(days=1))
    assert "app_nudged_at" not in um
    r2 = s.post(f"{BASE_URL}/api/admin/members/app-nudge", json={"user_ids": [seed["a"], seed["c"]]})
    assert r2.json()["sent"] == 0


def test_app_nudge_all_and_forbidden(seed):
    # reset a to old nudge so 'all' picks it up
    db.users.update_one({"user_id": seed["a"]}, {"$set": {"app_nudged_at": _now(-timedelta(days=8))}})
    s = admin_s(seed)
    real = db.users.count_documents({"member_status": "active", "user_id": {"$not": {"$regex": "^test58_"}}, "app_installed_at": {"$exists": False}})
    if real:
        pytest.skip("Real active un-installed members exist; skipping all:true to avoid emailing them")
    r = s.post(f"{BASE_URL}/api/admin/members/app-nudge", json={"all": True})
    assert r.status_code == 200
    assert r.json()["sent"] == 1
    assert s.post(f"{BASE_URL}/api/admin/members/app-nudge", json={"all": True}).json()["sent"] == 0
    assert mem_s(seed).post(f"{BASE_URL}/api/admin/members/app-nudge", json={"all": True}).status_code == 403


# --- Email code request ---
def test_code_request_unknown_email_generic():
    _clear_code_rate()
    r = requests.post(f"{BASE_URL}/api/auth/code-request", json={"email": f"nobody.{RUN}@example.com"}, headers=H)
    assert r.status_code == 200 and r.json()["ok"] is True
    assert "6-digit code" in r.json()["message"]


def test_code_request_stores_token_and_replaces(seed):
    _clear_code_rate()
    em = f"test58.code.{RUN}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/code-request", json={"email": em.upper()}, headers=H)
    assert r.status_code == 200
    toks = list(db.auth_tokens.find({"user_id": seed["code"], "kind": "code"}))
    assert len(toks) == 1
    t = toks[0]
    assert len(t["token_hash"]) == 64 and t["attempts"] == 0 and t["used"] is False
    exp = t["expires_at"].replace(tzinfo=timezone.utc)
    mins = (exp - datetime.now(timezone.utc)).total_seconds() / 60
    assert 9 < mins <= 10.1
    first_hash = t["token_hash"]
    requests.post(f"{BASE_URL}/api/auth/code-request", json={"email": em}, headers=H)
    toks = list(db.auth_tokens.find({"user_id": seed["code"], "kind": "code"}))
    assert len(toks) == 1 and toks[0]["token_hash"] != first_hash


def test_code_request_rate_limited():
    _clear_code_rate()
    codes = [requests.post(f"{BASE_URL}/api/auth/code-request", json={"email": f"rl{i}.{RUN}@example.com"}, headers=H).status_code for i in range(7)]
    assert 429 in codes, codes
    _clear_code_rate()


def test_code_request_invalid_email():
    _clear_code_rate()
    assert requests.post(f"{BASE_URL}/api/auth/code-request", json={"email": "notanemail"}, headers=H).status_code == 400


# --- Email code verify ---
def _insert_code(uid, code, minutes=10, attempts=0):
    db.auth_tokens.delete_many({"user_id": uid, "kind": "code"})
    db.auth_tokens.insert_one({"token_hash": hashlib.sha256(f"{uid}:{code}".encode()).hexdigest(), "user_id": uid, "kind": "code",
                               "used": False, "attempts": attempts, "expires_at": datetime.now(timezone.utc) + timedelta(minutes=minutes),
                               "created_at": datetime.now(timezone.utc)})


def test_code_verify_wrong_then_lockout(seed):
    _clear_code_rate()
    uid, em = seed["code"], f"test58.code.{RUN}@example.com"
    _insert_code(uid, "123456")
    for i in range(5):
        r = requests.post(f"{BASE_URL}/api/auth/code-verify", json={"email": em, "code": "000000"}, headers=H)
        assert r.status_code == 400, (i, r.status_code)
    assert db.auth_tokens.find_one({"user_id": uid, "kind": "code"})["attempts"] == 5
    r = requests.post(f"{BASE_URL}/api/auth/code-verify", json={"email": em, "code": "123456"}, headers=H)
    assert r.status_code == 429
    assert db.auth_tokens.find_one({"user_id": uid, "kind": "code"})["used"] is True
    # burned: correct code still rejected
    assert requests.post(f"{BASE_URL}/api/auth/code-verify", json={"email": em, "code": "123456"}, headers=H).status_code == 400


def test_code_verify_success_then_reuse(seed):
    _clear_code_rate()
    uid, em = seed["code"], f"test58.code.{RUN}@example.com"
    _insert_code(uid, "654321")
    s = requests.Session(); s.headers.update(H)
    r = s.post(f"{BASE_URL}/api/auth/code-verify", json={"email": em, "code": "654 321"})
    assert r.status_code == 200, r.text
    assert r.json()["user_id"] == uid and "_id" not in r.json()
    sc = r.headers.get("set-cookie", "")
    assert "session_token=" in sc and "HttpOnly" in sc and "Secure" in sc
    assert db.users.find_one({"user_id": uid})["email_verified"] is True
    me = s.get(f"{BASE_URL}/api/auth/me")
    assert me.status_code == 200 and me.json()["user_id"] == uid
    assert requests.post(f"{BASE_URL}/api/auth/code-verify", json={"email": em, "code": "654321"}, headers=H).status_code == 400


def test_code_verify_expired_and_bad_input(seed):
    _clear_code_rate()
    uid, em = seed["code"], f"test58.code.{RUN}@example.com"
    _insert_code(uid, "111222", minutes=-1)
    assert requests.post(f"{BASE_URL}/api/auth/code-verify", json={"email": em, "code": "111222"}, headers=H).status_code == 400
    assert requests.post(f"{BASE_URL}/api/auth/code-verify", json={"email": em, "code": "12"}, headers=H).status_code == 400
    assert requests.post(f"{BASE_URL}/api/auth/code-verify", json={"email": f"nobody.{RUN}@example.com", "code": "123456"}, headers=H).status_code == 400
