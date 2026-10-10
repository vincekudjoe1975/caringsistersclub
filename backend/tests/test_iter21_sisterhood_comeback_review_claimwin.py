"""Iter-21 backend tests: Sisterhood badges page, Comeback tracking, Review feature requests, Claim window."""
import os
import time
import uuid
import secrets
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
DB = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

ADMIN_COOKIES = {"session_token": "qa_tok_123"}
ADMIN_HEADERS = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}
PID = f"qa21-{uuid.uuid4().hex[:8]}"


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    # Clean QA data
    DB.volunteer_milestones.delete_many({"email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.participant_badges.delete_many({"email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.sisterhood_links.delete_many({"email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.volunteer_hours.delete_many({"email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.session_feedback.delete_many({"email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.noshow_emails.delete_many({"email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.story_submissions.delete_many({"email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.submissions.delete_many({"data.email": {"$regex": "^qa\\.(sis|back|rev|iter21)"}})
    DB.programs.delete_many({"id": {"$regex": f"^qa21-"}})


# ---------- Sisterhood badges ----------
class TestSisterhood:
    EMAIL = "qa.sis@example.com"

    def test_sis_link_idempotent(self):
        import sys
        sys.path.insert(0, '/app/backend')
        import server

        async def _two():
            a = await server._sis_link(self.EMAIL)
            b = await server._sis_link(self.EMAIL)
            return a, b
        a, b = asyncio.run(_two())
        assert a == b, f"_sis_link not idempotent: {a} vs {b}"
        assert "/sisterhood/" in a

    def test_sisterhood_endpoints(self):
        # Seed
        link = DB.sisterhood_links.find_one({"email": self.EMAIL})
        token = link["token"]
        DB.volunteer_milestones.delete_many({"email": self.EMAIL})
        DB.participant_badges.delete_many({"email": self.EMAIL})
        DB.volunteer_milestones.insert_one({
            "email": self.EMAIL, "scope": "all", "threshold": 10,
            "label": "10 Hours All-Time", "awarded_at": _iso(_now() - timedelta(days=5)),
            "share_token": secrets.token_urlsafe(10),
        })
        DB.participant_badges.insert_one({
            "email": self.EMAIL, "kind": "faithful", "label": "Faithful Sister",
            "seal": "3x", "name": "QA Sis Tester", "share_token": secrets.token_urlsafe(10),
            "awarded_at": _iso(_now() - timedelta(days=2)),
        })
        # GET
        r = requests.get(f"{BASE}/api/sisterhood/{token}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["badges"]) == 2
        # _short_name uses first + last word initial. "QA Sis Tester" -> "QA T."
        assert d["name"] in ("QA S.", "QA T."), f"Unexpected name {d['name']}"

        # Bad token
        assert requests.get(f"{BASE}/api/sisterhood/doesnotexist123").status_code == 404

        # card.png
        r2 = requests.get(f"{BASE}/api/share/sisterhood/{token}/card.png")
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/png")
        assert len(r2.content) > 1000

        # OG html
        r3 = requests.get(f"{BASE}/api/share/sisterhood/{token}")
        assert r3.status_code == 200
        assert "og:image" in r3.text


# ---------- Certificate request ----------
class TestCertRequest:
    def test_cert_request_badges_only(self):
        email = "qa.sis@example.com"  # has participant badge only (<50h)
        # Rate limited 3/600s so just once
        r = requests.post(f"{BASE}/api/certificates/request", json={"email": email})
        assert r.status_code == 200, r.text
        msg = r.json().get("message", "")
        assert "badge" in msg.lower(), msg


# ---------- Comeback ----------
class TestComeback:
    EMAIL = "qa.back@example.com"
    ROOT_ID = f"qa21-root-{uuid.uuid4().hex[:6]}"
    CLONE_ID = f"qa21-clone-{uuid.uuid4().hex[:6]}"
    CLONE_SLUG = f"qa21-clone-{uuid.uuid4().hex[:6]}"

    def test_comeback_flow(self):
        # Seed root program
        now = _now()
        DB.programs.insert_one({
            "id": self.ROOT_ID, "slug": f"qa21-root-{self.ROOT_ID[-6:]}",
            "title": "QA21 Root Program", "published": True, "capacity": 0,
            "waitlist_mode": "claim", "offer_hours": 48, "created_at": _iso(now),
        })
        DB.programs.insert_one({
            "id": self.CLONE_ID, "slug": self.CLONE_SLUG, "cloned_from": self.ROOT_ID,
            "title": "QA21 Clone Program", "published": True, "capacity": 0,
            "waitlist_mode": "claim", "offer_hours": 48, "created_at": _iso(now),
        })

        # Noshow email (recent) for root program
        noshow_id = str(uuid.uuid4())
        DB.noshow_emails.insert_one({
            "id": noshow_id, "submission_id": "x", "program_id": self.ROOT_ID,
            "email": self.EMAIL, "at": _iso(now - timedelta(days=3)),
        })

        # First signup to clone -> came_back true
        r = requests.post(f"{BASE}/api/programs/{self.CLONE_SLUG}/signup", json={
            "name": "QA Back Tester", "email": self.EMAIL, "phone": "", "message": ""
        })
        assert r.status_code == 200, r.text

        sub = DB.submissions.find_one({"data.email": self.EMAIL, "program_id": self.CLONE_ID}, sort=[("created_at", -1)])
        assert sub is not None
        assert sub.get("came_back") is True, f"Expected came_back=True, got {sub.get('came_back')}"

        ns = DB.noshow_emails.find_one({"id": noshow_id})
        assert ns.get("comeback_at") is not None

        # Second signup should not re-count (noshow already has comeback_at)
        time.sleep(13)  # rate limit 5/60s per IP for signup
        r2 = requests.post(f"{BASE}/api/programs/{self.CLONE_SLUG}/signup", json={
            "name": "QA Back Tester 2", "email": self.EMAIL, "phone": "", "message": ""
        })
        # may be 200 or 429; if 200 came_back should be False/absent (noshow was already consumed)
        if r2.status_code == 200:
            sub2 = DB.submissions.find_one({"data.email": self.EMAIL, "program_id": self.CLONE_ID}, sort=[("created_at", -1)])
            assert sub2["id"] != sub["id"]
            assert not sub2.get("came_back", False)

        # Reports endpoint
        r3 = requests.get(f"{BASE}/api/admin/reports/comebacks", cookies=ADMIN_COOKIES)
        assert r3.status_code == 200, r3.text
        rep = r3.json()
        row = next((it for it in rep["items"] if it["program_id"] == self.ROOT_ID), None)
        assert row is not None, rep
        assert row["sent"] == 1
        assert row["comebacks"] == 1
        assert row["rate"] == 100

    def test_comeback_old_noshow_no_count(self):
        email = "qa.back2@example.com"
        # Seed old noshow (70 days ago)
        root_id = f"qa21-root2-{uuid.uuid4().hex[:6]}"
        clone_slug = f"qa21-clone2-{uuid.uuid4().hex[:6]}"
        now = _now()
        DB.programs.insert_one({"id": root_id, "slug": f"qa21-root2-{root_id[-6:]}", "title": "QA21 R2", "published": True, "capacity": 0, "offer_hours": 48})
        DB.programs.insert_one({"id": f"qa21-clone2x-{uuid.uuid4().hex[:6]}", "slug": clone_slug, "cloned_from": root_id, "title": "QA21 C2", "published": True, "capacity": 0, "offer_hours": 48})
        DB.noshow_emails.insert_one({"id": str(uuid.uuid4()), "submission_id": "x", "program_id": root_id, "email": email, "at": _iso(now - timedelta(days=70))})
        time.sleep(13)
        r = requests.post(f"{BASE}/api/programs/{clone_slug}/signup", json={"name": "QA Back2", "email": email, "phone": "", "message": ""})
        assert r.status_code == 200, r.text
        sub = DB.submissions.find_one({"data.email": email, "data.program_slug": clone_slug}, sort=[("created_at", -1)])
        assert not sub.get("came_back", False)
        # Cleanup
        DB.submissions.delete_many({"data.email": email})
        DB.noshow_emails.delete_many({"email": email})
        DB.programs.delete_many({"$or": [{"id": root_id}, {"slug": clone_slug}]})


# ---------- Review feature request ----------
class TestReviewFeature:
    EMAIL = "qa.rev@example.com"
    TOKEN = secrets.token_urlsafe(16)
    FID = str(uuid.uuid4())
    PROG_ID = f"qa21-rev-{uuid.uuid4().hex[:6]}"

    def test_feedback_review_request(self):
        # Seed program + feedback
        DB.programs.insert_one({"id": self.PROG_ID, "slug": f"qa21-rev-{self.PROG_ID[-6:]}", "title": "QA21 Rev Program", "published": True})
        DB.session_feedback.delete_many({"token": self.TOKEN})
        DB.session_feedback.insert_one({
            "id": self.FID, "token": self.TOKEN, "program_id": self.PROG_ID,
            "email": self.EMAIL, "name": "QA Rev Tester", "sent_at": _iso(_now()),
        })

        # POST feedback 5 stars + comment
        r = requests.post(f"{BASE}/api/feedback", json={
            "token": self.TOKEN, "rating": 5, "recommend": True,
            "comment": "Wonderful session, loved it!"
        })
        assert r.status_code == 200, r.text
        time.sleep(0.5)
        f = DB.session_feedback.find_one({"token": self.TOKEN})
        assert f.get("review_requested") is True

        # Repeat - should not re-request
        time.sleep(6)
        r2 = requests.post(f"{BASE}/api/feedback", json={
            "token": self.TOKEN, "rating": 5, "recommend": True,
            "comment": "Wonderful session, loved it!"
        })
        assert r2.status_code == 200
        f2 = DB.session_feedback.find_one({"token": self.TOKEN})
        orig_at = f.get("review_requested_at")
        assert f2.get("review_requested_at") == orig_at, "review_requested_at should not change on repeat"

    def test_feature_consent_get(self):
        r = requests.get(f"{BASE}/api/feature-consent?token={self.TOKEN}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["quote"] == "Wonderful session, loved it!"
        assert d["consented"] is False

    def test_feature_consent_post(self):
        time.sleep(6)
        r = requests.post(f"{BASE}/api/feature-consent", json={"token": self.TOKEN, "photo_url": ""})
        assert r.status_code == 200, r.text
        story = DB.story_submissions.find_one({"source": "feedback", "email": self.EMAIL})
        assert story is not None
        assert story["status"] == "pending"
        assert story["quote"] == "Wonderful session, loved it!"

        # Repeat - no duplicate
        time.sleep(6)
        r2 = requests.post(f"{BASE}/api/feature-consent", json={"token": self.TOKEN, "photo_url": ""})
        assert r2.status_code == 200
        cnt = DB.story_submissions.count_documents({"source": "feedback", "email": self.EMAIL})
        assert cnt == 1, f"Expected 1 story, got {cnt}"

    def test_feature_consent_bad_photo(self):
        time.sleep(6)
        r = requests.post(f"{BASE}/api/feature-consent", json={"token": self.TOKEN, "photo_url": "https://evil"})
        assert r.status_code == 400

    def test_feature_consent_rating4_not_eligible(self):
        tok = secrets.token_urlsafe(16)
        email = "qa.rev2@example.com"
        DB.session_feedback.insert_one({
            "id": str(uuid.uuid4()), "token": tok, "program_id": self.PROG_ID,
            "email": email, "name": "QA Rev4", "sent_at": _iso(_now()),
            "rating": 4, "comment": "Pretty good overall", "submitted_at": _iso(_now()),
        })
        r = requests.get(f"{BASE}/api/feature-consent?token={tok}")
        assert r.status_code == 404
        DB.session_feedback.delete_many({"token": tok})


# ---------- Claim window ----------
class TestClaimWindow:
    PID = f"qa21-cw-{uuid.uuid4().hex[:6]}"
    SLUG = f"qa21-cw-{uuid.uuid4().hex[:6]}"

    def _get_prog(self):
        return DB.programs.find_one({"id": self.PID}, {"_id": 0})

    def test_offer_hours_persists(self):
        DB.programs.delete_many({"id": self.PID})
        DB.programs.insert_one({"id": self.PID, "slug": self.SLUG, "title": "QA21 CW", "published": True, "capacity": 1, "offer_hours": 48, "created_at": _iso(_now())})
        # PUT with offer_hours=24
        body = {"title": "QA21 CW", "category": "", "image_url": "", "summary": "", "body": "", "goals": [], "impact": [],
                "cta_text": "Get Involved", "cta_link": "/volunteer", "published": True, "gallery": [], "testimonials": [],
                "home_testimonial_ids": [], "capacity": 1, "waitlist_mode": "claim", "offer_hours": 24,
                "start_date": "", "end_date": "", "schedule": ""}
        r = requests.put(f"{BASE}/api/admin/programs/{self.PID}", json=body, cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
        assert r.status_code == 200, r.text
        assert self._get_prog()["offer_hours"] == 24

        # invalid 30 -> normalized to 48
        body["offer_hours"] = 30
        r2 = requests.put(f"{BASE}/api/admin/programs/{self.PID}", json=body, cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
        assert r2.status_code == 200
        assert self._get_prog()["offer_hours"] == 48

    def test_claim_window_offer_expires(self):
        # Set offer_hours=24
        DB.programs.update_one({"id": self.PID}, {"$set": {"offer_hours": 24, "capacity": 1}})
        time.sleep(13)
        # Fill: first signup fills seat
        r1 = requests.post(f"{BASE}/api/programs/{self.SLUG}/signup", json={"name": "QA Fill", "email": "qa.iter21.a@example.com", "phone": "", "message": ""})
        assert r1.status_code == 200, r1.text
        # Waitlist signup
        time.sleep(13)
        r2 = requests.post(f"{BASE}/api/programs/{self.SLUG}/signup", json={"name": "QA WL", "email": "qa.iter21.b@example.com", "phone": "", "message": ""})
        assert r2.status_code == 200, r2.text
        assert r2.json().get("waitlist") is True

        wl_sub = DB.submissions.find_one({"data.email": "qa.iter21.b@example.com", "data.program_slug": self.SLUG})
        assert wl_sub
        # Admin triggers an offer directly (equivalent to releasing a seat)
        r3 = requests.post(f"{BASE}/api/admin/waitlist/{wl_sub['id']}/offer", cookies=ADMIN_COOKIES, headers=ADMIN_HEADERS)
        assert r3.status_code == 200, r3.text
        updated = DB.submissions.find_one({"id": wl_sub["id"]})
        sent = datetime.fromisoformat(updated["offer_sent_at"])
        exp = datetime.fromisoformat(updated["offer_expires"])
        delta_h = (exp - sent).total_seconds() / 3600
        assert 23.9 <= delta_h <= 24.1, f"Expected ~24h window, got {delta_h}h"

    def test_waitlist_speed_tip(self):
        # Seed 5 claimed offers on this program with offer_hours=48 and claimed_at 2h after sent
        DB.programs.update_one({"id": self.PID}, {"$set": {"offer_hours": 48}})
        DB.submissions.delete_many({"program_id": self.PID, "data.email": {"$regex": "^qa\\.iter21\\.wst"}})
        now = _now()
        for i in range(5):
            sent = now - timedelta(hours=5)
            claimed = sent + timedelta(hours=2)
            DB.submissions.insert_one({
                "id": str(uuid.uuid4()), "type": "program_signup", "program_id": self.PID,
                "waitlist": True, "created_at": _iso(sent), "read": True,
                "data": {"program": "QA21 CW", "program_slug": self.SLUG, "name": f"QA WST{i}", "email": f"qa.iter21.wst{i}@example.com"},
                "offer_sent_at": _iso(sent), "offer_expires": _iso(sent + timedelta(hours=48)),
                "offer_status": "claimed", "claimed_at": _iso(claimed),
            })
        r = requests.get(f"{BASE}/api/admin/reports/waitlist-speed", cookies=ADMIN_COOKIES)
        assert r.status_code == 200, r.text
        row = next((x for x in r.json()["items"] if x["program_id"] == self.PID), None)
        assert row is not None
        assert "24-hour" in row["tip"], f"Expected 24-hour tip, got '{row['tip']}'"

        # Change window to 24 -> no tip
        DB.programs.update_one({"id": self.PID}, {"$set": {"offer_hours": 24}})
        r2 = requests.get(f"{BASE}/api/admin/reports/waitlist-speed", cookies=ADMIN_COOKIES)
        row2 = next((x for x in r2.json()["items"] if x["program_id"] == self.PID), None)
        assert row2 is not None
        assert row2["tip"] == "", f"Expected no tip, got '{row2['tip']}'"
