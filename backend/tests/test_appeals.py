"""Backend tests for Recurring Appeals + Appeal Analytics (click tracking)."""
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"
SESSION_TOKEN = "qa_appeal_tok_1791605910187"

HEADERS_ADMIN = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json",
}


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


# --- Appeal click tracking ---
def test_track_appeal_click_known_id_302_and_increments(db):
    appeal_id = str(uuid.uuid4())
    db.segment_emails.insert_one({
        "id": appeal_id, "segment": "all", "subject": "QA Click", "recipients": 1,
        "sent": 1, "clicks": 0, "sent_by_name": "QA",
    })
    try:
        r = requests.get(f"{BASE_URL}/api/t/appeal/{appeal_id}", allow_redirects=False, timeout=15)
        assert r.status_code in (302, 307), r.status_code
        loc = r.headers.get("location", "")
        assert f"/donate?appeal={appeal_id}" in loc, loc
        doc = db.segment_emails.find_one({"id": appeal_id})
        assert doc["clicks"] == 1
    finally:
        db.segment_emails.delete_one({"id": appeal_id})


def test_track_appeal_click_unknown_redirects_to_donate():
    r = requests.get(f"{BASE_URL}/api/t/appeal/{uuid.uuid4()}", allow_redirects=False, timeout=15)
    assert r.status_code in (302, 307)
    assert r.headers.get("location", "").endswith("/donate") or "/donate?appeal=" in r.headers.get("location", "")


# --- Scheduled appeals POST validation ---
def test_scheduled_appeal_invalid_repeat_returns_400():
    payload = {"segment": "all", "subject": "QA", "message": "hi", "send_on": "2099-01-01", "repeat": "weekly"}
    r = requests.post(f"{BASE_URL}/api/admin/scheduled-appeals", headers=HEADERS_ADMIN, json=payload, timeout=15)
    assert r.status_code == 400, (r.status_code, r.text)


def test_scheduled_appeal_create_monthly_and_cancel(db):
    payload = {"segment": "all", "subject": "QA Monthly", "message": "<p>hi</p>", "send_on": "2099-01-15", "repeat": "monthly"}
    r = requests.post(f"{BASE_URL}/api/admin/scheduled-appeals", headers=HEADERS_ADMIN, json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    data = r.json()
    sid = data.get("id") or data.get("scheduled_id") or (data.get("appeal") or {}).get("id")
    # Fallback: find by subject
    if not sid:
        row = db.scheduled_appeals.find_one({"subject": "QA Monthly"})
        sid = row and row.get("id")
    assert sid, data
    # List
    rl = requests.get(f"{BASE_URL}/api/admin/scheduled-appeals", headers=HEADERS_ADMIN, timeout=15)
    assert rl.status_code == 200
    items = rl.json().get("items", rl.json()) if isinstance(rl.json(), dict) else rl.json()
    found = next((x for x in items if x.get("id") == sid), None)
    assert found and found.get("repeat") == "monthly"
    # Cancel
    rd = requests.delete(f"{BASE_URL}/api/admin/scheduled-appeals/{sid}", headers=HEADERS_ADMIN, timeout=15)
    assert rd.status_code in (200, 204)
    db.scheduled_appeals.delete_one({"id": sid})


# --- Appeal history aggregates ---
def test_appeal_history_aggregates_clicks_gifts_raised(db):
    from datetime import datetime, timezone
    appeal_id = str(uuid.uuid4())
    db.segment_emails.insert_one({
        "id": appeal_id, "segment": "all", "subject": "QA Seed", "recipients": 2, "sent": 2,
        "clicks": 3, "sent_by_name": "QA", "sent_at": datetime.now(timezone.utc).isoformat(),
    })
    db.payment_transactions.insert_one({
        "session_id": "qa_x", "amount": 40, "payment_status": "paid", "appeal_id": appeal_id,
    })
    try:
        r = requests.get(f"{BASE_URL}/api/admin/appeals", headers=HEADERS_ADMIN, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        rows = body.get("items", body) if isinstance(body, dict) else body
        row = next((x for x in rows if x.get("id") == appeal_id), None)
        assert row, "appeal row missing"
        assert row.get("clicks") == 3
        assert row.get("donations") == 1
        assert row.get("raised") == 40
    finally:
        db.segment_emails.delete_one({"id": appeal_id})
        db.payment_transactions.delete_one({"session_id": "qa_x"})


# --- Checkout stores appeal_id ---
def test_checkout_stores_appeal_id(db):
    appeal_id = str(uuid.uuid4())
    payload = {
        "amount": 10, "frequency": "one-time", "donor_name": "QA Checkout",
        "donor_email": "qa.checkout@example.com", "origin_url": BASE_URL, "appeal_id": appeal_id,
    }
    r = requests.post(f"{BASE_URL}/api/payments/checkout", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    sid = r.json().get("session_id")
    assert sid
    try:
        doc = db.payment_transactions.find_one({"session_id": sid})
        assert doc, "transaction not persisted"
        assert doc.get("appeal_id") == appeal_id
    finally:
        db.payment_transactions.delete_one({"session_id": sid})
