#!/usr/bin/env python3
"""
Test script for NEW backend features:
1. Campaign deadline setting/clearing
2. Recurring metrics (active_recurring, monthly_revenue)
3. No 500 errors with milestone logic
"""
import requests
import time
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

# Configuration
BASE_URL = "http://localhost:8001/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Test data
USER_ID = f"test_user_{int(time.time())}"
SESSION_TOKEN = f"test_session_{int(time.time())}"
TEST_EMAIL = f"test.admin.{int(time.time())}@example.com"

def setup_auth():
    """Seed admin user and session per auth_testing.md pattern"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Insert test user with role='admin'
    db.users.insert_one({
        "user_id": USER_ID,
        "email": TEST_EMAIL,
        "name": "Test Admin",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Insert session token
    db.user_sessions.insert_one({
        "user_id": USER_ID,
        "session_token": SESSION_TOKEN,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    client.close()
    print(f"✓ Seeded admin user: {TEST_EMAIL}")
    print(f"✓ Session token: {SESSION_TOKEN}")
    return SESSION_TOKEN

def cleanup():
    """Clean up all seeded test data"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Delete test user and session
    db.users.delete_many({"email": TEST_EMAIL})
    db.user_sessions.delete_many({"session_token": SESSION_TOKEN})
    
    # Delete ALL payment transactions (test database, safe to clear all)
    db.payment_transactions.delete_many({})
    
    # Delete test settings
    db.settings.delete_one({"key": "site"})
    
    # Delete test milestones
    db.milestones_sent.delete_many({})
    
    client.close()
    print("\n✓ Cleaned up all test data from MongoDB")

def test_deadline_setting():
    """Test 1: Campaign deadline setting and retrieval"""
    print("\n=== TEST 1: CAMPAIGN DEADLINE ===")
    headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}
    
    # 1a. Set deadline to 2026-12-31
    print("\n1a. PUT /api/admin/settings with deadline='2026-12-31'")
    resp = requests.put(
        f"{BASE_URL}/admin/settings",
        json={"deadline": "2026-12-31"},
        headers=headers
    )
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response deadline: {data.get('deadline')}")
        assert data.get("deadline") == "2026-12-31", f"Expected deadline='2026-12-31', got {data.get('deadline')}"
        print("   ✅ PASS: Deadline set to 2026-12-31")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False
    
    # 1b. GET /api/settings includes deadline
    print("\n1b. GET /api/settings includes deadline='2026-12-31'")
    resp = requests.get(f"{BASE_URL}/settings")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response deadline: {data.get('deadline')}")
        assert data.get("deadline") == "2026-12-31", f"Expected deadline='2026-12-31', got {data.get('deadline')}"
        print("   ✅ PASS: GET /api/settings includes deadline='2026-12-31'")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        return False
    
    # 1c. GET /api/donations/public includes deadline
    print("\n1c. GET /api/donations/public includes deadline='2026-12-31'")
    resp = requests.get(f"{BASE_URL}/donations/public")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response deadline: {data.get('deadline')}")
        assert data.get("deadline") == "2026-12-31", f"Expected deadline='2026-12-31', got {data.get('deadline')}"
        print("   ✅ PASS: GET /api/donations/public includes deadline='2026-12-31'")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        return False
    
    # 1d. Clear deadline (set to empty string)
    print("\n1d. PUT /api/admin/settings with deadline='' (clear)")
    resp = requests.put(
        f"{BASE_URL}/admin/settings",
        json={"deadline": ""},
        headers=headers
    )
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response deadline: {data.get('deadline')}")
        assert data.get("deadline") is None, f"Expected deadline=None, got {data.get('deadline')}"
        print("   ✅ PASS: Deadline cleared (None)")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        return False
    
    # 1e. Verify deadline is None in GET /api/settings
    print("\n1e. GET /api/settings shows deadline=None after clearing")
    resp = requests.get(f"{BASE_URL}/settings")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response deadline: {data.get('deadline')}")
        assert data.get("deadline") is None, f"Expected deadline=None, got {data.get('deadline')}"
        print("   ✅ PASS: GET /api/settings shows deadline=None")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        return False
    
    print("\n✅ ALL DEADLINE TESTS PASSED (5/5)")
    return True

def test_recurring_metrics():
    """Test 2: Recurring metrics in GET /api/admin/donations"""
    print("\n=== TEST 2: RECURRING METRICS ===")
    headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}
    
    # Seed payment transactions
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Transaction (a): monthly, amount=25, stripe_subscription_id="sub_A"
    db.payment_transactions.insert_one({
        "id": f"txn_a_{int(time.time())}",
        "amount": 25,
        "frequency": "monthly",
        "stripe_subscription_id": "sub_A",
        "payment_status": "paid",
        "donor_name": "Alice Monthly",
        "donor_email": "test_deadline_alice@example.com",
        "updated_at": now_iso,
        "created_at": now_iso,
    })
    
    # Transaction (b): monthly, amount=25, stripe_subscription_id="sub_A", is_renewal=true
    db.payment_transactions.insert_one({
        "id": f"txn_b_{int(time.time())}",
        "amount": 25,
        "frequency": "monthly",
        "stripe_subscription_id": "sub_A",
        "is_renewal": True,
        "payment_status": "paid",
        "donor_name": "Alice Monthly",
        "donor_email": "test_deadline_alice@example.com",
        "updated_at": now_iso,
        "created_at": now_iso,
    })
    
    # Transaction (c): one-time, amount=100
    db.payment_transactions.insert_one({
        "id": f"txn_c_{int(time.time())}",
        "amount": 100,
        "frequency": "one-time",
        "payment_status": "paid",
        "donor_name": "Bob Onetime",
        "donor_email": "test_deadline_bob@example.com",
        "updated_at": now_iso,
        "created_at": now_iso,
    })
    
    client.close()
    print("✓ Seeded 3 payment_transactions:")
    print("  (a) monthly, amount=25, stripe_subscription_id='sub_A'")
    print("  (b) monthly, amount=25, stripe_subscription_id='sub_A', is_renewal=true")
    print("  (c) one-time, amount=100")
    
    # 2a. GET /api/admin/donations and verify summary
    print("\n2a. GET /api/admin/donations - verify summary metrics")
    resp = requests.get(f"{BASE_URL}/admin/donations", headers=headers)
    print(f"   Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        summary = data.get("summary", {})
        items = data.get("items", [])
        
        print(f"   summary.total_raised: {summary.get('total_raised')}")
        print(f"   summary.monthly_count: {summary.get('monthly_count')}")
        print(f"   summary.onetime_count: {summary.get('onetime_count')}")
        print(f"   summary.active_recurring: {summary.get('active_recurring')}")
        print(f"   summary.monthly_revenue: {summary.get('monthly_revenue')}")
        print(f"\n   DEBUG: Found {len(items)} paid transactions:")
        for i, item in enumerate(items):
            print(f"      [{i+1}] amount={item.get('amount')}, frequency={item.get('frequency')}, "
                  f"donor_email={item.get('donor_email')}, stripe_subscription_id={item.get('stripe_subscription_id')}, "
                  f"is_renewal={item.get('is_renewal')}")
        
        # Verify totals
        assert summary.get("total_raised") == 150, f"Expected total_raised=150, got {summary.get('total_raised')}"
        assert summary.get("monthly_count") == 2, f"Expected monthly_count=2, got {summary.get('monthly_count')}"
        assert summary.get("onetime_count") == 1, f"Expected onetime_count=1, got {summary.get('onetime_count')}"
        
        # Verify active_recurring = 1 (unique subscription sub_A)
        assert summary.get("active_recurring") == 1, f"Expected active_recurring=1 (unique sub_A), got {summary.get('active_recurring')}"
        
        # Verify monthly_revenue = 25 (ONE gift per active subscription, not both renewals)
        assert summary.get("monthly_revenue") == 25, f"Expected monthly_revenue=25 (one gift per subscription), got {summary.get('monthly_revenue')}"
        
        print("   ✅ PASS: All metrics correct")
        print("      - total_raised = 150 ✓")
        print("      - monthly_count = 2 ✓")
        print("      - onetime_count = 1 ✓")
        print("      - active_recurring = 1 (unique subscription sub_A) ✓")
        print("      - monthly_revenue = 25 (ONE gift per subscription) ✓")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False
    
    print("\n✅ ALL RECURRING METRICS TESTS PASSED (1/1)")
    return True

def test_no_500_milestones():
    """Test 3: No 500 errors when milestone logic runs"""
    print("\n=== TEST 3: NO 500 ERRORS / MILESTONES ===")
    headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}
    
    # 3a. Set goal to 100
    print("\n3a. PUT /api/admin/settings with goal=100")
    resp = requests.put(
        f"{BASE_URL}/admin/settings",
        json={"goal": 100},
        headers=headers
    )
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response goal: {data.get('goal')}")
        assert data.get("goal") == 100, f"Expected goal=100, got {data.get('goal')}"
        print("   ✅ PASS: Goal set to 100")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        return False
    
    # 3b. Seed a paid one-time donation amount=60
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    now_iso = datetime.now(timezone.utc).isoformat()
    db.payment_transactions.insert_one({
        "id": f"txn_milestone_{int(time.time())}",
        "amount": 60,
        "frequency": "one-time",
        "payment_status": "paid",
        "donor_name": "Charlie Milestone",
        "donor_email": "test_deadline_charlie@example.com",
        "updated_at": now_iso,
        "created_at": now_iso,
    })
    
    client.close()
    print("✓ Seeded paid one-time donation: amount=60")
    
    # 3c. GET /api/donations/public - should return 200 (no 500)
    print("\n3c. GET /api/donations/public - verify no 500 error")
    resp = requests.get(f"{BASE_URL}/donations/public")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   total_raised: {data.get('total_raised')}")
        print(f"   goal: {data.get('goal')}")
        print("   ✅ PASS: GET /api/donations/public returns 200 (no 500)")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False
    
    # 3d. GET /api/admin/donations - should return 200 (no 500)
    print("\n3d. GET /api/admin/donations - verify no 500 error")
    resp = requests.get(f"{BASE_URL}/admin/donations", headers=headers)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        summary = data.get("summary", {})
        print(f"   summary.total_raised: {summary.get('total_raised')}")
        print("   ✅ PASS: GET /api/admin/donations returns 200 (no 500)")
    else:
        print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False
    
    print("\n✅ ALL NO-500 / MILESTONE TESTS PASSED (4/4)")
    print("   Note: Milestone emails fire only on live paid-donation recording")
    print("   which can't be triggered headlessly. Endpoints are healthy.")
    return True

def main():
    print("=" * 60)
    print("BACKEND TEST: Deadline, Recurring Metrics, Milestones")
    print("=" * 60)
    
    # Clean up any leftover data from previous runs first
    print("\nCleaning up any leftover data from previous runs...")
    cleanup()
    
    try:
        # Setup
        setup_auth()
        
        # Run tests
        test1_pass = test_deadline_setting()
        test2_pass = test_recurring_metrics()
        test3_pass = test_no_500_milestones()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"1. Campaign Deadline: {'✅ PASS' if test1_pass else '❌ FAIL'}")
        print(f"2. Recurring Metrics: {'✅ PASS' if test2_pass else '❌ FAIL'}")
        print(f"3. No 500 / Milestones: {'✅ PASS' if test3_pass else '❌ FAIL'}")
        
        all_pass = test1_pass and test2_pass and test3_pass
        if all_pass:
            print("\n🎉 ALL TESTS PASSED (10/10)")
        else:
            print("\n❌ SOME TESTS FAILED")
        
        return all_pass
        
    finally:
        # Cleanup
        cleanup()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
