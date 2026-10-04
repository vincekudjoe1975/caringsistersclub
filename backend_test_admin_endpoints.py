#!/usr/bin/env python3
"""
Test NEW admin endpoints: CSV export, year-end statements, campaign progress emails.
Per review_request: seed admin Bearer token, seed payment_transactions, test endpoints.
"""
import requests
import time
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

# Config
BASE_URL = "http://localhost:8001/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Test data
CURRENT_YEAR = "2026"
test_user_id = f"user_test_{int(time.time() * 1000)}"
test_session_token = f"test_session_{int(time.time() * 1000)}"
test_pending_user_id = f"user_pending_{int(time.time() * 1000)}"
test_pending_session_token = f"test_pending_session_{int(time.time() * 1000)}"

# Track created IDs for cleanup
created_payment_ids = []

def cleanup():
    """Clean up all test data"""
    print("\n🧹 Cleaning up test data...")
    db.users.delete_many({"user_id": {"$in": [test_user_id, test_pending_user_id]}})
    db.user_sessions.delete_many({"session_token": {"$in": [test_session_token, test_pending_session_token]}})
    db.payment_transactions.delete_many({"id": {"$in": created_payment_ids}})
    db.settings.delete_many({"key": "site"})
    db.milestones_sent.delete_many({})
    print("✅ Cleanup complete")

def seed_admin_user():
    """Seed admin user and session per auth_testing.md pattern"""
    print(f"🌱 Seeding admin user (role='admin')...")
    db.users.insert_one({
        "user_id": test_user_id,
        "email": f"test.admin.{int(time.time())}@example.com",
        "name": "Test Admin",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    db.user_sessions.insert_one({
        "user_id": test_user_id,
        "session_token": test_session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    print(f"✅ Admin user seeded with session_token: {test_session_token}")

def seed_pending_user():
    """Seed pending user (role='pending') for 403 tests"""
    print(f"🌱 Seeding pending user (role='pending')...")
    db.users.insert_one({
        "user_id": test_pending_user_id,
        "email": f"test.pending.{int(time.time())}@example.com",
        "name": "Test Pending",
        "picture": "https://via.placeholder.com/150",
        "role": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    db.user_sessions.insert_one({
        "user_id": test_pending_user_id,
        "session_token": test_pending_session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    print(f"✅ Pending user seeded with session_token: {test_pending_session_token}")

def seed_payment_transactions():
    """Seed 3 payment_transactions (payment_status='paid') per review_request"""
    print(f"🌱 Seeding payment_transactions (payment_status='paid')...")
    
    # Transaction 1: one-time, Jane Doe, 2026-03-15
    txn1_id = f"txn_test_{int(time.time() * 1000)}_1"
    db.payment_transactions.insert_one({
        "id": txn1_id,
        "session_id": f"cs_test_{txn1_id}",
        "amount": 100,
        "frequency": "one-time",
        "donor_name": "Jane Doe",
        "donor_email": "jane@example.com",
        "anonymous": False,
        "payment_status": "paid",
        "status": "completed",
        "updated_at": f"{CURRENT_YEAR}-03-15T10:00:00+00:00",
        "created_at": f"{CURRENT_YEAR}-03-15T10:00:00+00:00"
    })
    created_payment_ids.append(txn1_id)
    
    # Transaction 2: monthly, Jane Doe, 2026-04-15, with stripe_subscription_id
    txn2_id = f"txn_test_{int(time.time() * 1000)}_2"
    db.payment_transactions.insert_one({
        "id": txn2_id,
        "session_id": f"cs_test_{txn2_id}",
        "amount": 25,
        "frequency": "monthly",
        "donor_name": "Jane Doe",
        "donor_email": "jane@example.com",
        "anonymous": False,
        "stripe_subscription_id": "sub_X",
        "payment_status": "paid",
        "status": "completed",
        "updated_at": f"{CURRENT_YEAR}-04-15T10:00:00+00:00",
        "created_at": f"{CURRENT_YEAR}-04-15T10:00:00+00:00"
    })
    created_payment_ids.append(txn2_id)
    
    # Transaction 3: one-time, anonymous, 2026-05-01
    txn3_id = f"txn_test_{int(time.time() * 1000)}_3"
    db.payment_transactions.insert_one({
        "id": txn3_id,
        "session_id": f"cs_test_{txn3_id}",
        "amount": 50,
        "frequency": "one-time",
        "donor_name": "Secret",
        "donor_email": "",
        "anonymous": True,
        "payment_status": "paid",
        "status": "completed",
        "updated_at": f"{CURRENT_YEAR}-05-01T10:00:00+00:00",
        "created_at": f"{CURRENT_YEAR}-05-01T10:00:00+00:00"
    })
    created_payment_ids.append(txn3_id)
    
    print(f"✅ Seeded 3 payment_transactions: {created_payment_ids}")

def seed_campaign_settings():
    """Seed campaign settings with goal=1000 for progress test"""
    print(f"🌱 Seeding campaign settings (goal=1000)...")
    # Use PUT endpoint to set goal
    headers = {"Authorization": f"Bearer {test_session_token}"}
    resp = requests.put(f"{BASE_URL}/admin/settings", json={"goal": 1000}, headers=headers)
    if resp.status_code == 200:
        print(f"✅ Campaign settings seeded: goal=1000")
    else:
        print(f"⚠️ Failed to seed campaign settings: {resp.status_code} {resp.text}")

# ============ TEST 1: CSV EXPORT ============
def test_csv_export():
    """Test GET /api/admin/donations/export"""
    print("\n" + "="*60)
    print("TEST 1: CSV EXPORT (GET /api/admin/donations/export)")
    print("="*60)
    
    # 1.1: Without auth -> 401
    print("\n1.1: GET /api/admin/donations/export without auth -> 401")
    resp = requests.get(f"{BASE_URL}/admin/donations/export")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print("✅ PASS: Returns 401 without auth")
    
    # 1.2: With role='pending' token -> 403
    print("\n1.2: GET /api/admin/donations/export with role='pending' token -> 403")
    headers = {"Authorization": f"Bearer {test_pending_session_token}"}
    resp = requests.get(f"{BASE_URL}/admin/donations/export", headers=headers)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    print("✅ PASS: Returns 403 with role='pending'")
    
    # 1.3: With admin token -> 200, Content-Type text/csv, Content-Disposition attachment
    print("\n1.3: GET /api/admin/donations/export with admin token -> 200")
    headers = {"Authorization": f"Bearer {test_session_token}"}
    resp = requests.get(f"{BASE_URL}/admin/donations/export", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "text/csv" in resp.headers.get("Content-Type", ""), f"Expected text/csv, got {resp.headers.get('Content-Type')}"
    assert "attachment" in resp.headers.get("Content-Disposition", ""), f"Expected attachment in Content-Disposition"
    assert "filename" in resp.headers.get("Content-Disposition", ""), f"Expected filename in Content-Disposition"
    print(f"✅ PASS: Returns 200 with Content-Type: {resp.headers.get('Content-Type')}")
    print(f"✅ PASS: Content-Disposition: {resp.headers.get('Content-Disposition')}")
    
    # 1.4: Verify CSV structure (header row + 3 data rows)
    print("\n1.4: Verify CSV structure (header row + 3 data rows)")
    csv_content = resp.text
    lines = csv_content.strip().split("\n")
    assert len(lines) == 4, f"Expected 4 lines (1 header + 3 data), got {len(lines)}"
    header = lines[0]
    assert "Date,Donor Name,Email,Amount (USD),Type,Renewal,Transaction ID" in header, f"Unexpected header: {header}"
    print(f"✅ PASS: CSV has correct header row")
    print(f"✅ PASS: CSV has 3 data rows")
    
    # Verify data rows contain expected values
    csv_body = "\n".join(lines[1:])
    assert "Jane Doe" in csv_body, "Expected 'Jane Doe' in CSV"
    assert "jane@example.com" in csv_body, "Expected 'jane@example.com' in CSV"
    assert "100.00" in csv_body, "Expected '100.00' in CSV"
    assert "25.00" in csv_body, "Expected '25.00' in CSV"
    assert "50.00" in csv_body, "Expected '50.00' in CSV"
    assert "One-Time" in csv_body, "Expected 'One-Time' in CSV"
    assert "Monthly" in csv_body, "Expected 'Monthly' in CSV"
    print(f"✅ PASS: CSV contains expected donor data")
    
    # 1.5: Test year filter (GET /api/admin/donations/export?year=2026)
    print(f"\n1.5: GET /api/admin/donations/export?year={CURRENT_YEAR} -> only rows from {CURRENT_YEAR}")
    resp = requests.get(f"{BASE_URL}/admin/donations/export?year={CURRENT_YEAR}", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    csv_content = resp.text
    lines = csv_content.strip().split("\n")
    assert len(lines) == 4, f"Expected 4 lines (1 header + 3 data from {CURRENT_YEAR}), got {len(lines)}"
    # Verify all data rows start with CURRENT_YEAR
    for line in lines[1:]:
        assert line.startswith(CURRENT_YEAR), f"Expected row to start with {CURRENT_YEAR}, got: {line}"
    print(f"✅ PASS: Year filter works correctly (all rows from {CURRENT_YEAR})")
    
    print("\n" + "="*60)
    print("✅ ALL CSV EXPORT TESTS PASSED (5/5)")
    print("="*60)

# ============ TEST 2: YEAR-END STATEMENTS ============
def test_year_end_statements():
    """Test POST /api/admin/donations/send-statements"""
    print("\n" + "="*60)
    print("TEST 2: YEAR-END STATEMENTS (POST /api/admin/donations/send-statements)")
    print("="*60)
    
    # 2.1: Without auth -> 401
    print("\n2.1: POST /api/admin/donations/send-statements without auth -> 401")
    resp = requests.post(f"{BASE_URL}/admin/donations/send-statements")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print("✅ PASS: Returns 401 without auth")
    
    # 2.2: With admin token -> 200 JSON {year, recipients, sent}
    print(f"\n2.2: POST /api/admin/donations/send-statements?year={CURRENT_YEAR} with admin token -> 200")
    headers = {"Authorization": f"Bearer {test_session_token}"}
    resp = requests.post(f"{BASE_URL}/admin/donations/send-statements?year={CURRENT_YEAR}", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "year" in data, f"Expected 'year' in response, got {data}"
    assert "recipients" in data, f"Expected 'recipients' in response, got {data}"
    assert "sent" in data, f"Expected 'sent' in response, got {data}"
    print(f"✅ PASS: Returns 200 with JSON structure: {data}")
    
    # 2.3: Verify recipients count (unique non-empty donor emails)
    # We have: jane@example.com (2 transactions), anonymous with empty email (1 transaction)
    # Expected recipients: 1 (jane@example.com)
    print(f"\n2.3: Verify recipients count (unique non-empty donor emails)")
    assert data["year"] == int(CURRENT_YEAR), f"Expected year={CURRENT_YEAR}, got {data['year']}"
    assert data["recipients"] == 1, f"Expected recipients=1 (jane@example.com), got {data['recipients']}"
    print(f"✅ PASS: recipients=1 (jane@example.com, anonymous excluded)")
    
    # 2.4: Verify 'sent' field (may be 0 if email service rejects/sandbox, but must NOT 500)
    print(f"\n2.4: Verify 'sent' field (may be 0 if email service rejects/sandbox)")
    assert isinstance(data["sent"], int), f"Expected 'sent' to be int, got {type(data['sent'])}"
    assert data["sent"] >= 0, f"Expected 'sent' >= 0, got {data['sent']}"
    print(f"✅ PASS: sent={data['sent']} (no 500 error, email service may reject in sandbox)")
    
    print("\n" + "="*60)
    print("✅ ALL YEAR-END STATEMENTS TESTS PASSED (4/4)")
    print("="*60)

# ============ TEST 3: CAMPAIGN PROGRESS ============
def test_campaign_progress():
    """Test POST /api/admin/campaign/send-progress"""
    print("\n" + "="*60)
    print("TEST 3: CAMPAIGN PROGRESS (POST /api/admin/campaign/send-progress)")
    print("="*60)
    
    # 3.1: Without auth -> 401
    print("\n3.1: POST /api/admin/campaign/send-progress without auth -> 401")
    resp = requests.post(f"{BASE_URL}/admin/campaign/send-progress", json={"message": "Test"})
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print("✅ PASS: Returns 401 without auth")
    
    # 3.2: With admin token -> 200 JSON {percent, recipients, sent}
    print(f"\n3.2: POST /api/admin/campaign/send-progress with admin token -> 200")
    headers = {"Authorization": f"Bearer {test_session_token}"}
    resp = requests.post(f"{BASE_URL}/admin/campaign/send-progress", json={"message": "Almost there!"}, headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "percent" in data, f"Expected 'percent' in response, got {data}"
    assert "recipients" in data, f"Expected 'recipients' in response, got {data}"
    assert "sent" in data, f"Expected 'sent' in response, got {data}"
    print(f"✅ PASS: Returns 200 with JSON structure: {data}")
    
    # 3.3: Verify percent calculation (total paid=175, goal=1000 -> 17%)
    print(f"\n3.3: Verify percent calculation (total paid=175, goal=1000 -> 17%)")
    # Total: 100 + 25 + 50 = 175
    # Goal: 1000
    # Percent: (175 / 1000) * 100 = 17.5 -> int(17.5) = 17
    assert data["percent"] == 17, f"Expected percent=17, got {data['percent']}"
    print(f"✅ PASS: percent=17 (175/1000)")
    
    # 3.4: Verify recipients count (unique non-empty donor emails)
    # We have: jane@example.com (2 transactions), anonymous with empty email (1 transaction)
    # Expected recipients: 1 (jane@example.com)
    print(f"\n3.4: Verify recipients count (unique non-empty donor emails)")
    assert data["recipients"] == 1, f"Expected recipients=1 (jane@example.com), got {data['recipients']}"
    print(f"✅ PASS: recipients=1 (jane@example.com, anonymous excluded)")
    
    # 3.5: Verify 'sent' field (may be 0 if email service rejects/sandbox, but must NOT 500)
    print(f"\n3.5: Verify 'sent' field (may be 0 if email service rejects/sandbox)")
    assert isinstance(data["sent"], int), f"Expected 'sent' to be int, got {type(data['sent'])}"
    assert data["sent"] >= 0, f"Expected 'sent' >= 0, got {data['sent']}"
    print(f"✅ PASS: sent={data['sent']} (no 500 error, email service may reject in sandbox)")
    
    print("\n" + "="*60)
    print("✅ ALL CAMPAIGN PROGRESS TESTS PASSED (5/5)")
    print("="*60)

# ============ MAIN ============
if __name__ == "__main__":
    try:
        print("="*60)
        print("TESTING NEW ADMIN ENDPOINTS")
        print("="*60)
        
        # Setup
        seed_admin_user()
        seed_pending_user()
        seed_payment_transactions()
        seed_campaign_settings()
        
        # Run tests
        test_csv_export()
        test_year_end_statements()
        test_campaign_progress()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED (14/14)")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise
    finally:
        cleanup()
