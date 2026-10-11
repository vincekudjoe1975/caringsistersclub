"""Backend tests for iteration 31: Leadership manager, Gallery manager,
Program sessions, and session-aware signup. Cleans up all QA data at teardown.
"""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
COOKIES = {"session_token": "qa_tok_123"}
ADMIN_HEADERS = {"X-Requested-With": "XMLHttpRequest"}

# A real published program slug we can attach sessions to.
TEST_PROGRAM_SLUG = "business-elevation-lab"


@pytest.fixture(scope="module")
def program_id():
    r = requests.get(f"{API}/programs/{TEST_PROGRAM_SLUG}")
    assert r.status_code == 200, r.text
    pid = r.json().get("id")
    assert pid
    return pid


@pytest.fixture(scope="module", autouse=True)
def cleanup(program_id):
    yield
    # Delete QA leaders
    try:
        for lead in requests.get(f"{API}/admin/leaders", cookies=COOKIES).json().get("items", []):
            if lead.get("name", "").startswith("QA"):
                requests.delete(f"{API}/admin/leaders/{lead['id']}", cookies=COOKIES, headers=ADMIN_HEADERS)
    except Exception as e:
        print("leader cleanup error", e)
    # Delete QA sessions (location QA Hall)
    try:
        for s in requests.get(f"{API}/admin/programs/{program_id}/sessions", cookies=COOKIES).json().get("items", []):
            if "QA" in (s.get("location") or ""):
                requests.delete(f"{API}/admin/sessions/{s['id']}", cookies=COOKIES, headers=ADMIN_HEADERS)
    except Exception as e:
        print("session cleanup error", e)


# =============== Leaders ===============
class TestLeaders:
    created = {}

    def test_public_leaders_shape(self):
        r = requests.get(f"{API}/leaders")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_admin_requires_auth(self):
        r = requests.get(f"{API}/admin/leaders")
        assert r.status_code in (401, 403)

    def test_create_leader_board(self):
        payload = {"name": "QA Board Member", "role": "Chair", "group": "board",
                   "intro": "Short intro", "bio": "Long\nbio text", "linkedin": "linkedin.com/in/qa",
                   "email": "qa.board@example.com", "visible": True}
        r = requests.post(f"{API}/admin/leaders", json=payload, cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == "QA Board Member"
        assert d["linkedin"].startswith("https://"), f"linkedin not normalized: {d['linkedin']}"
        TestLeaders.created["board"] = d["id"]

    def test_create_leader_executive(self):
        payload = {"name": "QA Executive Member", "role": "Director", "group": "executive",
                   "intro": "Exec intro", "bio": "Exec bio paragraph.", "visible": True}
        r = requests.post(f"{API}/admin/leaders", json=payload, cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200, r.text
        TestLeaders.created["exec"] = r.json()["id"]

    def test_create_leader_invalid_email(self):
        r = requests.post(f"{API}/admin/leaders",
                          json={"name": "QA Bad Email", "group": "board", "email": "not-an-email"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_create_leader_invalid_group(self):
        r = requests.post(f"{API}/admin/leaders",
                          json={"name": "QA Bad Group", "group": "other"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_create_leader_missing_name(self):
        r = requests.post(f"{API}/admin/leaders",
                          json={"name": "   ", "group": "board"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_create_leader_invalid_photo(self):
        r = requests.post(f"{API}/admin/leaders",
                          json={"name": "QA Bad Photo", "group": "board", "photo_url": "http://evil.com/x.png"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_update_and_hide(self):
        lid = TestLeaders.created["board"]
        r = requests.put(f"{API}/admin/leaders/{lid}",
                         json={"name": "QA Board Member", "role": "President", "group": "board",
                               "intro": "Updated intro", "bio": "Updated bio", "visible": False},
                         cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "President"
        # public should hide it
        public = requests.get(f"{API}/leaders").json().get("items", [])
        assert all(x["id"] != lid for x in public)

    def test_public_lists_visible_executive(self):
        public = requests.get(f"{API}/leaders").json().get("items", [])
        assert any(x["id"] == TestLeaders.created["exec"] for x in public)

    def test_reorder(self):
        ids = [TestLeaders.created["exec"], TestLeaders.created["board"]]
        r = requests.post(f"{API}/admin/leaders/reorder", json={"ids": ids}, cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200

    def test_csrf_blocks_without_header(self):
        r = requests.post(f"{API}/admin/leaders", json={"name": "QA Noheader", "group": "board"}, cookies=COOKIES)
        assert r.status_code == 403


# =============== Gallery ===============
class TestGallery:
    uploaded = []

    def test_admin_requires_auth(self):
        assert requests.get(f"{API}/admin/gallery").status_code in (401, 403)

    def test_upload_and_edit(self):
        # Upload via /api/media (existing media uploader) with category=gallery
        import base64
        # 1x1 transparent PNG
        png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")

        def _files():
            return {"file": ("qa.png", io.BytesIO(png_bytes), "image/png")}

        r = requests.post(f"{API}/admin/media", files=_files(), data={"category": "gallery", "title": "QA Photo"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        if r.status_code == 404:
            r = requests.post(f"{API}/media", files=_files(), data={"category": "gallery", "title": "QA Photo"},
                              cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code in (200, 201), f"Media upload failed {r.status_code}: {r.text[:200]}"
        mid = r.json().get("id") or r.json().get("media_id")
        assert mid
        TestGallery.uploaded.append(mid)

        # Edit
        r = requests.put(f"{API}/admin/gallery/{mid}", json={
            "title": "QA Gallery Title", "description": "QA desc",
            "tag_type": "program", "tag_label": "QA Prog", "tag_ref": "qa-prog", "hidden": False},
            cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200, r.text

        # Verify in admin list
        items = requests.get(f"{API}/admin/gallery", cookies=COOKIES).json().get("items", [])
        found = next((x for x in items if x["id"] == mid), None)
        assert found and found["title"] == "QA Gallery Title"
        assert found["tag_type"] == "program"

    def test_hide_excludes_from_public(self):
        if not TestGallery.uploaded:
            pytest.skip("no upload")
        mid = TestGallery.uploaded[0]
        requests.put(f"{API}/admin/gallery/{mid}", json={
            "title": "QA Gallery Title", "description": "QA desc",
            "tag_type": "program", "tag_label": "QA Prog", "tag_ref": "qa-prog", "hidden": True},
            cookies=COOKIES, headers=ADMIN_HEADERS)
        public = requests.get(f"{API}/media?category=gallery").json()
        items = public.get("items") if isinstance(public, dict) else public
        assert all(x.get("id") != mid for x in (items or []))

    def test_invalid_tag_type(self):
        if not TestGallery.uploaded:
            pytest.skip("no upload")
        mid = TestGallery.uploaded[0]
        r = requests.put(f"{API}/admin/gallery/{mid}", json={"tag_type": "bogus"},
                         cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_reorder(self):
        if not TestGallery.uploaded:
            pytest.skip("no upload")
        r = requests.post(f"{API}/admin/gallery/reorder",
                          json={"ids": TestGallery.uploaded},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200

    def test_cleanup_delete(self):
        # Soft delete via media endpoint if available
        for mid in TestGallery.uploaded:
            for ep in (f"{API}/admin/media/{mid}", f"{API}/media/{mid}"):
                r = requests.delete(ep, cookies=COOKIES, headers=ADMIN_HEADERS)
                if r.status_code in (200, 204):
                    break


# =============== Sessions ===============
class TestSessions:
    sid = None

    def test_date_validation(self, program_id):
        r = requests.post(f"{API}/admin/programs/{program_id}/sessions",
                          json={"date": "2026/01/30", "location": "QA Hall"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_time_validation(self, program_id):
        r = requests.post(f"{API}/admin/programs/{program_id}/sessions",
                          json={"date": "2026-12-01", "start_time": "9:00", "location": "QA Hall"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_end_after_start(self, program_id):
        r = requests.post(f"{API}/admin/programs/{program_id}/sessions",
                          json={"date": "2026-12-01", "start_time": "10:00", "end_time": "09:00", "location": "QA Hall"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_create_session(self, program_id):
        r = requests.post(f"{API}/admin/programs/{program_id}/sessions",
                          json={"date": "2026-12-10", "start_time": "10:00", "end_time": "12:00",
                                "location": "QA Hall", "seats": 2, "notes": "QA session"},
                          cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["seats_left"] == 2
        TestSessions.sid = d["id"]

    def test_program_sessions_include(self, program_id):
        r = requests.get(f"{API}/programs/{TEST_PROGRAM_SLUG}")
        assert r.status_code == 200
        data = r.json()
        sessions = data.get("sessions", [])
        assert any(s["id"] == TestSessions.sid for s in sessions)
        s = next(s for s in sessions if s["id"] == TestSessions.sid)
        assert "seats_left" in s

    def test_calendar(self):
        r = requests.get(f"{API}/sessions/calendar")
        assert r.status_code == 200
        d = r.json()
        kinds = {e["kind"] for e in d.get("entries", [])}
        assert "session" in kinds
        assert "categories" in d
        assert any(e["id"] == TestSessions.sid for e in d["entries"] if e["kind"] == "session")

    def test_signup_requires_session(self):
        r = requests.post(f"{API}/programs/{TEST_PROGRAM_SLUG}/signup",
                          json={"name": "QA Person1", "email": "qa.person1@example.com",
                                "phone": "", "message": ""})
        assert r.status_code == 400
        assert "session" in r.text.lower()

    def test_signup_success_with_session(self):
        r = requests.post(f"{API}/programs/{TEST_PROGRAM_SLUG}/signup",
                          json={"name": "QA Person2", "email": "qa.person2@example.com",
                                "phone": "", "message": "", "session_id": TestSessions.sid})
        assert r.status_code == 200, r.text
        assert r.json().get("waitlist") in (False, None)

    def test_signup_fills_session(self):
        # second seat
        r = requests.post(f"{API}/programs/{TEST_PROGRAM_SLUG}/signup",
                          json={"name": "QA Person3", "email": "qa.person3@example.com",
                                "phone": "", "message": "", "session_id": TestSessions.sid})
        assert r.status_code == 200, r.text
        # third attempt -> full
        time.sleep(0.5)
        r = requests.post(f"{API}/programs/{TEST_PROGRAM_SLUG}/signup",
                          json={"name": "QA Person4", "email": "qa.person4@example.com",
                                "phone": "", "message": "", "session_id": TestSessions.sid})
        assert r.status_code == 400
        assert "full" in r.text.lower()

    def test_delete_blocked_with_signups(self):
        r = requests.delete(f"{API}/admin/sessions/{TestSessions.sid}",
                            cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 400

    def test_cleanup_signups_then_delete(self):
        # Cleanup QA submissions + delete session
        from pymongo import MongoClient
        mongo = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        c = MongoClient(mongo)[db_name]
        c.submissions.delete_many({"data.email": {"$regex": "^qa.person"}})
        c.session_launch_emails.delete_many({"email": {"$regex": "^qa.person"}})
        r = requests.delete(f"{API}/admin/sessions/{TestSessions.sid}",
                            cookies=COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200
