"""Backend tests for Transparency, Waitlist (auto+invite), ICS, Add-to-Calendar, Donor Self-Service.
Prereqs: `python3 /app/backend/tests/qa_session.py up` must have been run (seeds admin cookie
session_token=qa_tok_123). Teardown done by qa_session.py down + test cleanup fixture.
"""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
DB = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
ADMIN_HEADERS = {"X-Requested-With": "XMLHttpRequest"}
ADMIN_COOKIES = {"session_token": "qa_tok_123"}


def _future_date(days=14):
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


@pytest.fixture
def admin():
    s = requests.Session()
    s.headers.update(ADMIN_HEADERS)
    s.cookies.update(ADMIN_COOKIES)
    return s


@pytest.fixture
def pub():
    return requests.Session()


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    # Remove any QA-created events / rsvps / waitlist / tokens
    DB.events.delete_many({"title": {"$regex": "^QA"}})
    DB.event_rsvps.delete_many({"email": {"$regex": "example.com$"}})
    DB.event_waitlist.delete_many({"email": {"$regex": "example.com$"}})
    DB.submissions.delete_many({"data.email": {"$regex": "example.com$"}})
    DB.donor_manage_tokens.delete_many({"token": {"$regex": "^qa_"}})
    DB.settings.delete_one({"key": "transparency"})


# ---------- Transparency ----------
class TestTransparency:
    def test_public_transparency_defaults_when_unset(self, pub):
        DB.settings.delete_one({"key": "transparency"})
        r = pub.get(f"{BASE}/api/transparency")
        assert r.status_code == 200
        j = r.json()
        assert j["updated_at"] is None  # never published
        assert len(j["breakdown"]) == 3
        assert j["reports"] == []
        assert j["financials"] == []

    def test_admin_transparency_rejects_non_100(self, admin):
        payload = {
            "headline_text": "QA headline",
            "breakdown": [{"label": "A", "pct": 50, "color": "var(--csc-magenta)"},
                          {"label": "B", "pct": 40, "color": "var(--csc-plum-soft)"}],
            "stats": [], "financials": [], "reports": [],
        }
        r = admin.put(f"{BASE}/api/admin/transparency", json=payload)
        assert r.status_code == 400
        assert "100" in r.json()["detail"]

    def test_admin_transparency_requires_admin(self, pub):
        r = pub.put(f"{BASE}/api/admin/transparency", json={"breakdown": []})
        assert r.status_code in (401, 403)

    def test_admin_transparency_full_publish(self, admin, pub):
        payload = {
            "headline_text": "QA transparency headline",
            "breakdown": [
                {"label": "Programs", "pct": 80, "color": "var(--csc-magenta)"},
                {"label": "Admin", "pct": 12, "color": "var(--csc-plum-soft)"},
                {"label": "Fundraising", "pct": 8, "color": "var(--csc-gold)"},
            ],
            "stats": [{"value": "QA-123", "label": "QA sisters"},
                      {"value": "QA-20", "label": "QA programs"}],
            "financials": [{"year": "2024", "revenue": 100000, "expenses": 90000, "program_expenses": 72000},
                           {"year": "2023", "revenue": 80000, "expenses": 70000, "program_expenses": 56000}],
            "reports": [{"year": "2024", "type": "990", "title": "QA 990",
                         "url": "https://example.com/qa.pdf", "size": "1 MB"}],
        }
        r = admin.put(f"{BASE}/api/admin/transparency", json=payload)
        assert r.status_code == 200, r.text
        got = r.json()
        assert got["headline_text"] == "QA transparency headline"
        assert got["breakdown"][0]["pct"] == 80
        assert got["updated_at"] is not None
        assert len(got["reports"]) == 1 and got["reports"][0]["type"] == "990"
        # Public reflects it
        p = pub.get(f"{BASE}/api/transparency").json()
        assert p["headline_text"] == "QA transparency headline"
        assert p["financials"][0]["year"] == "2024"  # sorted desc
        assert p["stats"][0]["value"] == "QA-123"

    def test_admin_transparency_rejects_bad_report_url(self, admin):
        payload = {
            "headline_text": "", "stats": [], "financials": [],
            "breakdown": [{"label": "A", "pct": 100, "color": "var(--csc-magenta)"}],
            "reports": [{"year": "2024", "type": "990", "title": "x",
                         "url": "ftp://bad", "size": ""}],
        }
        r = admin.put(f"{BASE}/api/admin/transparency", json=payload)
        assert r.status_code == 400


# ---------- Events / Waitlist / ICS ----------
class TestWaitlistAuto:
    @pytest.fixture(scope="class")
    def event_id(self, request):
        s = requests.Session(); s.headers.update(ADMIN_HEADERS); s.cookies.update(ADMIN_COOKIES)
        r = s.post(f"{BASE}/api/admin/events", json={
            "title": f"QA Auto Waitlist {uuid.uuid4().hex[:6]}",
            "date": _future_date(14), "time": "6:00 PM",
            "location": "Virtual", "capacity": 1,
            "description": "QA", "category": "QA", "waitlist_mode": "auto",
        })
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        yield eid
        s.delete(f"{BASE}/api/admin/events/{eid}")

    def test_rsvp_fills_last_seat(self, event_id, pub):
        r = pub.post(f"{BASE}/api/events/{event_id}/rsvp",
                     json={"name": "QA One", "email": "qa.one@example.com", "guests": 1})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["spots_left"] == 0
        assert "ics_url" in j and "gcal_url" in j
        assert "/api/events/" in j["ics_url"]

    def test_rsvp_full_returns_409(self, event_id, pub):
        time.sleep(1)
        r = pub.post(f"{BASE}/api/events/{event_id}/rsvp",
                     json={"name": "QA Two", "email": "qa.two@example.com", "guests": 1})
        assert r.status_code == 409
        assert "full" in r.json()["detail"].lower() or "waitlist" in r.json()["detail"].lower()

    def test_ics_endpoint(self, event_id, pub):
        r = pub.get(f"{BASE}/api/events/{event_id}/calendar.ics")
        assert r.status_code == 200
        assert "text/calendar" in r.headers.get("content-type", "")
        body = r.text
        assert "BEGIN:VCALENDAR" in body and "END:VCALENDAR" in body
        assert "BEGIN:VEVENT" in body

    def test_waitlist_join_and_dup(self, event_id, pub):
        time.sleep(13)  # rate limit (shared bucket w/ rsvp 5/min)
        r = pub.post(f"{BASE}/api/events/{event_id}/waitlist",
                     json={"name": "QA Wait", "email": "qa.wait@example.com", "guests": 1})
        assert r.status_code == 200, r.text
        assert r.json()["position"] == 1
        time.sleep(13)
        r2 = pub.post(f"{BASE}/api/events/{event_id}/waitlist",
                      json={"name": "QA Wait", "email": "qa.wait@example.com", "guests": 1})
        assert r2.status_code == 409

    def test_remove_rsvp_promotes_waitlister(self, event_id, admin):
        rsvp = DB.event_rsvps.find_one({"event_id": event_id, "email": "qa.one@example.com"})
        assert rsvp
        r = admin.delete(f"{BASE}/api/admin/events/{event_id}/rsvps/{rsvp['id']}")
        assert r.status_code == 200
        # Wait for bg task
        for _ in range(10):
            time.sleep(0.5)
            new_rsvp = DB.event_rsvps.find_one({"event_id": event_id, "email": "qa.wait@example.com"})
            if new_rsvp:
                break
        assert new_rsvp is not None, "Waitlister should be auto-promoted to RSVP"
        w = DB.event_waitlist.find_one({"event_id": event_id, "email": "qa.wait@example.com"})
        assert w["status"] == "promoted"


class TestWaitlistInvite:
    @pytest.fixture(scope="class")
    def event_id(self):
        s = requests.Session(); s.headers.update(ADMIN_HEADERS); s.cookies.update(ADMIN_COOKIES)
        r = s.post(f"{BASE}/api/admin/events", json={
            "title": f"QA Invite Waitlist {uuid.uuid4().hex[:6]}",
            "date": _future_date(15), "time": "6:00 PM",
            "location": "Virtual", "capacity": 1,
            "description": "QA", "category": "QA", "waitlist_mode": "invite",
        })
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        yield eid
        s.delete(f"{BASE}/api/admin/events/{eid}")

    def test_full_flow_invite_mode(self, event_id, pub, admin):
        time.sleep(65)
        # Fill event
        r = pub.post(f"{BASE}/api/events/{event_id}/rsvp",
                     json={"name": "QA Full", "email": "qa.inv.full@example.com", "guests": 1})
        assert r.status_code == 200, r.text
        time.sleep(15)
        # Join waitlist
        r2 = pub.post(f"{BASE}/api/events/{event_id}/waitlist",
                      json={"name": "QA Inv", "email": "qa.inv.wait@example.com", "guests": 1})
        assert r2.status_code == 200, r2.text
        # Remove the RSVP -> waitlister should be INVITED (not promoted)
        rsvp = DB.event_rsvps.find_one({"event_id": event_id, "email": "qa.inv.full@example.com"})
        admin.delete(f"{BASE}/api/admin/events/{event_id}/rsvps/{rsvp['id']}")
        token = None
        for _ in range(10):
            time.sleep(0.5)
            w = DB.event_waitlist.find_one({"event_id": event_id, "email": "qa.inv.wait@example.com"})
            if w and w["status"] == "invited":
                token = w.get("invite_token")
                break
        assert token, "Waitlister should be set to 'invited' with token"
        # Should NOT create a new rsvp yet
        assert DB.event_rsvps.find_one({"event_id": event_id, "email": "qa.inv.wait@example.com"}) is None

        # Token info
        info = pub.get(f"{BASE}/api/events/token/{token}").json()
        assert info["kind"] == "claim" and info["state"] == "open"

        # Claim it
        claim = pub.post(f"{BASE}/api/events/token/{token}")
        assert claim.status_code == 200
        assert claim.json()["done"] == "claimed"
        assert "ics_url" in claim.json()

        # Second attempt => already claimed
        again = pub.get(f"{BASE}/api/events/token/{token}").json()
        assert again.get("state") == "claimed"

        # Invalid token
        bad = pub.get(f"{BASE}/api/events/token/nonexistent_qa_token_zzz")
        assert bad.status_code == 404


class TestRsvpCancelToken:
    def test_cancel_via_token(self, pub, admin):
        # Create event
        r = admin.post(f"{BASE}/api/admin/events", json={
            "title": f"QA Cancel {uuid.uuid4().hex[:6]}",
            "date": _future_date(16), "time": "6:00 PM",
            "location": "Virtual", "capacity": 5,
            "description": "QA", "category": "QA", "waitlist_mode": "auto",
        })
        eid = r.json()["id"]
        try:
            time.sleep(13)
            resp = pub.post(f"{BASE}/api/events/{eid}/rsvp",
                            json={"name": "QA Cx", "email": "qa.cancel@example.com", "guests": 1})
            assert resp.status_code == 200
            doc = DB.event_rsvps.find_one({"event_id": eid, "email": "qa.cancel@example.com"})
            tok = doc["cancel_token"]
            info = pub.get(f"{BASE}/api/events/token/{tok}").json()
            assert info["kind"] == "cancel"
            cx = pub.post(f"{BASE}/api/events/token/{tok}")
            assert cx.status_code == 200
            assert cx.json()["done"] == "cancelled"
            assert DB.event_rsvps.find_one({"event_id": eid, "email": "qa.cancel@example.com"}) is None
        finally:
            admin.delete(f"{BASE}/api/admin/events/{eid}")


# ---------- Donor Self-Service ----------
class TestManageGift:
    def test_bogus_token_info_invalid(self, pub):
        r = pub.get(f"{BASE}/api/donor/manage-token/qa_bogus_token_zzz_{uuid.uuid4().hex}")
        assert r.status_code == 200
        assert r.json()["valid"] is False

    def test_bogus_portal_token_410(self, pub):
        time.sleep(1)
        r = pub.post(f"{BASE}/api/donor/portal", json={"token": "qa_bogus_portal_zzz"})
        assert r.status_code == 410

    def test_manage_link_generic_response(self, pub):
        # unknown email: generic reply
        r = pub.post(f"{BASE}/api/donor/manage-link", json={"email": f"qa.unknown.{uuid.uuid4().hex[:6]}@example.com"})
        assert r.status_code == 200
        assert "secure link" in r.json()["message"].lower()

    def test_manage_link_invalid_email_400(self, pub):
        time.sleep(1)
        r = pub.post(f"{BASE}/api/donor/manage-link", json={"email": "not-an-email"})
        assert r.status_code == 400

    def test_real_donor_portal_redirect(self, pub):
        # Only run if a real monthly donor exists
        txn = DB.payment_transactions.find_one({
            "frequency": "monthly", "payment_status": "paid",
            "stripe_subscription_id": {"$nin": [None, ""]}})
        if not txn:
            pytest.skip("No real monthly donor present")
        tok = f"qa_manage_tok_{uuid.uuid4().hex[:10]}"
        DB.donor_manage_tokens.insert_one({
            "token": tok, "email": txn["donor_email"].lower(),
            "kind": "request", "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        })
        try:
            # token info says valid
            info = pub.get(f"{BASE}/api/donor/manage-token/{tok}").json()
            assert info["valid"] is True
            # open portal
            time.sleep(1)
            r = pub.post(f"{BASE}/api/donor/portal", json={"token": tok})
            assert r.status_code == 200, r.text
            url = r.json()["url"]
            assert "billing.stripe.com" in url
            # second use -> 410 (one-time)
            time.sleep(1)
            r2 = pub.post(f"{BASE}/api/donor/portal", json={"token": tok})
            assert r2.status_code == 410
        finally:
            DB.donor_manage_tokens.delete_one({"token": tok})
