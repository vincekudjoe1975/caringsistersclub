"""Backend tests: Events, RSVPs, Submissions, Site URL settings."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
TOKEN = os.environ.get("QA_SESSION_TOKEN")  # set by test runner


@pytest.fixture(scope="session")
def admin():
    assert TOKEN, "QA_SESSION_TOKEN env is required"
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {TOKEN}",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
    })
    return s


@pytest.fixture(scope="session")
def public():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Auth / Host detection ----------
def test_auth_me_detects_site_url(admin):
    r = admin.get(f"{API}/auth/me")
    assert r.status_code == 200, r.text
    # Read settings
    r2 = admin.get(f"{API}/admin/settings")
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("detected_site_url", "").startswith("https://")


# ---------- Site URL settings ----------
def test_site_url_rejects_bad(admin):
    r = admin.put(f"{API}/admin/settings", json={"site_url": "http://bad"})
    assert r.status_code == 400
    assert "https" in r.json().get("detail", "").lower()


def test_site_url_accepts_valid_then_restores_empty(admin):
    r = admin.put(f"{API}/admin/settings", json={"site_url": "https://example.org"})
    assert r.status_code == 200
    r2 = admin.put(f"{API}/admin/settings", json={"site_url": ""})
    assert r2.status_code == 200


# ---------- Events CRUD ----------
@pytest.fixture(scope="session")
def created_event(admin):
    future = "2030-10-15"
    payload = {
        "title": "TEST_QA_Event_" + str(uuid.uuid4())[:6],
        "date": future, "time": "6:00 PM",
        "location": "Community Hall", "description": "Test",
        "category": "Workshop", "capacity": 3, "image_url": "",
    }
    r = admin.post(f"{API}/admin/events", json=payload)
    assert r.status_code == 200, r.text
    ev = r.json()
    assert ev["title"] == payload["title"]
    assert ev["capacity"] == 3
    yield ev
    # cleanup
    admin.delete(f"{API}/admin/events/{ev['id']}")


def test_event_list_admin_has_event(admin, created_event):
    r = admin.get(f"{API}/admin/events")
    assert r.status_code == 200
    ids = [e["id"] for e in r.json()["items"]]
    assert created_event["id"] in ids


def test_event_public_shows_upcoming(public, created_event):
    r = public.get(f"{API}/events")
    assert r.status_code == 200
    items = r.json()["items"]
    ev = next((e for e in items if e["id"] == created_event["id"]), None)
    assert ev is not None
    assert ev["spots_left"] == 3


def test_event_invalid_date(admin):
    r = admin.post(f"{API}/admin/events", json={"title": "x", "date": "bad", "capacity": 2})
    assert r.status_code == 400


def test_event_update_persists(admin, created_event):
    new_title = created_event["title"] + "_EDITED"
    r = admin.put(f"{API}/admin/events/{created_event['id']}", json={
        "title": new_title, "date": created_event["date"], "time": created_event.get("time", ""),
        "location": created_event.get("location", ""), "description": created_event.get("description", ""),
        "category": created_event.get("category", ""), "capacity": created_event["capacity"],
    })
    assert r.status_code == 200
    assert r.json()["title"] == new_title


# ---------- Submissions validation ----------
def test_submission_contact_success(public):
    r = public.post(f"{API}/submissions", json={
        "type": "contact", "name": "QA Tester", "email": "qa_contact@example.com",
        "message": "Hello world",
    })
    assert r.status_code == 200
    assert "id" in r.json()


def test_submission_invalid_email(public):
    r = public.post(f"{API}/submissions", json={
        "type": "contact", "name": "QA", "email": "notanemail", "message": "hi",
    })
    assert r.status_code == 400
    assert "valid email" in r.json()["detail"].lower()


def test_submission_contact_empty_message(public):
    r = public.post(f"{API}/submissions", json={
        "type": "contact", "name": "QA", "email": "qa_empty@example.com", "message": "   ",
    })
    assert r.status_code == 400


def test_submission_type_donation_rejected(public):
    r = public.post(f"{API}/submissions", json={
        "type": "donation", "name": "QA", "email": "qa@example.com",
    })
    assert r.status_code == 400


def test_submission_type_rsvp_rejected(public):
    r = public.post(f"{API}/submissions", json={
        "type": "rsvp", "name": "QA", "email": "qa@example.com",
    })
    assert r.status_code == 400


# ---------- RSVP flow ----------
def test_rsvp_full_flow(public, admin, created_event):
    # wait to avoid rate limit from earlier submissions
    time.sleep(62)
    eid = created_event["id"]
    # First rsvp 2 seats
    r1 = public.post(f"{API}/events/{eid}/rsvp", json={
        "name": "Alice QA", "email": "qa_rsvp_a@example.com", "guests": 2,
    })
    assert r1.status_code == 200, r1.text
    assert r1.json()["spots_left"] == 1

    # Duplicate email
    r_dup = public.post(f"{API}/events/{eid}/rsvp", json={
        "name": "Alice QA", "email": "qa_rsvp_a@example.com", "guests": 1,
    })
    assert r_dup.status_code == 409
    assert "already" in r_dup.json()["detail"].lower()

    # Over capacity: 2 more seats requested but only 1 left
    r_over = public.post(f"{API}/events/{eid}/rsvp", json={
        "name": "Bob QA", "email": "qa_rsvp_b@example.com", "guests": 2,
    })
    assert r_over.status_code == 409
    assert "only 1" in r_over.json()["detail"].lower() or "1 spot" in r_over.json()["detail"].lower()

    # Fill last seat
    r_last = public.post(f"{API}/events/{eid}/rsvp", json={
        "name": "Carol QA", "email": "qa_rsvp_c@example.com", "guests": 1,
    })
    assert r_last.status_code == 200
    assert r_last.json()["spots_left"] == 0

    # Full
    r_full = public.post(f"{API}/events/{eid}/rsvp", json={
        "name": "Dave QA", "email": "qa_rsvp_d@example.com", "guests": 1,
    })
    assert r_full.status_code == 409

    # Admin list rsvps
    r_list = admin.get(f"{API}/admin/events/{eid}/rsvps")
    assert r_list.status_code == 200
    rsvps = r_list.json()["items"]
    assert len(rsvps) == 2

    # CSV export
    r_csv = admin.get(f"{API}/admin/events/{eid}/rsvps/export")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers.get("content-type", "")
    body = r_csv.text
    assert "Name,Email" in body
    assert "qa_rsvp_a@example.com" in body

    # Delete one rsvp
    rid = rsvps[0]["id"]
    r_del = admin.delete(f"{API}/admin/events/{eid}/rsvps/{rid}")
    assert r_del.status_code == 200


def test_rsvp_invalid_email(public):
    # New valid event
    pass  # covered by validation on event create path; direct invalid email tested here:


def test_rsvp_bad_email_rejected(public, admin, created_event):
    r = public.post(f"{API}/events/{created_event['id']}/rsvp", json={
        "name": "Z", "email": "notanemail", "guests": 1,
    })
    assert r.status_code == 400
    assert "valid email" in r.json()["detail"].lower()
