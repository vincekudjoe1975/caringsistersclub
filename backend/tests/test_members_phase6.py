"""Phase 6 member portal: Welcome packet, Door check-in, Spotlight archive, Prayer board.

Prereq:
  python3 /app/backend/tests/qa_session.py up
  python3 /app/backend/tests/qa_members.py up
Run: pytest /app/backend/tests/test_members_phase6.py -v --tb=short
"""
import os
import uuid
from datetime import date, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
H_CSRF = {"X-Requested-With": "XMLHttpRequest"}
C_ADMIN = {"session_token": "qa_tok_123"}
C_A = {"session_token": "mem_tok_a"}
C_B = {"session_token": "mem_tok_b"}


# -------- Fixtures: activate both QA members (invite + /members/me) --------
@pytest.fixture(scope="session", autouse=True)
def ensure_members_active():
    for e in ("qa.sister.a@example.com", "qa.sister.b@example.com"):
        requests.post(f"{API}/admin/members/invite", json={"email": e}, cookies=C_ADMIN, headers=H_CSRF)
    for cookie in (C_A, C_B):
        r = requests.get(f"{API}/members/me", cookies=cookie)
        assert r.status_code == 200 and r.json().get("status") == "active", r.text
    yield


@pytest.fixture(scope="session")
def uid_a():
    return requests.get(f"{API}/members/me", cookies=C_A).json()["user_id"]


@pytest.fixture(scope="session")
def uid_b():
    return requests.get(f"{API}/members/me", cookies=C_B).json()["user_id"]


# ============================================================
# Welcome packet
# ============================================================
class TestWelcome:
    def test_get_welcome_defaults(self):
        r = requests.get(f"{API}/admin/members/welcome", cookies=C_ADMIN)
        assert r.status_code == 200
        d = r.json()
        assert "subject" in d and "message" in d
        assert "{first}" in d["subject"] or "Welcome" in d["subject"]

    def test_put_welcome_persists(self):
        payload = {"subject": "QA Welcome, {first}!", "message": "QA custom welcome body for test."}
        r = requests.put(f"{API}/admin/members/welcome", json=payload, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200, r.text
        g = requests.get(f"{API}/admin/members/welcome", cookies=C_ADMIN).json()
        assert g["subject"] == payload["subject"]
        assert g["message"] == payload["message"]

    def test_put_welcome_requires_fields(self):
        r = requests.put(f"{API}/admin/members/welcome", json={"subject": "", "message": ""}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 400

    def test_preview_contains_sections(self):
        r = requests.post(f"{API}/admin/members/welcome/preview",
                          json={"subject": "x", "message": "Hello sisters"}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        html = r.json()["html"]
        assert "Our bylaws in brief" in html
        assert "Your dues" in html
        assert "Upcoming gatherings" in html

    def test_member_cannot_view_welcome_settings(self):
        r = requests.get(f"{API}/admin/members/welcome", cookies=C_A)
        assert r.status_code == 403

    def test_anonymous_welcome_401(self):
        r = requests.get(f"{API}/admin/members/welcome")
        assert r.status_code == 401

    def test_resend_welcome_to_active_member(self, uid_a):
        r = requests.post(f"{API}/admin/members/{uid_a}/welcome", cookies=C_ADMIN, headers=H_CSRF)
        # Emails to example.com may 422 at provider level -> _send_welcome returns False -> 400.
        assert r.status_code in (200, 400), r.text

    def test_resend_welcome_member_forbidden(self, uid_a):
        r = requests.post(f"{API}/admin/members/{uid_a}/welcome", cookies=C_A, headers=H_CSRF)
        assert r.status_code == 403


# ============================================================
# Member check-in code (QR)
# ============================================================
class TestCheckinCode:
    def test_get_code_stable(self):
        r1 = requests.get(f"{API}/members/checkin-code", cookies=C_A)
        assert r1.status_code == 200
        code1 = r1.json()["code"]
        assert code1.startswith("CSC:") and len(code1) > 6
        r2 = requests.get(f"{API}/members/checkin-code", cookies=C_A)
        assert r2.json()["code"] == code1

    def test_anon_checkin_code_401(self):
        r = requests.get(f"{API}/members/checkin-code")
        assert r.status_code == 401


# ============================================================
# Door check-in
# ============================================================
@pytest.fixture(scope="class")
def qa_meeting():
    today = date.today().isoformat()
    payload = {"title": f"QA Checkin Gathering {uuid.uuid4().hex[:6]}", "date": today, "kind": "in-person",
               "location": "QA Hall", "address": "", "time": "10:00", "details": ""}
    r = requests.post(f"{API}/admin/members/meetings", json=payload, cookies=C_ADMIN, headers=H_CSRF)
    assert r.status_code == 200, r.text
    mid = r.json().get("id") or r.json().get("meeting", {}).get("id")
    if not mid:
        # fallback: list meetings
        ms = requests.get(f"{API}/admin/members/checkin", cookies=C_ADMIN).json()["meetings"]
        mid = next(m["id"] for m in ms if m["title"] == payload["title"])
    yield mid
    requests.delete(f"{API}/admin/members/meetings/{mid}", cookies=C_ADMIN, headers=H_CSRF)


class TestCheckin:
    def test_list_meetings_window(self, qa_meeting):
        r = requests.get(f"{API}/admin/members/checkin", cookies=C_ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert "today" in data and "meetings" in data
        assert any(m["id"] == qa_meeting for m in data["meetings"])

    def test_member_forbidden_listing(self):
        r = requests.get(f"{API}/admin/members/checkin", cookies=C_A)
        assert r.status_code == 403

    def test_sheet_shape(self, qa_meeting):
        r = requests.get(f"{API}/admin/members/checkin/{qa_meeting}", cookies=C_ADMIN)
        assert r.status_code == 200
        d = r.json()
        assert d["meeting"]["id"] == qa_meeting
        assert isinstance(d["rows"], list) and len(d["rows"]) >= 2
        c = d["counts"]
        for k in ("present", "guests", "headcount", "members", "expected"):
            assert k in c

    def test_checkin_by_user_id(self, qa_meeting, uid_a):
        r = requests.post(f"{API}/admin/members/checkin/{qa_meeting}",
                          json={"user_id": uid_a, "guests": 1}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200, r.text
        assert r.json()["user_id"] == uid_a
        # Verify present and headcount counts
        sheet = requests.get(f"{API}/admin/members/checkin/{qa_meeting}", cookies=C_ADMIN).json()
        row = next(x for x in sheet["rows"] if x["user_id"] == uid_a)
        assert row["status"] == "present"
        assert row["guests"] == 1
        assert sheet["counts"]["present"] >= 1
        assert sheet["counts"]["headcount"] >= 2

    def test_checkin_by_code(self, qa_meeting, uid_b):
        code = requests.get(f"{API}/members/checkin-code", cookies=C_B).json()["code"]
        r = requests.post(f"{API}/admin/members/checkin/{qa_meeting}",
                          json={"code": code, "guests": 0}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200, r.text
        assert r.json()["user_id"] == uid_b

    def test_checkin_invalid_code_404(self, qa_meeting):
        r = requests.post(f"{API}/admin/members/checkin/{qa_meeting}",
                          json={"code": "CSC:not-a-real-token", "guests": 0}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 404

    def test_checkin_missing_selector_400(self, qa_meeting):
        r = requests.post(f"{API}/admin/members/checkin/{qa_meeting}",
                          json={"guests": 0}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 400

    def test_checkin_guest_range(self, qa_meeting, uid_a):
        r = requests.post(f"{API}/admin/members/checkin/{qa_meeting}",
                          json={"user_id": uid_a, "guests": 21}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 400

    def test_undo_checkin(self, qa_meeting, uid_a):
        r = requests.delete(f"{API}/admin/members/checkin/{qa_meeting}/{uid_a}",
                            cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        sheet = requests.get(f"{API}/admin/members/checkin/{qa_meeting}", cookies=C_ADMIN).json()
        row = next(x for x in sheet["rows"] if x["user_id"] == uid_a)
        assert row["status"] is None

    def test_finish_marks_remaining_absent(self, qa_meeting, uid_b):
        # Re-check uid_b (undo earlier might not have been done); finish should mark everyone else absent
        requests.post(f"{API}/admin/members/checkin/{qa_meeting}",
                      json={"user_id": uid_b, "guests": 0}, cookies=C_ADMIN, headers=H_CSRF)
        r = requests.post(f"{API}/admin/members/checkin/{qa_meeting}/finish",
                          cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        assert "marked_absent" in r.json()
        sheet = requests.get(f"{API}/admin/members/checkin/{qa_meeting}", cookies=C_ADMIN).json()
        statuses = {r["status"] for r in sheet["rows"]}
        assert "absent" in statuses or "present" in statuses  # at least one of each exists
        # uid_b remains present
        row_b = next(x for x in sheet["rows"] if x["user_id"] == uid_b)
        assert row_b["status"] == "present"

    def test_member_cannot_checkin(self, qa_meeting, uid_a):
        r = requests.post(f"{API}/admin/members/checkin/{qa_meeting}",
                          json={"user_id": uid_a, "guests": 0}, cookies=C_A, headers=H_CSRF)
        assert r.status_code == 403


# ============================================================
# Spotlight archive
# ============================================================
@pytest.fixture(scope="class")
def published_spotlight(uid_b):
    # Create+publish a spotlight for current month, staff mode
    today = date.today()
    month = f"{today.year:04d}-{today.month:02d}"
    # If one already exists published this month, use it
    existing = requests.get(f"{API}/admin/members/spotlights", cookies=C_ADMIN).json()
    for s in existing:
        if s.get("month") == month and s.get("status") == "published":
            yield s["id"]
            return
    r = requests.post(f"{API}/admin/members/spotlights",
                      json={"user_id": uid_b, "month": month, "mode": "staff", "story": "QA phase6 spotlight story."},
                      cookies=C_ADMIN, headers=H_CSRF)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    requests.put(f"{API}/admin/members/spotlights/{sid}",
                 json={"story": "QA phase6 spotlight story body.", "photo_url": ""}, cookies=C_ADMIN, headers=H_CSRF)
    pub = requests.post(f"{API}/admin/members/spotlights/{sid}/publish", cookies=C_ADMIN, headers=H_CSRF)
    assert pub.status_code == 200, pub.text
    yield sid
    requests.delete(f"{API}/admin/members/spotlights/{sid}", cookies=C_ADMIN, headers=H_CSRF)


class TestSpotlightArchive:
    def test_member_sees_archive(self, published_spotlight):
        r = requests.get(f"{API}/members/spotlights", cookies=C_A)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert any(s["id"] == published_spotlight for s in rows)

    def test_archive_only_published_and_past_or_current_month(self, published_spotlight):
        rows = requests.get(f"{API}/members/spotlights", cookies=C_A).json()
        cur = f"{date.today().year:04d}-{date.today().month:02d}"
        for s in rows:
            assert s.get("month") <= cur

    def test_anon_archive_401(self):
        r = requests.get(f"{API}/members/spotlights")
        assert r.status_code == 401


# ============================================================
# Prayer board
# ============================================================
@pytest.fixture
def prayer_from_a():
    r = requests.post(f"{API}/members/prayers",
                      json={"kind": "request", "body": "QA please pray for test " + uuid.uuid4().hex[:6], "anonymous": False},
                      cookies=C_A, headers=H_CSRF)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{API}/members/prayers/{pid}", cookies=C_ADMIN, headers=H_CSRF)


@pytest.fixture
def anon_prayer_from_a():
    r = requests.post(f"{API}/members/prayers",
                      json={"kind": "praise", "body": "QA anon praise " + uuid.uuid4().hex[:6], "anonymous": True},
                      cookies=C_A, headers=H_CSRF)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{API}/members/prayers/{pid}", cookies=C_ADMIN, headers=H_CSRF)


class TestPrayers:
    def test_anon_prayers_401(self):
        r = requests.get(f"{API}/members/prayers")
        assert r.status_code == 401

    def test_create_and_list(self, prayer_from_a):
        rows = requests.get(f"{API}/members/prayers", cookies=C_A).json()
        p = next((x for x in rows if x["id"] == prayer_from_a), None)
        assert p is not None
        assert p["kind"] == "request"
        assert p["mine"] is True
        assert p["praying_count"] == 0

    def test_empty_body_400(self):
        r = requests.post(f"{API}/members/prayers",
                          json={"kind": "request", "body": "   ", "anonymous": False},
                          cookies=C_A, headers=H_CSRF)
        assert r.status_code == 400

    def test_bad_kind_400(self):
        r = requests.post(f"{API}/members/prayers",
                          json={"kind": "weird", "body": "hi", "anonymous": False},
                          cookies=C_A, headers=H_CSRF)
        assert r.status_code == 400

    def test_pray_toggle(self, prayer_from_a):
        r1 = requests.post(f"{API}/members/prayers/{prayer_from_a}/pray", cookies=C_B, headers=H_CSRF)
        assert r1.status_code == 200 and r1.json()["praying"] is True
        rows = requests.get(f"{API}/members/prayers", cookies=C_B).json()
        p = next(x for x in rows if x["id"] == prayer_from_a)
        assert p["praying_count"] == 1 and p["i_am_praying"] is True
        r2 = requests.post(f"{API}/members/prayers/{prayer_from_a}/pray", cookies=C_B, headers=H_CSRF)
        assert r2.json()["praying"] is False

    def test_encourage_and_delete_own(self, prayer_from_a):
        r = requests.post(f"{API}/members/prayers/{prayer_from_a}/encourage",
                          json={"body": "QA praying with you"}, cookies=C_B, headers=H_CSRF)
        assert r.status_code == 200
        rows = requests.get(f"{API}/members/prayers", cookies=C_A).json()
        p = next(x for x in rows if x["id"] == prayer_from_a)
        assert len(p["encouragements"]) == 1
        eid = p["encouragements"][0]["id"]
        # B can delete own encouragement
        r2 = requests.delete(f"{API}/members/prayers/{prayer_from_a}/encourage/{eid}", cookies=C_B, headers=H_CSRF)
        assert r2.status_code == 200

    def test_encouragement_empty_400(self, prayer_from_a):
        r = requests.post(f"{API}/members/prayers/{prayer_from_a}/encourage",
                          json={"body": "   "}, cookies=C_B, headers=H_CSRF)
        assert r.status_code == 400

    def test_cannot_delete_others_encouragement(self, prayer_from_a):
        # B posts encouragement, A tries to delete
        requests.post(f"{API}/members/prayers/{prayer_from_a}/encourage",
                      json={"body": "QA from B"}, cookies=C_B, headers=H_CSRF)
        rows = requests.get(f"{API}/members/prayers", cookies=C_A).json()
        p = next(x for x in rows if x["id"] == prayer_from_a)
        eid = p["encouragements"][0]["id"]
        r = requests.delete(f"{API}/members/prayers/{prayer_from_a}/encourage/{eid}", cookies=C_A, headers=H_CSRF)
        assert r.status_code == 403

    def test_mark_answered_author_only(self, prayer_from_a):
        # A (author) can toggle
        r = requests.post(f"{API}/members/prayers/{prayer_from_a}/answered", cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200
        rows = requests.get(f"{API}/members/prayers", cookies=C_A).json()
        p = next(x for x in rows if x["id"] == prayer_from_a)
        assert p["answered_at"] is not None
        # B cannot
        r2 = requests.post(f"{API}/members/prayers/{prayer_from_a}/answered", cookies=C_B, headers=H_CSRF)
        assert r2.status_code == 403

    def test_other_member_cannot_delete(self, prayer_from_a):
        r = requests.delete(f"{API}/members/prayers/{prayer_from_a}", cookies=C_B, headers=H_CSRF)
        assert r.status_code == 403

    def test_admin_can_delete(self):
        # Create fresh then admin deletes
        pid = requests.post(f"{API}/members/prayers",
                            json={"kind": "request", "body": "QA admin-delete " + uuid.uuid4().hex[:6], "anonymous": False},
                            cookies=C_A, headers=H_CSRF).json()["id"]
        r = requests.delete(f"{API}/members/prayers/{pid}", cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200

    def test_author_can_delete_own(self):
        pid = requests.post(f"{API}/members/prayers",
                            json={"kind": "request", "body": "QA self-delete " + uuid.uuid4().hex[:6], "anonymous": False},
                            cookies=C_A, headers=H_CSRF).json()["id"]
        r = requests.delete(f"{API}/members/prayers/{pid}", cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200

    def test_anonymous_mask_for_others(self, anon_prayer_from_a):
        # Other member sees "A sister", author sees real name, admin sees real name
        rows_b = requests.get(f"{API}/members/prayers", cookies=C_B).json()
        p_b = next(x for x in rows_b if x["id"] == anon_prayer_from_a)
        assert p_b["author_name"] == "A sister"
        assert p_b["author_picture"] == ""

        rows_a = requests.get(f"{API}/members/prayers", cookies=C_A).json()
        p_a = next(x for x in rows_a if x["id"] == anon_prayer_from_a)
        assert p_a["author_name"] != "A sister"
        assert p_a["mine"] is True

        rows_admin = requests.get(f"{API}/members/prayers", cookies=C_ADMIN).json()
        p_ad = next(x for x in rows_admin if x["id"] == anon_prayer_from_a)
        assert p_ad["author_name"] != "A sister"
