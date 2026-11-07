"""Iter62: Team Access sign-in activity, staff access expiry, Club team badge (owner-only), directory club_team, cron auth."""
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
H = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}
A, B, C = "qa62_staff_a", "qa62_staff_b", "qa62_staff_c"


def _s(tok, extra=None):
    s = requests.Session()
    s.headers.update({**H, **(extra or {})})
    s.cookies.set("session_token", tok)
    return s


@pytest.fixture(scope="module")
def owner():
    # X-Preview-Level: full keeps full level but skips owner's last-seen bump
    return _s("qa_owner_tok", {"X-Preview-Level": "full"})


@pytest.fixture(scope="module")
def admin():
    return _s("qa_tok_123")


def _today_et():
    return datetime.now(ZoneInfo("America/New_York")).date()


# --- Sign-in activity ---
class TestActivity:
    def test_team_fields(self, owner):
        r = owner.get(f"{BASE_URL}/api/admin/team")
        assert r.status_code == 200
        users = {u["user_id"]: u for u in r.json()["users"]}
        assert A in users and B in users and C in users
        assert users[A]["admin_last_seen_at"]
        assert "admin_last_seen_at" not in users[B] or not users[B]["admin_last_seen_at"]
        me = users[r.json()["me"]]
        assert me["is_owner"] is True

    def test_last_seen_bump_and_preview_skip(self):
        db.users.update_one({"user_id": "qa_user"}, {"$unset": {"admin_last_seen_at": ""}})
        r = _s("qa_tok_123", {"X-Preview-Level": "full"}).get(f"{BASE_URL}/api/admin/team")
        assert r.status_code == 200
        assert not db.users.find_one({"user_id": "qa_user"}).get("admin_last_seen_at")
        r = _s("qa_tok_123").get(f"{BASE_URL}/api/admin/team")
        assert r.status_code == 200
        seen1 = db.users.find_one({"user_id": "qa_user"}).get("admin_last_seen_at")
        assert seen1
        _s("qa_tok_123").get(f"{BASE_URL}/api/admin/team")
        assert db.users.find_one({"user_id": "qa_user"}).get("admin_last_seen_at") == seen1  # throttled 1/hour


# --- Expiry (owner only) ---
class TestExpiry:
    def test_non_owner_forbidden(self, admin):
        d = (_today_et() + timedelta(days=10)).isoformat()
        assert admin.post(f"{BASE_URL}/api/admin/team/{A}/expiry", json={"date": d}).status_code == 403
        assert admin.post(f"{BASE_URL}/api/admin/team/{A}/badge", json={"on": True}).status_code == 403

    def test_past_and_today_rejected(self, owner):
        for d in [_today_et().isoformat(), (_today_et() - timedelta(days=1)).isoformat(), "not-a-date"]:
            r = owner.post(f"{BASE_URL}/api/admin/team/{A}/expiry", json={"date": d})
            assert r.status_code == 400, (d, r.text)

    def test_owner_own_access_cannot_expire(self, owner):
        me = owner.get(f"{BASE_URL}/api/admin/team").json()["me"]
        d = (_today_et() + timedelta(days=10)).isoformat()
        r = owner.post(f"{BASE_URL}/api/admin/team/{me}/expiry", json={"date": d})
        assert r.status_code == 400
        other = db.users.find_one({"email": "caringsistersclub@gmail.com"})
        if other:
            assert owner.post(f"{BASE_URL}/api/admin/team/{other['user_id']}/expiry", json={"date": d}).status_code == 400

    def test_set_and_clear(self, owner):
        d = (_today_et() + timedelta(days=10)).isoformat()
        r = owner.post(f"{BASE_URL}/api/admin/team/{A}/expiry", json={"date": d})
        assert r.status_code == 200 and r.json()["staff_expires_on"] == d
        users = {u["user_id"]: u for u in owner.get(f"{BASE_URL}/api/admin/team").json()["users"]}
        assert users[A]["staff_expires_on"] == d
        log = owner.get(f"{BASE_URL}/api/admin/team/log").json()
        rows = log if isinstance(log, list) else log.get("rows", log.get("log", []))
        assert any(e["action"] == "expiry" and e["target"].get("user_id") == A and e.get("expires_on") == d for e in rows)
        r = owner.post(f"{BASE_URL}/api/admin/team/{A}/expiry", json={"date": None})
        assert r.status_code == 200 and r.json()["staff_expires_on"] is None
        assert "staff_expires_on" not in db.users.find_one({"user_id": A})

    def test_compact_date_format_normalised(self, owner):
        # Python 3.11 fromisoformat accepts '20261201' - should be stored as YYYY-MM-DD
        d = (_today_et() + timedelta(days=20))
        r = owner.post(f"{BASE_URL}/api/admin/team/{C}/expiry", json={"date": d.strftime("%Y%m%d")})
        stored = db.users.find_one({"user_id": C}).get("staff_expires_on")
        owner.post(f"{BASE_URL}/api/admin/team/{C}/expiry", json={"date": None})
        assert r.status_code == 400 or stored == d.isoformat(), f"stored raw value {stored!r}"

    def test_not_found(self, owner):
        d = (_today_et() + timedelta(days=10)).isoformat()
        assert owner.post(f"{BASE_URL}/api/admin/team/nope_xyz/expiry", json={"date": d}).status_code == 404
        assert owner.post(f"{BASE_URL}/api/admin/team/nope_xyz/badge", json={"on": True}).status_code == 404


# --- Club team badge + directory ---
class TestBadge:
    def test_badge_on_directory(self, owner):
        r = owner.post(f"{BASE_URL}/api/admin/team/{A}/badge", json={"on": True})
        assert r.status_code == 200 and r.json()["club_team_badge"] is True
        d = owner.get(f"{BASE_URL}/api/members/directory")
        assert d.status_code == 200
        m = {x["user_id"]: x for x in d.json()}
        assert m[A]["club_team"] is True
        assert m[B]["club_team"] is False
        assert all(isinstance(x["club_team"], bool) for x in d.json())

    def test_badge_off(self, owner):
        assert owner.post(f"{BASE_URL}/api/admin/team/{B}/badge", json={"on": False}).status_code == 200
        m = {x["user_id"]: x for x in owner.get(f"{BASE_URL}/api/members/directory").json()}
        assert m[B]["club_team"] is False

    def test_badge_needs_csrf(self):
        s = requests.Session()
        s.cookies.set("session_token", "qa_owner_tok")
        assert s.post(f"{BASE_URL}/api/admin/team/{A}/badge", json={"on": False}).status_code in (400, 403)


# --- Cron auth (never call with real secret) ---
class TestCron:
    def test_no_auth(self):
        assert requests.post(f"{BASE_URL}/api/cron/staff-expiry", json={}).status_code == 401

    def test_wrong_secret(self):
        r = requests.post(f"{BASE_URL}/api/cron/staff-expiry", json={}, headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401
