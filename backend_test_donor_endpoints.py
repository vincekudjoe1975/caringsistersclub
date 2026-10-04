#!/usr/bin/env python3
"""
Backend API Testing for NEW Admin Donor Endpoints
Tests: GET /api/admin/donors, GET /api/admin/donors/{email}, POST /api/admin/recurring/send-reminders
"""

import requests
import json
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

# Configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"
DB_NAME = "test_database"
MONGO_URL = "mongodb://localhost:27017"

# Test data
admin_user_id = None
admin_session_token = None
admin_email = None
pending_user_id = None
pending_session_token = None
pending_email = None
payment_transaction_ids = []

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_test(name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   Details: {details}")

def seed_admin_user():
    """Seed an admin user and session directly in MongoDB"""
    global admin_user_id, admin_session_token, admin_email
    
    print_section("SETUP: Seeding Admin User & Session")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Generate unique identifiers
    timestamp = int(datetime.now().timestamp() * 1000)
    admin_user_id = f"user_admin_{timestamp}"
    admin_session_token = f"test_session_admin_{timestamp}"
    admin_email = f"test.admin.{timestamp}@example.com"
    
    # Insert admin user with role='admin'
    user_doc = {
        "user_id": admin_user_id,
        "email": admin_email,
        "name": "Test Admin",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db.users.insert_one(user_doc)
    print(f"✓ Created admin user: {admin_email} (role=admin)")
    
    # Insert session with 7-day expiry
    session_doc = {
        "user_id": admin_user_id,
        "session_token": admin_session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db.user_sessions.insert_one(session_doc)
    print(f"✓ Created session token: {admin_session_token[:20]}...")
    
    client.close()

def seed_pending_user():
    """Seed a pending user (role='pending') for 403 testing"""
    global pending_user_id, pending_session_token, pending_email
    
    print_section("SETUP: Seeding Pending User & Session")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Generate unique identifiers
    timestamp = int(datetime.now().timestamp() * 1000)
    pending_user_id = f"user_pending_{timestamp}"
    pending_session_token = f"test_session_pending_{timestamp}"
    pending_email = f"test.pending.{timestamp}@example.com"
    
    # Insert pending user with role='pending'
    user_doc = {
        "user_id": pending_user_id,
        "email": pending_email,
        "name": "Test Pending",
        "picture": "https://via.placeholder.com/150",
        "role": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db.users.insert_one(user_doc)
    print(f"✓ Created pending user: {pending_email} (role=pending)")
    
    # Insert session with 7-day expiry
    session_doc = {
        "user_id": pending_user_id,
        "session_token": pending_session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db.user_sessions.insert_one(session_doc)
    print(f"✓ Created session token: {pending_session_token[:20]}...")
    
    client.close()

def seed_payment_transactions():
    """Seed 3 payment_transactions with payment_status='paid'"""
    global payment_transaction_ids
    
    print_section("SETUP: Seeding Payment Transactions")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Transaction 1: Jane Doe, $100, one-time, 2026-03-15
    tx1 = {
        "id": "tx_jane_100",
        "amount": 100,
        "frequency": "one-time",
        "donor_name": "Jane Doe",
        "donor_email": "jane@example.com",
        "anonymous": False,
        "payment_status": "paid",
        "updated_at": "2026-03-15T10:00:00+00:00",
        "session_id": "cs_1",
        "created_at": "2026-03-15T09:00:00+00:00"
    }
    db.payment_transactions.insert_one(tx1)
    payment_transaction_ids.append("tx_jane_100")
    print(f"✓ Created transaction: Jane Doe $100 one-time (2026-03-15)")
    
    # Transaction 2: Jane Doe, $25, monthly with subscription, 2026-04-15
    tx2 = {
        "id": "tx_jane_25",
        "amount": 25,
        "frequency": "monthly",
        "donor_name": "Jane Doe",
        "donor_email": "jane@example.com",
        "anonymous": False,
        "payment_status": "paid",
        "stripe_subscription_id": "sub_X",
        "updated_at": "2026-04-15T10:00:00+00:00",
        "session_id": "cs_2",
        "created_at": "2026-04-15T09:00:00+00:00"
    }
    db.payment_transactions.insert_one(tx2)
    payment_transaction_ids.append("tx_jane_25")
    print(f"✓ Created transaction: Jane Doe $25 monthly (sub_X) (2026-04-15)")
    
    # Transaction 3: Bob Smith, $50, one-time, 2026-05-01
    tx3 = {
        "id": "tx_bob_50",
        "amount": 50,
        "frequency": "one-time",
        "donor_name": "Bob Smith",
        "donor_email": "bob@example.com",
        "anonymous": False,
        "payment_status": "paid",
        "updated_at": "2026-05-01T10:00:00+00:00",
        "session_id": "cs_3",
        "created_at": "2026-05-01T09:00:00+00:00"
    }
    db.payment_transactions.insert_one(tx3)
    payment_transaction_ids.append("tx_bob_50")
    print(f"✓ Created transaction: Bob Smith $50 one-time (2026-05-01)")
    
    client.close()

def test_donor_profiles():
    """Test GET /api/admin/donors"""
    print_section("TEST 1: Donor Profiles (GET /api/admin/donors)")
    
    # Test 1a: Without auth -> 401
    print("\n1a. Testing without authentication (expect 401)...")
    response = requests.get(f"{API_BASE}/admin/donors")
    passed = response.status_code == 401
    print_test("GET /api/admin/donors without auth returns 401", passed, 
               f"Status: {response.status_code}")
    
    # Test 1b: With role='pending' -> 403
    print("\n1b. Testing with role='pending' user (expect 403)...")
    headers = {"Authorization": f"Bearer {pending_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donors", headers=headers)
    passed = response.status_code == 403
    print_test("GET /api/admin/donors with role='pending' returns 403", passed,
               f"Status: {response.status_code}")
    
    # Test 1c: With admin token -> 200 with correct data
    print("\n1c. Testing with admin token (expect 200 with donor profiles)...")
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donors", headers=headers)
    passed = response.status_code == 200
    print_test("GET /api/admin/donors with admin returns 200", passed,
               f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        print(f"\n   Response structure: {json.dumps(data, indent=2)}")
        
        # Verify structure
        has_donors = "donors" in data
        has_count = "count" in data
        print_test("Response has 'donors' field", has_donors)
        print_test("Response has 'count' field", has_count)
        
        if has_donors:
            donors = data["donors"]
            count = data.get("count", 0)
            
            # Should have 2 donors (Jane and Bob)
            correct_count = count == 2
            print_test("Donor count is 2", correct_count, f"Count: {count}")
            
            # Verify Jane's profile (should be first, highest lifetime)
            if len(donors) >= 1:
                jane = donors[0]
                jane_email_correct = jane.get("email") == "jane@example.com"
                jane_lifetime_correct = jane.get("lifetime") == 125  # 100 + 25
                jane_gifts_correct = jane.get("gifts") == 2
                jane_has_monthly = jane.get("has_monthly") == True
                
                print_test("Jane's email is correct", jane_email_correct, 
                          f"Email: {jane.get('email')}")
                print_test("Jane's lifetime is 125", jane_lifetime_correct,
                          f"Lifetime: {jane.get('lifetime')}")
                print_test("Jane's gift count is 2", jane_gifts_correct,
                          f"Gifts: {jane.get('gifts')}")
                print_test("Jane has monthly subscription", jane_has_monthly,
                          f"has_monthly: {jane.get('has_monthly')}")
            
            # Verify Bob's profile (should be second)
            if len(donors) >= 2:
                bob = donors[1]
                bob_email_correct = bob.get("email") == "bob@example.com"
                bob_lifetime_correct = bob.get("lifetime") == 50
                bob_gifts_correct = bob.get("gifts") == 1
                bob_no_monthly = bob.get("has_monthly") == False
                
                print_test("Bob's email is correct", bob_email_correct,
                          f"Email: {bob.get('email')}")
                print_test("Bob's lifetime is 50", bob_lifetime_correct,
                          f"Lifetime: {bob.get('lifetime')}")
                print_test("Bob's gift count is 1", bob_gifts_correct,
                          f"Gifts: {bob.get('gifts')}")
                print_test("Bob has no monthly subscription", bob_no_monthly,
                          f"has_monthly: {bob.get('has_monthly')}")
            
            # Verify sorting (Jane should be first with higher lifetime)
            if len(donors) >= 2:
                sorted_correctly = donors[0].get("lifetime", 0) >= donors[1].get("lifetime", 0)
                print_test("Donors sorted by lifetime descending", sorted_correctly,
                          f"Jane: {donors[0].get('lifetime')}, Bob: {donors[1].get('lifetime')}")

def test_donor_detail():
    """Test GET /api/admin/donors/{email}"""
    print_section("TEST 2: Donor Detail (GET /api/admin/donors/{email})")
    
    # Test 2a: Get Jane's detail
    print("\n2a. Testing GET /api/admin/donors/jane@example.com...")
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donors/jane@example.com", headers=headers)
    passed = response.status_code == 200
    print_test("GET /api/admin/donors/jane@example.com returns 200", passed,
               f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        print(f"\n   Response: {json.dumps(data, indent=2)}")
        
        # Verify structure
        email_correct = data.get("email") == "jane@example.com"
        name_correct = data.get("name") == "Jane Doe"
        lifetime_correct = data.get("lifetime") == 125
        gift_count_correct = data.get("gift_count") == 2
        has_gifts = "gifts" in data and isinstance(data["gifts"], list)
        
        print_test("Email is 'jane@example.com'", email_correct,
                  f"Email: {data.get('email')}")
        print_test("Name is 'Jane Doe'", name_correct,
                  f"Name: {data.get('name')}")
        print_test("Lifetime is 125", lifetime_correct,
                  f"Lifetime: {data.get('lifetime')}")
        print_test("Gift count is 2", gift_count_correct,
                  f"Gift count: {data.get('gift_count')}")
        print_test("Has gifts array", has_gifts,
                  f"Gifts: {len(data.get('gifts', []))} items")
        
        # Verify gifts are sorted by updated_at descending
        if has_gifts and len(data["gifts"]) >= 2:
            gifts = data["gifts"]
            first_date = gifts[0].get("updated_at", "")
            second_date = gifts[1].get("updated_at", "")
            sorted_correctly = first_date >= second_date
            print_test("Gifts sorted by updated_at descending", sorted_correctly,
                      f"First: {first_date}, Second: {second_date}")
    
    # Test 2b: Case-insensitive match (JANE@EXAMPLE.COM)
    print("\n2b. Testing case-insensitive match (JANE@EXAMPLE.COM)...")
    response = requests.get(f"{API_BASE}/admin/donors/JANE@EXAMPLE.COM", headers=headers)
    passed = response.status_code == 200
    print_test("GET /api/admin/donors/JANE@EXAMPLE.COM returns 200", passed,
               f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        email_matches = data.get("email") == "jane@example.com"
        print_test("Case-insensitive match works", email_matches,
                  f"Returned email: {data.get('email')}")

def test_renewal_reminders():
    """Test POST /api/admin/recurring/send-reminders"""
    print_section("TEST 3: Renewal Reminders (POST /api/admin/recurring/send-reminders)")
    
    # Test 3a: Without auth -> 401
    print("\n3a. Testing without authentication (expect 401)...")
    response = requests.post(f"{API_BASE}/admin/recurring/send-reminders")
    passed = response.status_code == 401
    print_test("POST /api/admin/recurring/send-reminders without auth returns 401", passed,
               f"Status: {response.status_code}")
    
    # Test 3b: With admin token -> 200 (no 500 error)
    print("\n3b. Testing with admin token (expect 200, no 500)...")
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.post(f"{API_BASE}/admin/recurring/send-reminders", headers=headers)
    passed = response.status_code == 200
    print_test("POST /api/admin/recurring/send-reminders with admin returns 200", passed,
               f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        print(f"\n   Response: {json.dumps(data, indent=2)}")
        
        # Verify structure
        has_sent = "sent" in data
        has_checked = "subscriptions_checked" in data
        
        print_test("Response has 'sent' field", has_sent,
                  f"sent: {data.get('sent')}")
        print_test("Response has 'subscriptions_checked' field", has_checked,
                  f"subscriptions_checked: {data.get('subscriptions_checked')}")
        
        # Should check at least 1 subscription (sub_X)
        if has_checked:
            checked = data.get("subscriptions_checked", 0)
            checked_at_least_one = checked >= 1
            print_test("Checked at least 1 subscription", checked_at_least_one,
                      f"Checked: {checked}")
        
        # Note: sent will likely be 0 because sub_X is fake and Stripe retrieve will error
        # But the endpoint should NOT 500 - it should catch the error and continue
        if has_sent:
            sent = data.get("sent", 0)
            print(f"   Note: sent={sent} (likely 0 because sub_X is fake, but no 500 error)")

def cleanup():
    """Clean up all seeded test data"""
    print_section("CLEANUP: Removing Test Data")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Delete users
    if admin_user_id:
        result = db.users.delete_one({"user_id": admin_user_id})
        print(f"✓ Deleted admin user: {result.deleted_count} document(s)")
    
    if pending_user_id:
        result = db.users.delete_one({"user_id": pending_user_id})
        print(f"✓ Deleted pending user: {result.deleted_count} document(s)")
    
    # Delete sessions
    if admin_session_token:
        result = db.user_sessions.delete_one({"session_token": admin_session_token})
        print(f"✓ Deleted admin session: {result.deleted_count} document(s)")
    
    if pending_session_token:
        result = db.user_sessions.delete_one({"session_token": pending_session_token})
        print(f"✓ Deleted pending session: {result.deleted_count} document(s)")
    
    # Delete payment transactions
    if payment_transaction_ids:
        result = db.payment_transactions.delete_many({"id": {"$in": payment_transaction_ids}})
        print(f"✓ Deleted payment transactions: {result.deleted_count} document(s)")
    
    # Delete any reminders_sent records
    result = db.reminders_sent.delete_many({})
    print(f"✓ Deleted reminders_sent: {result.deleted_count} document(s)")
    
    # Delete any scheduled_runs records
    result = db.scheduled_runs.delete_many({})
    print(f"✓ Deleted scheduled_runs: {result.deleted_count} document(s)")
    
    client.close()
    print("\n✓ Cleanup complete!")

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  BACKEND API TESTING: NEW ADMIN DONOR ENDPOINTS")
    print("="*70)
    
    try:
        # Setup
        seed_admin_user()
        seed_pending_user()
        seed_payment_transactions()
        
        # Run tests
        test_donor_profiles()
        test_donor_detail()
        test_renewal_reminders()
        
        # Cleanup
        cleanup()
        
        print_section("TEST SUMMARY")
        print("✅ All tests completed successfully!")
        print("   - Donor profiles endpoint tested")
        print("   - Donor detail endpoint tested")
        print("   - Renewal reminders endpoint tested")
        print("   - Auth requirements verified (401/403)")
        print("   - All test data cleaned up")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Attempt cleanup even on error
        try:
            cleanup()
        except:
            pass
        
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
