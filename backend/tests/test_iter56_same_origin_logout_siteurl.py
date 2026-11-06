# Iteration 56: same-origin API fix — logout cookie attributes, site_url *.emergent.host ignored for email links
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
HDR = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin():
    uid = f"TEST_qa56_{uuid.uuid4().hex[:8]}"
    tok = f"TEST_tok56_{uuid.uuid4().hex}"
    db.users.insert_one({"user_id": uid, "email": f"{uid}@example.com", "name": "TEST QA56", "role": "admin"})
    db.user_sessions.insert_one({"session_token": tok, "user_id": uid, "expires_at": "2099-01-01T00:00:00+00:00"})
    backup = db.settings.find_one({"key": "site"}, {"_id": 0, "site_url": 1, "detected_site_url": 1}) or {}
    s = requests.Session()
    s.headers.update(HDR)
    s.cookies.set("session_token", tok)
    yield s
    db.users.delete_one({"user_id": uid})
    db.user_sessions.delete_many({"user_id": uid})
    db.settings.update_one({"key": "site"}, {"$set": {"site_url": backup.get("site_url", ""),
                                                      "detected_site_url": backup.get("detected_site_url", "")}})
    # refresh in-memory PUBLIC_APP_URL with restored value
    r = s.put(f"{BASE_URL}/api/admin/settings", json={"site_url": backup.get("site_url", "")})


@pytest.fixture(scope="module")
def event_id(admin):
    r = admin.post(f"{BASE_URL}/api/admin/events", json={"title": "TEST_QA56 Event", "date": "2099-01-01", "capacity": 5})
    assert r.status_code in (200, 201), r.text
    eid = r.json()["id"]
    yield eid
    admin.delete(f"{BASE_URL}/api/admin/events/{eid}")


def _ics_url(eid):
    r = requests.get(f"{BASE_URL}/api/events/{eid}/calendar.ics")
    assert r.status_code == 200
    line = [l for l in r.text.split("\r\n") if l.startswith("URL:")][0]
    return line[4:]


class TestLogoutCookie:
    def test_logout_delete_cookie_attrs(self):
        uid = f"TEST_qa56l_{uuid.uuid4().hex[:8]}"
        tok = f"TEST_tok56l_{uuid.uuid4().hex}"
        db.users.insert_one({"user_id": uid, "email": f"{uid}@example.com", "name": "TEST L", "role": "pending"})
        db.user_sessions.insert_one({"session_token": tok, "user_id": uid, "expires_at": "2099-01-01T00:00:00+00:00"})
        try:
            s = requests.Session()
            s.headers.update(HDR)
            s.cookies.set("session_token", tok)
            assert s.get(f"{BASE_URL}/api/auth/me").status_code == 200
            r = s.post(f"{BASE_URL}/api/auth/logout")
            assert r.status_code == 200
            sc = r.headers.get("set-cookie", "").lower()
            print("Set-Cookie:", sc)
            assert "session_token=" in sc and "max-age=0" in sc
            assert "secure" in sc and "httponly" in sc and "samesite=none" in sc and "path=/" in sc
            assert db.user_sessions.find_one({"session_token": tok}) is None
            s2 = requests.Session(); s2.headers.update(HDR); s2.cookies.set("session_token", tok)
            assert s2.get(f"{BASE_URL}/api/auth/me").status_code == 401
        finally:
            db.users.delete_one({"user_id": uid})
            db.user_sessions.delete_many({"user_id": uid})

    def test_logout_without_cookie_ok(self):
        r = requests.post(f"{BASE_URL}/api/auth/logout", headers=HDR)
        assert r.status_code == 200
        assert r.json()["message"] == "Logged out"


class TestSiteUrl:
    def test_custom_domain_site_url_used(self, admin, event_id):
        r = admin.put(f"{BASE_URL}/api/admin/settings", json={"site_url": "https://caringsistersclub.org"})
        assert r.status_code == 200 and r.json()["site_url"] == "https://caringsistersclub.org"
        assert _ics_url(event_id) == "https://caringsistersclub.org/events"

    def test_emergent_host_site_url_ignored(self, admin, event_id):
        r = admin.put(f"{BASE_URL}/api/admin/settings", json={"site_url": "https://caring-sisters-clone.emergent.host"})
        assert r.status_code == 200
        print("stored site_url:", r.json()["site_url"], "detected:", r.json()["detected_site_url"])
        url = _ics_url(event_id)
        print("ICS URL:", url)
        assert "emergent.host" not in url
        detected = r.json()["detected_site_url"]
        expected = (detected if detected else "https://caringsistersclub.org") + "/events"
        assert url == expected or url == "https://caringsistersclub.org/events"

    def test_emergent_host_uppercase_ignored(self, admin, event_id):
        r = admin.put(f"{BASE_URL}/api/admin/settings", json={"site_url": "https://Caring-Sisters-Clone.EMERGENT.HOST/"})
        assert r.status_code == 200
        assert "emergent.host" not in _ics_url(event_id).lower()

    def test_www_site_url_used(self, admin, event_id):
        r = admin.put(f"{BASE_URL}/api/admin/settings", json={"site_url": "https://www.caringsistersclub.org"})
        assert r.status_code == 200
        assert _ics_url(event_id) == "https://www.caringsistersclub.org/events"

    def test_invalid_site_url_rejected(self, admin):
        r = admin.put(f"{BASE_URL}/api/admin/settings", json={"site_url": "http://caringsistersclub.org"})
        assert r.status_code == 400


class TestSmoke:
    def test_public_endpoints(self):
        for p in ["/api/home-content", "/api/settings", "/api/events", "/api/payments/mode"]:
            r = requests.get(f"{BASE_URL}{p}")
            assert r.status_code == 200, p
            assert "_id" not in r.text

    def test_cors_preview_origin_with_credentials(self):
        r = requests.options(f"{BASE_URL}/api/auth/me", headers={"Origin": BASE_URL, "Access-Control-Request-Method": "GET"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-credentials") == "true"
