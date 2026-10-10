"""Backend tests for review request: Volunteer Hours, Program Interest Report,
Impact Email tracking (open/click), Story-request toggle, Program signup counts update.
Uses QA admin cookie (session_token=qa_tok_123) created by qa_session.py up.
"""
import os
import re
import time
from datetime import date, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_COOKIE = {"session_token": "qa_tok_123"}
CSRF = {"X-Requested-With": "XMLHttpRequest"}


# ---------- helpers ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.cookies.set("session_token", "qa_tok_123")
    s.headers.update(CSRF)
    # verify admin
    r = s.get(f"{API}/auth/me", timeout=10)
    if r.status_code != 200 or (r.json() or {}).get("role") != "admin":
        pytest.skip(f"QA admin not available: {r.status_code} {r.text[:120]}")
    return s


@pytest.fixture(scope="module")
def wellness_program():
    r = requests.get(f"{API}/programs/wellness-workshops", timeout=10)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Volunteer Hours ----------
class TestVolunteerHours:
    created_ids = []

    def _payload(self, hours=2.5, d=None, email="TEST_hours1@example.com"):
        return {
            "name": "TEST Hours",
            "email": email,
            "program_id": self.prog_id,
            "date": (d or date.today().isoformat()),
            "hours": hours,
            "note": "QA test entry",
        }

    @pytest.fixture(autouse=True)
    def _bind(self, wellness_program):
        self.prog_id = wellness_program["id"]

    def test_submit_valid_hours(self):
        r = requests.post(f"{API}/volunteer-hours", json=self._payload(), headers=CSRF, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data
        TestVolunteerHours.created_ids.append(data["id"])

    def test_submit_second_entry_for_reject(self):
        r = requests.post(f"{API}/volunteer-hours", json=self._payload(hours=1.0, email="TEST_hours2@example.com"),
                          headers=CSRF, timeout=10)
        assert r.status_code == 200
        TestVolunteerHours.created_ids.append(r.json()["id"])

    def test_hours_out_of_range_low(self):
        r = requests.post(f"{API}/volunteer-hours", json=self._payload(hours=0.1), headers=CSRF, timeout=10)
        assert r.status_code == 400
        assert "0.25" in r.text or "between" in r.text.lower()

    def test_hours_out_of_range_high(self):
        r = requests.post(f"{API}/volunteer-hours", json=self._payload(hours=30), headers=CSRF, timeout=10)
        assert r.status_code == 400

    def test_future_date_blocked(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        r = requests.post(f"{API}/volunteer-hours", json=self._payload(d=future), headers=CSRF, timeout=10)
        assert r.status_code == 400
        assert "future" in r.text.lower() or "past year" in r.text.lower()

    def test_invalid_program(self):
        payload = self._payload()
        payload["program_id"] = "nonexistent_prog_id_xxx"
        r = requests.post(f"{API}/volunteer-hours", json=payload, headers=CSRF, timeout=10)
        assert r.status_code == 400
        assert "program" in r.text.lower()

    def test_admin_list_shows_pending(self, admin_session):
        r = admin_session.get(f"{API}/admin/volunteer-hours", timeout=10)
        assert r.status_code == 200
        items = r.json().get("items", [])
        ids = {i["id"] for i in items}
        for cid in TestVolunteerHours.created_ids:
            assert cid in ids

    def test_approve_entry_and_summary_updates(self, admin_session):
        hid = TestVolunteerHours.created_ids[0]
        r = admin_session.post(f"{API}/admin/volunteer-hours/{hid}/approve", timeout=10)
        assert r.status_code == 200
        # verify status
        r2 = admin_session.get(f"{API}/admin/volunteer-hours", timeout=10)
        item = next(i for i in r2.json()["items"] if i["id"] == hid)
        assert item["status"] == "approved"
        # summary reflects approved hours
        s = requests.get(f"{API}/volunteer-hours/summary", timeout=10).json()
        assert s["total_hours"] >= 2.5
        assert any(b["program"].lower().startswith("wellness") for b in s["by_program"])

    def test_reject_second_entry(self, admin_session):
        hid = TestVolunteerHours.created_ids[1]
        r = admin_session.post(f"{API}/admin/volunteer-hours/{hid}/reject", timeout=10)
        assert r.status_code == 200
        r2 = admin_session.get(f"{API}/admin/volunteer-hours", timeout=10)
        item = next(i for i in r2.json()["items"] if i["id"] == hid)
        assert item["status"] == "rejected"

    def test_approve_already_reviewed_404(self, admin_session):
        hid = TestVolunteerHours.created_ids[0]
        r = admin_session.post(f"{API}/admin/volunteer-hours/{hid}/approve", timeout=10)
        assert r.status_code == 404


# ---------- Program interest report ----------
class TestProgramReport:
    def test_report_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/reports/program-signups?months=6", timeout=10)
        assert r.status_code == 200
        data = r.json()
        # Expect items list and 6 month columns
        assert isinstance(data, dict)
        # Shape could be {items:[{program, counts:[], total, trend}], months:[...]} or similar
        # Validate basic keys exist
        for key in ("rows", "months", "totals"):
            assert key in data, f"missing {key} in {list(data.keys())}"
        assert len(data["months"]) == 6
        assert len(data["totals"]) == 6
        for row in data["rows"]:
            assert "program" in row and "counts" in row and "trend" in row
            assert len(row["counts"]) == 6

    def test_report_requires_admin(self):
        r = requests.get(f"{API}/admin/reports/program-signups", timeout=10)
        assert r.status_code in (401, 403)

    def test_signup_increments_current_month(self, admin_session, wellness_program):
        slug = "wellness-workshops"
        before = admin_session.get(f"{API}/admin/reports/program-signups?months=6", timeout=10).json()
        row_before = next((r for r in before["rows"] if r.get("program") == wellness_program["title"]), None)
        payload = {"name": "TEST Signup", "email": "TEST_signup_report@example.com", "phone": "+15551234567",
                   "message": "QA report test"}
        time.sleep(0.3)
        r = requests.post(f"{API}/programs/{slug}/signup", json=payload, headers=CSRF, timeout=10)
        assert r.status_code == 200, r.text
        after = admin_session.get(f"{API}/admin/reports/program-signups?months=6", timeout=10).json()
        row_after = next((r for r in after["rows"] if r.get("program") == wellness_program["title"]), None)
        assert row_after is not None, "wellness program row missing after signup"
        before_val = (row_before["counts"][-1] if row_before else 0)
        after_val = row_after["counts"][-1]
        assert after_val >= before_val + 1, f"expected current-month count to increment, before={before_val} after={after_val}"
        # trend should become 'up' or at least not 'flat' with 0 totals now
        assert row_after["trend"] in ("up", "flat")  # up expected; flat tolerated if prior months also zero


# ---------- Impact Email tracking ----------
class TestImpactTracking:
    def test_pixel_gif_returns_image(self):
        r = requests.get(f"{API}/t/impact/fakecid/open.gif?r=fakerid", timeout=10, allow_redirects=False)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/gif")
        assert len(r.content) > 10

    def test_click_safe_relative_redirects_to_site_root(self):
        # //evil.com should NOT redirect off-site
        r = requests.get(f"{API}/t/impact/fakecid/click?r=fakerid&u=//evil.com", timeout=10, allow_redirects=False)
        assert r.status_code in (301, 302, 307)
        loc = r.headers.get("location", "")
        assert "evil.com" not in loc
        # Should go to app root
        assert loc.rstrip("/").endswith(BASE_URL.rstrip("/")) or loc.endswith("/") or loc.startswith(BASE_URL)

    def test_click_valid_relative_path(self):
        r = requests.get(f"{API}/t/impact/fakecid/click?r=fakerid&u=/programs", timeout=10, allow_redirects=False)
        assert r.status_code in (301, 302, 307)
        assert "/programs" in r.headers.get("location", "")

    def test_history_initial_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/impact-email/history", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)


# ---------- Story-request toggle ----------
class TestStoryRequestToggle:
    def test_default_or_current_on(self, admin_session):
        r = admin_session.get(f"{API}/admin/settings", timeout=10)
        assert r.status_code == 200
        assert "story_requests_enabled" in r.json()

    def test_toggle_off_then_on(self, admin_session):
        for flag in (False, True):
            r = admin_session.put(f"{API}/admin/settings", json={"story_requests_enabled": flag}, timeout=10)
            assert r.status_code == 200, r.text
            r2 = admin_session.get(f"{API}/admin/settings", timeout=10)
            assert r2.json().get("story_requests_enabled") is flag
        # restore ON (ensure final state is ON)
        admin_session.put(f"{API}/admin/settings", json={"story_requests_enabled": True}, timeout=10)


# ---------- cleanup ----------
def test_zz_cleanup(admin_session):
    """Delete leftover QA artefacts (hours entries + signup submissions)."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient  # noqa
    except Exception:
        pass
    # Use direct mongo via a small helper endpoint if available, otherwise do a best-effort via pymongo
    try:
        import pymongo
        mongo_url = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
        dbname = os.environ.get("DB_NAME") or "test_database"
        cli = pymongo.MongoClient(mongo_url)
        d = cli[dbname]
        res1 = d.volunteer_hours.delete_many({"email": {"$regex": "@example.com$"}})
        res2 = d.submissions.delete_many({"type": "program_signup", "data.email": {"$regex": "@example.com$"}})
        print(f"cleanup hours={res1.deleted_count} signups={res2.deleted_count}")
    except Exception as e:
        print("cleanup skipped:", e)
    # Restore story_requests ON
    admin_session.put(f"{API}/admin/settings", json={"story_requests_enabled": True}, timeout=10)
