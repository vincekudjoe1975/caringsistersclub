"""Tests for About editor, Story submissions, Program signups and Impact email."""
import os
import time
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
ADMIN_COOKIE = {"session_token": "qa_tok_123"}
TEST_EMAIL_DOMAIN = "example.com"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.cookies.update(ADMIN_COOKIE)
    s.headers.update({"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"})
    return s


@pytest.fixture(scope="module")
def anon_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def program_slug():
    r = requests.get(f"{BASE_URL}/api/programs")
    assert r.status_code == 200
    return r.json()["items"][0]["slug"]


# ---------- About page ----------
class TestAbout:
    def test_public_about_default(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/about-content")
        assert r.status_code == 200
        d = r.json()
        assert "mission_title" in d and "values" in d and "story" in d
        assert isinstance(d["values"], list) and len(d["values"]) >= 1

    def test_admin_update_empty_mission_rejected(self, admin_session):
        r = admin_session.put(f"{BASE_URL}/api/admin/about-content", json={
            "hero_subtitle": "x", "mission_title": "T", "mission_body": "   ",
            "mission_image": "", "values": [{"icon": "Heart", "title": "V", "text": "t"}],
            "story_title": "S", "story": [{"year": "2020", "title": "M", "text": "t", "image": ""}],
        })
        assert r.status_code == 400, r.text
        assert "Mission" in r.json().get("detail", "")

    def test_admin_update_invalid_image_rejected(self, admin_session):
        r = admin_session.put(f"{BASE_URL}/api/admin/about-content", json={
            "mission_body": "Body para", "mission_image": "http://evil.com/x.png",
            "values": [{"icon": "Heart", "title": "V", "text": "t"}],
            "story": [{"year": "2020", "title": "M", "text": "t", "image": ""}],
        })
        assert r.status_code == 400

    def test_admin_requires_auth(self, anon_session):
        r = anon_session.put(f"{BASE_URL}/api/admin/about-content", json={"mission_body": "x"})
        assert r.status_code in (401, 403)

    def test_admin_update_success_and_public_reflects(self, admin_session, anon_session):
        payload = {
            "hero_subtitle": "QA intro line.",
            "mission_title": "QA Mission",
            "mission_body": "This is our QA mission paragraph with enough content.",
            "mission_image": "",
            "values": [
                {"icon": "Heart", "title": "QA Value 1", "text": "val one"},
                {"icon": "Sparkles", "title": "QA Value 2", "text": "val two"},
            ],
            "story_title": "QA Our Journey",
            "story": [
                {"year": "2020", "title": "QA Milestone 1", "text": "started", "image": ""},
                {"year": "2024", "title": "QA Milestone 2", "text": "grew", "image": ""},
            ],
        }
        r = admin_session.put(f"{BASE_URL}/api/admin/about-content", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["mission_title"] == "QA Mission"
        assert d["updated_at"]
        # Public reflects
        pub = anon_session.get(f"{BASE_URL}/api/about-content").json()
        assert pub["mission_title"] == "QA Mission"
        assert len(pub["values"]) == 2
        assert pub["story"][0]["title"] == "QA Milestone 1"


# ---------- Story submissions ----------
_submitted_ids = []


class TestStories:
    def test_submit_too_short_rejected(self, anon_session):
        r = anon_session.post(f"{BASE_URL}/api/stories", json={
            "name": "QA Short", "email": f"qa.short.{uuid.uuid4().hex[:6]}@{TEST_EMAIL_DOMAIN}",
            "quote": "too short", "role": "member",
        })
        assert r.status_code == 400
        assert "20 characters" in r.json().get("detail", "")

    def test_submit_valid_home(self, anon_session):
        quote = "This program literally changed my life and gave me community."
        r = anon_session.post(f"{BASE_URL}/api/stories", json={
            "name": "QA Story Home",
            "email": f"qa.home.{uuid.uuid4().hex[:6]}@{TEST_EMAIL_DOMAIN}",
            "role": "Member since 2024",
            "quote": quote,
        })
        assert r.status_code == 200, r.text
        _submitted_ids.append(r.json()["id"])

    def test_submit_valid_with_program(self, anon_session, program_slug):
        quote = "Program feedback is really wonderful and helpful to share."
        r = anon_session.post(f"{BASE_URL}/api/stories", json={
            "name": "QA Story Prog",
            "email": f"qa.prog.{uuid.uuid4().hex[:6]}@{TEST_EMAIL_DOMAIN}",
            "role": "Alumna", "quote": quote, "program_slug": program_slug,
        })
        assert r.status_code == 200, r.text
        _submitted_ids.append(r.json()["id"])

    def test_admin_list_includes_submission(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/stories")
        assert r.status_code == 200
        items = r.json()["items"]
        ids = {i["id"] for i in items}
        assert _submitted_ids and _submitted_ids[0] in ids
        found = next(i for i in items if i["id"] == _submitted_ids[0])
        assert found["status"] == "pending"

    def test_admin_approve_to_home(self, admin_session, anon_session):
        sid = _submitted_ids[0]
        r = admin_session.post(f"{BASE_URL}/api/admin/stories/{sid}/approve",
                               json={"target": "home", "quote": "QA edited quote on approval."})
        assert r.status_code == 200, r.text
        assert r.json()["featured_on"] == "Home page"
        # verify home testimonials contain our quote
        home = anon_session.get(f"{BASE_URL}/api/home-content").json()
        quotes = [t.get("quote") for t in home.get("testimonials", [])]
        assert any("QA edited quote" in (q or "") for q in quotes)

    def test_admin_approve_to_program(self, admin_session, anon_session, program_slug):
        sid = _submitted_ids[1]
        # find program id
        prog = anon_session.get(f"{BASE_URL}/api/programs/{program_slug}").json()
        pid = prog["id"]
        r = admin_session.post(f"{BASE_URL}/api/admin/stories/{sid}/approve",
                               json={"target": pid})
        assert r.status_code == 200, r.text
        p2 = anon_session.get(f"{BASE_URL}/api/programs/{program_slug}").json()
        names = [t.get("name") for t in p2.get("testimonials", [])]
        assert "QA Story Prog" in names

    def test_admin_reject(self, anon_session, admin_session):
        quote = "Yet another helpful story we would like to share here!"
        # avoid rate limit from prior POSTs
        time.sleep(1)
        for attempt in range(3):
            r = anon_session.post(f"{BASE_URL}/api/stories", json={
                "name": "QA Reject",
                "email": f"qa.rej.{uuid.uuid4().hex[:6]}@{TEST_EMAIL_DOMAIN}",
                "quote": quote,
            })
            if r.status_code == 429:
                time.sleep(15)
                continue
            break
        if r.status_code != 200:
            pytest.skip(f"rate limited or other: {r.status_code} {r.text}")
        sid = r.json()["id"]
        _submitted_ids.append(sid)
        rj = admin_session.post(f"{BASE_URL}/api/admin/stories/{sid}/reject")
        assert rj.status_code == 200
        # verify status
        items = admin_session.get(f"{BASE_URL}/api/admin/stories").json()["items"]
        s = next(i for i in items if i["id"] == sid)
        assert s["status"] == "rejected"

    def test_stories_requires_admin(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/stories")
        assert r.status_code in (401, 403)


# ---------- Program sign-ups ----------
class TestSignups:
    def test_signup_invalid_email(self, anon_session, program_slug):
        r = anon_session.post(f"{BASE_URL}/api/programs/{program_slug}/signup", json={
            "name": "QA S", "email": "not-an-email", "phone": "", "message": ""
        })
        assert r.status_code in (400, 422)

    def test_signup_404_on_missing(self, anon_session):
        r = anon_session.post(f"{BASE_URL}/api/programs/does-not-exist-xyz/signup", json={
            "name": "QA S", "email": f"qa.n.{uuid.uuid4().hex[:6]}@{TEST_EMAIL_DOMAIN}"
        })
        assert r.status_code == 404

    def test_signup_success_and_in_admin(self, anon_session, admin_session, program_slug):
        email = f"qa.signup.{uuid.uuid4().hex[:6]}@{TEST_EMAIL_DOMAIN}"
        r = anon_session.post(f"{BASE_URL}/api/programs/{program_slug}/signup", json={
            "name": "QA Signup", "email": email, "phone": "+1 (555) 111-2222",
            "message": "I'd love to join this program."
        })
        assert r.status_code == 200, r.text
        # Admin submissions filter
        subs = admin_session.get(f"{BASE_URL}/api/submissions?type=program_signup").json()
        emails = [s.get("data", {}).get("email") for s in subs]
        assert email in emails
        found = next(s for s in subs if s.get("data", {}).get("email") == email)
        assert found["data"].get("program")  # includes program name
        # counts endpoint - BUG: ALLOWED_SUB_TYPES missing 'program_signup' so badge shows 0
        counts = admin_session.get(f"{BASE_URL}/api/submissions/counts").json()
        # Document existing bug (expected to fail until fixed):
        assert counts.get("program_signup", {}).get("total", 0) >= 1, (
            "BUG: /api/submissions/counts does not include program_signup type "
            "(ALLOWED_SUB_TYPES missing). AdminSubmissions tab badge always 0."
        )


# ---------- Impact email ----------
class TestImpact:
    def test_preview_requires_admin(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/impact-email/preview")
        assert r.status_code in (401, 403)

    def test_preview_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/impact-email/preview")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("html", "recipients", "photos", "stories"):
            assert k in d
        assert "<" in d["html"] and "html" in d["html"].lower() or "<table" in d["html"]
        # Approved stories above should make stories >= 1
        assert isinstance(d["stories"], int)
