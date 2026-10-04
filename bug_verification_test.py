#!/usr/bin/env python3
"""
Bug Verification Test: Admin Donations and Donors Tabs
Verifies that the admin Donations and Donors tabs now display data correctly.
"""

import requests
import json
import time
from pymongo import MongoClient
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"
DB_NAME = "test_database"
MONGO_URL = "mongodb://localhost:27017"

# Test data
test_user_id = None
test_session_token = None
test_email = None

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
    """Seed an admin test user and session directly in MongoDB"""
    global test_user_id, test_session_token, test_email
    
    print_section("SETUP: Seeding Admin Test User & Session")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Generate unique identifiers
    timestamp = int(time.time() * 1000)
    test_user_id = f"user_bugtest{timestamp}"
    test_session_token = f"bugtest_session_{timestamp}"
    test_email = f"bugtest.admin.{timestamp}@example.com"
    
    # Insert test admin user
    user_doc = {
        "user_id": test_user_id,
        "email": test_email,
        "name": "Bug Test Admin",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.utcnow().isoformat()
    }
    db.users.insert_one(user_doc)
    print(f"✓ Created test admin user: {test_email}")
    
    # Insert test session (expires in 7 days)
    expires_at = datetime.utcnow() + timedelta(days=7)
    session_doc = {
        "user_id": test_user_id,
        "session_token": test_session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    db.user_sessions.insert_one(session_doc)
    print(f"✓ Created test session: {test_session_token[:30]}...")
    
    client.close()
    return test_session_token

def cleanup_test_user():
    """Remove ONLY the test user and session (NOT sample_demo data)"""
    print_section("CLEANUP: Removing Test User & Session ONLY")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Delete ONLY our test user
    result = db.users.delete_one({"user_id": test_user_id})
    print(f"✓ Deleted test user: {result.deleted_count} user(s)")
    
    # Delete ONLY our test session
    result = db.user_sessions.delete_one({"session_token": test_session_token})
    print(f"✓ Deleted test session: {result.deleted_count} session(s)")
    
    # Verify sample_demo data is still present
    sample_count = db.payment_transactions.count_documents({"source": "sample_demo"})
    print(f"✓ Verified sample_demo data intact: {sample_count} payment_transactions")
    
    client.close()

# ============================================================================
# BUG VERIFICATION TESTS
# ============================================================================

def test_admin_donations_unauthenticated():
    """Test that GET /api/admin/donations returns 401 when unauthenticated"""
    print_section("TEST 1: Admin Donations - Unauthenticated (401)")
    
    response = requests.get(f"{API_BASE}/admin/donations")
    
    passed = response.status_code == 401
    print_test(
        "GET /api/admin/donations without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_admin_donations_list():
    """Test GET /api/admin/donations returns 5 items with correct summary"""
    print_section("TEST 2: Admin Donations - List All (5 items)")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donations", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        summary = data.get('summary', {})
        
        # Check items count
        items_count_ok = len(items) == 5
        
        # Check summary fields
        total_raised = summary.get('total_raised')
        count = summary.get('count')
        monthly_count = summary.get('monthly_count')
        onetime_count = summary.get('onetime_count')
        active_recurring = summary.get('active_recurring')
        monthly_revenue = summary.get('monthly_revenue')
        
        total_raised_ok = total_raised == 525
        count_ok = count == 5
        monthly_count_ok = monthly_count == 2
        onetime_count_ok = onetime_count == 3
        active_recurring_ok = active_recurring == 1
        monthly_revenue_ok = monthly_revenue == 50
        
        all_ok = (items_count_ok and total_raised_ok and count_ok and 
                  monthly_count_ok and onetime_count_ok and 
                  active_recurring_ok and monthly_revenue_ok)
        
        if all_ok:
            passed = True
            print_test(
                "GET /api/admin/donations returns 5 items with correct summary",
                True,
                f"items: {len(items)}, total_raised: {total_raised}, count: {count}, "
                f"monthly_count: {monthly_count}, onetime_count: {onetime_count}, "
                f"active_recurring: {active_recurring}, monthly_revenue: {monthly_revenue}"
            )
        else:
            print_test(
                "GET /api/admin/donations returns 5 items with correct summary",
                False,
                f"Expected: items=5, total_raised=525, count=5, monthly_count=2, "
                f"onetime_count=3, active_recurring=1, monthly_revenue=50. "
                f"Got: items={len(items)}, total_raised={total_raised}, count={count}, "
                f"monthly_count={monthly_count}, onetime_count={onetime_count}, "
                f"active_recurring={active_recurring}, monthly_revenue={monthly_revenue}"
            )
    else:
        print_test(
            "GET /api/admin/donations returns 5 items with correct summary",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_admin_donations_filter_monthly():
    """Test GET /api/admin/donations?frequency=monthly returns 2 items"""
    print_section("TEST 3: Admin Donations - Filter Monthly (2 items)")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donations?frequency=monthly", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        
        # Check that we have exactly 2 monthly items
        if len(items) == 2:
            # Verify all items are monthly
            all_monthly = all(item.get('frequency') == 'monthly' for item in items)
            if all_monthly:
                passed = True
                print_test(
                    "GET /api/admin/donations?frequency=monthly returns 2 monthly items",
                    True,
                    f"Found {len(items)} monthly donations"
                )
            else:
                print_test(
                    "GET /api/admin/donations?frequency=monthly returns 2 monthly items",
                    False,
                    f"Not all items are monthly: {[item.get('frequency') for item in items]}"
                )
        else:
            print_test(
                "GET /api/admin/donations?frequency=monthly returns 2 monthly items",
                False,
                f"Expected 2 items, got {len(items)}"
            )
    else:
        print_test(
            "GET /api/admin/donations?frequency=monthly returns 2 monthly items",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_admin_donors_unauthenticated():
    """Test that GET /api/admin/donors returns 401 when unauthenticated"""
    print_section("TEST 4: Admin Donors - Unauthenticated (401)")
    
    response = requests.get(f"{API_BASE}/admin/donors")
    
    passed = response.status_code == 401
    print_test(
        "GET /api/admin/donors without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_admin_donors_list():
    """Test GET /api/admin/donors returns correct donor profiles"""
    print_section("TEST 5: Admin Donors - List All Profiles")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donors", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        donors = data.get('donors', [])
        count = data.get('count')
        
        # Find specific donors
        louise = next((d for d in donors if d.get('email') == 'louise@example.com'), None)
        adaeze = next((d for d in donors if d.get('email') == 'adaeze@example.com'), None)
        chantal = next((d for d in donors if d.get('email') == 'chantal@example.com'), None)
        grace = next((d for d in donors if d.get('email') == ''), None)  # anonymous
        
        # Verify Louise
        louise_ok = (louise and 
                     louise.get('lifetime') == 100 and 
                     louise.get('gifts') == 2 and 
                     louise.get('has_monthly') == True)
        
        # Verify Adaeze
        adaeze_ok = (adaeze and adaeze.get('lifetime') == 250)
        
        # Verify Chantal
        chantal_ok = (chantal and chantal.get('lifetime') == 100)
        
        # Verify Grace (anonymous)
        grace_ok = (grace and grace.get('email') == '')
        
        # Verify sorted by lifetime descending (Adaeze first with 250)
        sorted_ok = donors[0].get('lifetime') == 250 if donors else False
        
        all_ok = louise_ok and adaeze_ok and chantal_ok and grace_ok and sorted_ok
        
        if all_ok:
            passed = True
            print_test(
                "GET /api/admin/donors returns correct donor profiles",
                True,
                f"Louise: lifetime=100, gifts=2, has_monthly=true ✓ | "
                f"Adaeze: lifetime=250 ✓ | Chantal: lifetime=100 ✓ | "
                f"Grace: anonymous (empty email) ✓ | Sorted by lifetime desc ✓"
            )
        else:
            print_test(
                "GET /api/admin/donors returns correct donor profiles",
                False,
                f"Louise OK: {louise_ok} (data: {louise}) | "
                f"Adaeze OK: {adaeze_ok} (data: {adaeze}) | "
                f"Chantal OK: {chantal_ok} (data: {chantal}) | "
                f"Grace OK: {grace_ok} (data: {grace}) | "
                f"Sorted OK: {sorted_ok}"
            )
    else:
        print_test(
            "GET /api/admin/donors returns correct donor profiles",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_admin_donor_detail():
    """Test GET /api/admin/donors/louise@example.com returns correct detail"""
    print_section("TEST 6: Admin Donor Detail - Louise")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donors/louise@example.com", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        
        email = data.get('email')
        lifetime = data.get('lifetime')
        gift_count = data.get('gift_count')
        
        email_ok = email == 'louise@example.com'
        lifetime_ok = lifetime == 100
        gift_count_ok = gift_count == 2
        
        all_ok = email_ok and lifetime_ok and gift_count_ok
        
        if all_ok:
            passed = True
            print_test(
                "GET /api/admin/donors/louise@example.com returns correct detail",
                True,
                f"email: {email}, lifetime: {lifetime}, gift_count: {gift_count}"
            )
        else:
            print_test(
                "GET /api/admin/donors/louise@example.com returns correct detail",
                False,
                f"Expected: email=louise@example.com, lifetime=100, gift_count=2. "
                f"Got: email={email}, lifetime={lifetime}, gift_count={gift_count}"
            )
    else:
        print_test(
            "GET /api/admin/donors/louise@example.com returns correct detail",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_donations_public():
    """Test GET /api/donations/public returns correct public data"""
    print_section("TEST 7: Donations Public - Total Raised & Donor Count")
    
    response = requests.get(f"{API_BASE}/donations/public")
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        
        total_raised = data.get('total_raised')
        donor_count = data.get('donor_count')
        recent = data.get('recent', [])
        
        total_raised_ok = total_raised == 525
        donor_count_ok = donor_count == 5
        recent_ok = isinstance(recent, list) and len(recent) > 0
        
        all_ok = total_raised_ok and donor_count_ok and recent_ok
        
        if all_ok:
            passed = True
            print_test(
                "GET /api/donations/public returns correct data",
                True,
                f"total_raised: {total_raised}, donor_count: {donor_count}, "
                f"recent: {len(recent)} items"
            )
        else:
            print_test(
                "GET /api/donations/public returns correct data",
                False,
                f"Expected: total_raised=525, donor_count=5, recent array present. "
                f"Got: total_raised={total_raised}, donor_count={donor_count}, "
                f"recent={len(recent) if isinstance(recent, list) else 'not a list'}"
            )
    else:
        print_test(
            "GET /api/donations/public returns correct data",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all bug verification tests"""
    print("\n" + "="*70)
    print("  BUG VERIFICATION: Admin Donations & Donors Tabs")
    print("="*70)
    
    results = {}
    
    try:
        # Setup
        seed_admin_user()
        
        # Run tests
        results['admin_donations_unauth'] = test_admin_donations_unauthenticated()
        results['admin_donations_list'] = test_admin_donations_list()
        results['admin_donations_filter_monthly'] = test_admin_donations_filter_monthly()
        results['admin_donors_unauth'] = test_admin_donors_unauthenticated()
        results['admin_donors_list'] = test_admin_donors_list()
        results['admin_donor_detail'] = test_admin_donor_detail()
        results['donations_public'] = test_donations_public()
        
    finally:
        # Cleanup (ONLY test user, NOT sample_demo data)
        cleanup_test_user()
    
    # Summary
    print_section("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%\n")
    
    if failed > 0:
        print("Failed Tests:")
        for test_name, result in results.items():
            if not result:
                print(f"  - {test_name}")
        print()
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
