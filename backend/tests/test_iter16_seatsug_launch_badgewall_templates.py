"""Iter-16: seat suggestions, session launch emails (auto/manual), badge wall celebration, template insights."""
import os
import time
import math
import asyncio
import importlib
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
MONGO = MongoClient(os.environ['MONGO_URL'])
db = MONGO[os.environ['DB_NAME']]

COOKIES = {"session_token": "qa_tok_123"}
HEADERS = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}


def _iso(dt=None):
    return (dt or datetime.now(timezone.utc)).isoformat()


# --- fixtures ---------------------------------------------------------------

@pytest.fixture
def seed_program():
    pid = f"qa-prog-{uuid.uuid4().hex[:8]}"
    slug = f"qa-prog-{uuid.uuid4().hex[:8]}"
    db.programs.insert_one({
        "id": pid, "slug": slug, "title": "QA Seat Program", "description": "QA",
        "image_url": "https://example.com/x.jpg", "capacity": 0, "published": True,
        "waitlist_mode": "claim", "order": 9999, "created_at": _iso(),
    })
    yield pid, slug
    # cleanup
    db.programs.delete_many({"id": pid})
    db.programs.delete_many({"cloned_from": pid})
    db.program_snapshots.delete_many({"program_id": pid})
    db.submissions.delete_many({"program_id": pid})
    db.session_launch_emails.delete_many({"program_id": pid})
    # clean clones too
    for p in db.programs.find({"cloned_from": pid}, {"id": 1}):
        db.session_launch_emails.delete_many({"program_id": p["id"]})
        db.submissions.delete_many({"program_id": p["id"]})


# --- Seat suggestion -------------------------------------------------------

class TestSeatSuggestion:
    def test_two_seasons_with_fast_fill_boosts_20pct(self, seed_program):
        pid, _ = seed_program
        now = _iso()
        db.program_snapshots.insert_many([
            {"program_id": pid, "kind": "season", "label": "QA S1",
             "capacity": 10, "taken": 10, "waitlist": 4, "days_to_fill": 10,
             "season_started_at": now, "season_ended_at": now, "created_at": now},
            {"program_id": pid, "kind": "season", "label": "QA S2",
             "capacity": 10, "taken": 8, "waitlist": 2, "days_to_fill": None,
             "season_started_at": now, "season_ended_at": now, "created_at": now},
        ])
        r = requests.get(f"{BASE}/api/admin/programs/{pid}/seat-suggestion",
                         cookies=COOKIES, headers=HEADERS, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        # avg taken=9, avg waitlist=3; fast fill -> *1.2 -> 14.4 -> ceil 15
        assert body["suggested"] == 15, body
        assert "+20%" in body["why"]

    def test_slow_season_only_no_boost(self, seed_program):
        pid, _ = seed_program
        now = _iso()
        db.program_snapshots.insert_one({
            "program_id": pid, "kind": "season", "label": "QA Slow",
            "capacity": 10, "taken": 8, "waitlist": 2, "days_to_fill": None,
            "season_started_at": now, "season_ended_at": now, "created_at": now})
        r = requests.get(f"{BASE}/api/admin/programs/{pid}/seat-suggestion",
                         cookies=COOKIES, headers=HEADERS, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["suggested"] == 10
        assert "+20%" not in body["why"]

    def test_no_history_capacity_zero_returns_null(self, seed_program):
        pid, _ = seed_program
        r = requests.get(f"{BASE}/api/admin/programs/{pid}/seat-suggestion",
                         cookies=COOKIES, headers=HEADERS, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["suggested"] is None, body

    def test_history_endpoint_includes_suggestion(self, seed_program):
        pid, _ = seed_program
        now = _iso()
        db.program_snapshots.insert_one({
            "program_id": pid, "kind": "season", "label": "QA S1",
            "capacity": 10, "taken": 10, "waitlist": 4, "days_to_fill": 10,
            "season_started_at": now, "season_ended_at": now, "created_at": now})
        r = requests.get(f"{BASE}/api/admin/programs/{pid}/history",
                         cookies=COOKIES, headers=HEADERS, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "suggestion" in body


# --- Clone with launch_email --------------------------------------------

class TestCloneLaunchEmail:
    def test_invalid_launch_email_returns_400(self, seed_program):
        pid, _ = seed_program
        r = requests.post(f"{BASE}/api/admin/programs/{pid}/clone",
                          json={"capacity": 5, "transfer": "none", "launch_email": "bogus"},
                          cookies=COOKIES, headers=HEADERS, timeout=20)
        assert r.status_code == 400, r.text

    def test_clone_response_includes_launch_audience(self, seed_program):
        pid, slug = seed_program
        # seed 3 QA submissions in original program (one per stage)
        now = _iso()
        for em, stg in [("qa.l1@example.com", "enrolled"),
                        ("qa.l2@example.com", "waitlisted"),
                        ("qa.l3@example.com", "not_fit")]:
            db.submissions.insert_one({
                "id": f"qs-{uuid.uuid4().hex[:8]}", "type": "program_signup", "program_id": pid,
                "data": {"name": em.split("@")[0], "email": em, "program": "QA Seat Program", "program_slug": slug},
                "created_at": now, "stage": stg,
            })
        r = requests.post(f"{BASE}/api/admin/programs/{pid}/clone",
                          json={"capacity": 5, "transfer": "none", "launch_email": "manual"},
                          cookies=COOKIES, headers=HEADERS, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "launch_audience" in body
        assert body["launch_audience"] == 3, body


# --- Launch (manual) ---------------------------------------------------

class TestLaunchManual:
    def test_full_manual_launch_flow(self, seed_program):
        pid, slug = seed_program
        now = _iso()
        for em, stg in [("qa.m1@example.com", "enrolled"),
                        ("qa.m2@example.com", "waitlisted"),
                        ("qa.m3@example.com", "not_fit")]:
            db.submissions.insert_one({
                "id": f"qs-{uuid.uuid4().hex[:8]}", "type": "program_signup", "program_id": pid,
                "data": {"name": em.split("@")[0], "email": em, "program": "QA Seat Program", "program_slug": slug},
                "created_at": now, "stage": stg,
            })
        # Clone manual
        cr = requests.post(f"{BASE}/api/admin/programs/{pid}/clone",
                           json={"capacity": 5, "transfer": "none", "launch_email": "manual"},
                           cookies=COOKIES, headers=HEADERS, timeout=20)
        assert cr.status_code == 200, cr.text
        clone = cr.json()
        cid, cslug = clone["id"], clone["slug"]

        # Before publish: POST launch -> 400 (publish first)
        r = requests.post(f"{BASE}/api/admin/programs/{cid}/launch",
                          cookies=COOKIES, headers=HEADERS, timeout=20)
        assert r.status_code == 400, r.text
        assert "publish" in r.text.lower() or "first" in r.text.lower()

        # Publish via admin PUT (full payload)
        full = {k: v for k, v in clone.items() if k in {
            "title", "slug", "description", "image_url", "capacity", "published",
            "waitlist_mode", "cloned_from", "launch_email", "transfer_from",
            "transfer_mode", "order", "age_min", "age_max", "accordion", "detail_blocks",
            "testimonial_ids", "home_testimonial_ids", "price_cents", "price_display",
            "gallery_image_urls", "cta_label", "cta_url"
        }}
        full["published"] = True
        pr = requests.put(f"{BASE}/api/admin/programs/{cid}", json=full,
                          cookies=COOKIES, headers=HEADERS, timeout=20)
        assert pr.status_code == 200, pr.text
        # NO auto send (manual)
        assert db.session_launch_emails.count_documents({"program_id": cid}) == 0

        # GET launch info -> pending 3
        gi = requests.get(f"{BASE}/api/admin/programs/{cid}/launch",
                          cookies=COOKIES, headers=HEADERS, timeout=20)
        assert gi.status_code == 200
        assert gi.json()["pending"] == 3, gi.json()

        # Add a submission in the clone for one of the emails -> pending 2
        db.submissions.insert_one({
            "id": f"qs-{uuid.uuid4().hex[:8]}", "type": "program_signup", "program_id": cid,
            "data": {"name": "qa.m1", "email": "qa.m1@example.com",
                     "program": clone["title"], "program_slug": cslug},
            "created_at": _iso(), "stage": "enrolled",
        })
        gi2 = requests.get(f"{BASE}/api/admin/programs/{cid}/launch",
                           cookies=COOKIES, headers=HEADERS, timeout=20)
        assert gi2.json()["pending"] == 2, gi2.json()

        # POST launch -> queued 2
        lr = requests.post(f"{BASE}/api/admin/programs/{cid}/launch",
                           cookies=COOKIES, headers=HEADERS, timeout=20)
        assert lr.status_code == 200, lr.text
        assert lr.json()["queued"] == 2

        time.sleep(4)
        assert db.session_launch_emails.count_documents({"program_id": cid}) == 2

        # POST again -> 400 nobody new
        lr2 = requests.post(f"{BASE}/api/admin/programs/{cid}/launch",
                            cookies=COOKIES, headers=HEADERS, timeout=20)
        assert lr2.status_code == 400, lr2.text


# --- Launch auto ------------------------------------------------------

class TestLaunchAuto:
    def test_auto_launch_on_publish(self, seed_program):
        pid, slug = seed_program
        now = _iso()
        for em, stg in [("qa.a1@example.com", "enrolled"),
                        ("qa.a2@example.com", "waitlisted")]:
            db.submissions.insert_one({
                "id": f"qs-{uuid.uuid4().hex[:8]}", "type": "program_signup", "program_id": pid,
                "data": {"name": em.split("@")[0], "email": em, "program": "QA Seat Program", "program_slug": slug},
                "created_at": now, "stage": stg,
            })
        cr = requests.post(f"{BASE}/api/admin/programs/{pid}/clone",
                           json={"capacity": 5, "transfer": "none", "launch_email": "auto"},
                           cookies=COOKIES, headers=HEADERS, timeout=20)
        assert cr.status_code == 200, cr.text
        clone = cr.json()
        cid = clone["id"]

        full = {k: v for k, v in clone.items() if k in {
            "title", "slug", "description", "image_url", "capacity", "published",
            "waitlist_mode", "cloned_from", "launch_email", "transfer_from",
            "transfer_mode", "order", "age_min", "age_max", "accordion", "detail_blocks",
            "testimonial_ids", "home_testimonial_ids", "price_cents", "price_display",
            "gallery_image_urls", "cta_label", "cta_url"
        }}
        full["published"] = True
        pr = requests.put(f"{BASE}/api/admin/programs/{cid}", json=full,
                          cookies=COOKIES, headers=HEADERS, timeout=20)
        assert pr.status_code == 200, pr.text

        time.sleep(4)
        count = db.session_launch_emails.count_documents({"program_id": cid})
        assert count == 2, f"expected 2 auto sends, got {count}"
        p2 = db.programs.find_one({"id": cid})
        assert p2.get("launch_sent") is True

        # Re-publish does not resend
        pr2 = requests.put(f"{BASE}/api/admin/programs/{cid}", json=full,
                           cookies=COOKIES, headers=HEADERS, timeout=20)
        assert pr2.status_code == 200
        time.sleep(2)
        assert db.session_launch_emails.count_documents({"program_id": cid}) == 2


# --- Badge wall celebration ----------------------------------------------

class TestBadgeWallCelebration:
    def _cleanup(self, email):
        db.volunteer_milestones.delete_many({"email": email})
        db.volunteer_hours.delete_many({"email": email})
        db.badge_wall_notified.delete_many({"email": email})

    def test_celebrate_and_public_filter(self):
        email = "qa.bw1@example.com"
        self._cleanup(email)
        try:
            now = _iso()
            db.volunteer_hours.insert_one({
                "id": f"vh-{uuid.uuid4().hex[:8]}", "email": email, "name": "QA Badge",
                "hours": 10.0, "status": "approved", "leaderboard": True,
                "scope": "all_time", "created_at": now,
            })
            db.volunteer_milestones.insert_one({
                "email": email, "scope": "all_time", "threshold": 10,
                "label": "10 Hours", "awarded_at": now,
                "share_token": f"tok-{uuid.uuid4().hex[:8]}",
            })
            # Call the private function via import
            import sys
            sys.path.insert(0, "/app/backend")
            import server
            n1 = asyncio.get_event_loop().run_until_complete(server._celebrate_badge_wall())
            # One notified doc
            assert db.badge_wall_notified.count_documents({"email": email}) == 1
            # Second call adds none
            n2 = asyncio.get_event_loop().run_until_complete(server._celebrate_badge_wall())
            assert db.badge_wall_notified.count_documents({"email": email}) == 1

            # Add a second milestone -> exactly 1 more
            db.volunteer_milestones.insert_one({
                "email": email, "scope": "all_time", "threshold": 25,
                "label": "25 Hours", "awarded_at": _iso(),
                "share_token": f"tok-{uuid.uuid4().hex[:8]}",
            })
            asyncio.get_event_loop().run_until_complete(server._celebrate_badge_wall())
            assert db.badge_wall_notified.count_documents({"email": email}) == 2

            # Public endpoint does not leak email/first/scope
            r = requests.get(f"{BASE}/api/volunteer-hours/badge-wall", timeout=20)
            assert r.status_code == 200
            items = r.json()["items"]
            assert any(i.get("share_token") for i in items)
            for i in items:
                assert "email" not in i
                assert "first" not in i
                assert "scope" not in i
        finally:
            self._cleanup(email)


# --- Template insights ---------------------------------------------------

class TestTemplateInsights:
    def _cleanup(self):
        db.appeal_templates.delete_many({"id": {"$in": ["qa-tpl-1", "qa-tpl-2"]}})
        db.segment_emails.delete_many({"id": {"$in": ["qa-se-1", "qa-se-2"]}})
        db.payment_transactions.delete_many({"session_id": {"$regex": "^qa_"}})

    def test_template_insights_uses_matched_top(self):
        self._cleanup()
        try:
            now = _iso()
            db.appeal_templates.insert_many([
                {"id": "qa-tpl-1", "name": "QA Year End", "subject": "QA Year End Subject",
                 "message": "x", "created_at": now},
                {"id": "qa-tpl-2", "name": "QA Spring", "subject": "QA Spring Subj",
                 "message": "y", "created_at": now},
            ])
            db.segment_emails.insert_many([
                {"id": "qa-se-1", "template_id": "qa-tpl-1", "subject": "anything",
                 "sent": 10, "clicks": 5, "sent_at": now, "kind": "segment"},
                {"id": "qa-se-2", "subject": "QA Spring Subj",
                 "sent": 20, "clicks": 2, "sent_at": now, "kind": "segment"},
            ])
            db.payment_transactions.insert_many([
                {"id": f"pt-{uuid.uuid4().hex[:8]}", "appeal_id": "qa-se-1",
                 "session_id": "qa_sess_1", "donor_email": "qa.d1@example.com",
                 "amount": 100.0, "payment_status": "paid", "created_at": now},
                {"id": f"pt-{uuid.uuid4().hex[:8]}", "appeal_id": "qa-se-2",
                 "session_id": "qa_sess_2", "donor_email": "qa.d2@example.com",
                 "amount": 40.0, "payment_status": "paid", "created_at": now},
            ])
            r = requests.get(f"{BASE}/api/admin/reports/template-insights",
                             cookies=COOKIES, headers=HEADERS, timeout=20)
            assert r.status_code == 200, r.text
            items = {i["id"]: i for i in r.json()["items"]}
            assert "qa-tpl-1" in items and "qa-tpl-2" in items
            t1, t2 = items["qa-tpl-1"], items["qa-tpl-2"]
            assert t1["uses"] == 1, t1
            assert t1["per_recipient"] == 10.0, t1
            assert t1["top"] is True, t1
            assert t2["uses"] == 1, t2
            assert t2["matched"] == 1, t2
            assert t2["per_recipient"] == 2.0, t2
        finally:
            self._cleanup()


# --- Scheduled appeals template_id persistence ----------------------------

class TestScheduledAppealTemplateId:
    def test_create_scheduled_stores_template_id(self):
        tid = "qa-tpl-sched-1"
        db.appeal_templates.insert_one({
            "id": tid, "name": "QA Sched Tpl", "subject": "QA SubjX",
            "message": "body", "created_at": _iso()})
        try:
            future = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
            payload = {"segment": "all", "subject": "QA Scheduled Subj",
                       "message": "QA body", "send_on": future, "repeat": "none",
                       "template_id": tid}
            r = requests.post(f"{BASE}/api/admin/scheduled-appeals", json=payload,
                              cookies=COOKIES, headers=HEADERS, timeout=20)
            assert r.status_code in (200, 201), r.text
            sid = r.json().get("id")
            assert sid, r.json()
            doc = db.scheduled_appeals.find_one({"id": sid})
            assert doc is not None
            assert doc.get("template_id") == tid, doc
            # cleanup
            rd = requests.delete(f"{BASE}/api/admin/scheduled-appeals/{sid}",
                                 cookies=COOKIES, headers=HEADERS, timeout=20)
            assert rd.status_code in (200, 204)
        finally:
            db.appeal_templates.delete_one({"id": tid})
            db.scheduled_appeals.delete_many({"subject": "QA Scheduled Subj"})
