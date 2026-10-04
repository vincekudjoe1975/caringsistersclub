#!/usr/bin/env python3
"""
Backend API Testing for Caring Sisters Club - New Features
Tests: Role Enforcement, Team Management, Donor Wall, Admin Donations
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
admin_user_id = None
admin_session_token = None
admin_email = None
pending_user_id = None
pending_session_token = None
pending_email = None
other_user_id = None
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

def seed_test_users():
    """Seed test users with different roles"""
    global admin_user_id, admin_session_token, admin_email
    global pending_user_id, pending_session_token, pending_email
    global other_user_id
    
    print_section("SETUP: Seeding Test Users & Sessions")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    timestamp = int(time.time() * 1000)
    
    # Create admin user
    admin_user_id = f"user_admin_{timestamp}"
    admin_session_token = f"test_session_admin_{timestamp}"
    admin_email = f"test.admin.{timestamp}@example.com"
    
    admin_user_doc = {
        "user_id": admin_user_id,
        "email": admin_email,
        "name": "Test Admin",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.utcnow().isoformat()
    }
    db.users.insert_one(admin_user_doc)
    print(f"✓ Created admin user: {admin_email}")
    
    expires_at = datetime.utcnow() + timedelta(days=7)
    admin_session_doc = {
        "user_id": admin_user_id,
        "session_token": admin_session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    db.user_sessions.insert_one(admin_session_doc)
    print(f"✓ Created admin session: {admin_session_token[:20]}...")
    
    # Create pending user
    pending_user_id = f"user_pending_{timestamp}"
    pending_session_token = f"test_session_pending_{timestamp}"
    pending_email = f"test.pending.{timestamp}@example.com"
    
    pending_user_doc = {
        "user_id": pending_user_id,
        "email": pending_email,
        "name": "Test Pending User",
        "picture": "https://via.placeholder.com/150",
        "role": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    db.users.insert_one(pending_user_doc)
    print(f"✓ Created pending user: {pending_email}")
    
    pending_session_doc = {
        "user_id": pending_user_id,
        "session_token": pending_session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    db.user_sessions.insert_one(pending_session_doc)
    print(f"✓ Created pending session: {pending_session_token[:20]}...")
    
    # Create another user for role update tests
    other_user_id = f"user_other_{timestamp}"
    other_user_doc = {
        "user_id": other_user_id,
        "email": f"test.other.{timestamp}@example.com",
        "name": "Test Other User",
        "picture": "https://via.placeholder.com/150",
        "role": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    db.users.insert_one(other_user_doc)
    print(f"✓ Created other user: {other_user_doc['email']}")
    
    client.close()

def seed_donor_data():
    """Seed payment transactions for donor wall testing"""
    print_section("SETUP: Seeding Donor Data")
    
    global payment_transaction_ids
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    now = datetime.utcnow().isoformat()
    
    # Seed paid donation 1: non-anonymous
    txn1 = {
        "session_id": f"cs_test_donor1_{int(time.time() * 1000)}",
        "amount": 100.0,
        "currency": "usd",
        "frequency": "one-time",
        "donor_name": "Jane Doe",
        "donor_email": "jane@example.com",
        "anonymous": False,
        "status": "completed",
        "payment_status": "paid",
        "created_at": now,
        "updated_at": now,
    }
    result1 = db.payment_transactions.insert_one(txn1)
    payment_transaction_ids.append(txn1["session_id"])
    print(f"✓ Seeded paid donation 1: $100 one-time, Jane Doe (non-anonymous)")
    
    # Seed paid donation 2: anonymous monthly
    txn2 = {
        "session_id": f"cs_test_donor2_{int(time.time() * 1000)}",
        "amount": 25.0,
        "currency": "usd",
        "frequency": "monthly",
        "donor_name": "Secret Giver",
        "donor_email": "secret@example.com",
        "anonymous": True,
        "status": "completed",
        "payment_status": "paid",
        "created_at": now,
        "updated_at": now,
    }
    result2 = db.payment_transactions.insert_one(txn2)
    payment_transaction_ids.append(txn2["session_id"])
    print(f"✓ Seeded paid donation 2: $25 monthly, Secret Giver (anonymous)")
    
    client.close()

def cleanup_test_data():
    """Remove all test data from MongoDB"""
    print_section("CLEANUP: Removing Test Data")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Delete test users
    result = db.users.delete_many({"email": {"$regex": "test\\.(admin|pending|other)\\."}})
    print(f"✓ Deleted {result.deleted_count} test user(s)")
    
    # Delete test sessions
    result = db.user_sessions.delete_many({"session_token": {"$regex": "test_session"}})
    print(f"✓ Deleted {result.deleted_count} test session(s)")
    
    # Delete test payment transactions
    if payment_transaction_ids:
        result = db.payment_transactions.delete_many({"session_id": {"$in": payment_transaction_ids}})
        print(f"✓ Deleted {result.deleted_count} test payment transaction(s)")
    
    # Delete test allowed_emails
    result = db.allowed_emails.delete_many({"email": {"$regex": "newperson@example\\.com"}})
    print(f"✓ Deleted {result.deleted_count} test allowed email(s)")
    
    client.close()

# ============================================================================
# TEST 1: ROLE ENFORCEMENT
# ============================================================================

def test_role_submissions_list_pending():
    """Test that GET /api/submissions returns 403 for pending user"""
    print_section("TEST 1.1: Role Enforcement - Submissions List (Pending)")
    
    headers = {"Authorization": f"Bearer {pending_session_token}"}
    response = requests.get(f"{API_BASE}/submissions", headers=headers)
    
    passed = response.status_code == 403
    print_test(
        "GET /api/submissions with pending role returns 403",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_submissions_list_admin():
    """Test that GET /api/submissions returns 200 for admin user"""
    print_section("TEST 1.2: Role Enforcement - Submissions List (Admin)")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/submissions", headers=headers)
    
    passed = response.status_code == 200
    print_test(
        "GET /api/submissions with admin role returns 200",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_submissions_counts_pending():
    """Test that GET /api/submissions/counts returns 403 for pending user"""
    print_section("TEST 1.3: Role Enforcement - Submissions Counts (Pending)")
    
    headers = {"Authorization": f"Bearer {pending_session_token}"}
    response = requests.get(f"{API_BASE}/submissions/counts", headers=headers)
    
    passed = response.status_code == 403
    print_test(
        "GET /api/submissions/counts with pending role returns 403",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_submissions_counts_admin():
    """Test that GET /api/submissions/counts returns 200 for admin user"""
    print_section("TEST 1.4: Role Enforcement - Submissions Counts (Admin)")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/submissions/counts", headers=headers)
    
    passed = response.status_code == 200
    print_test(
        "GET /api/submissions/counts with admin role returns 200",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_admin_donations_pending():
    """Test that GET /api/admin/donations returns 403 for pending user"""
    print_section("TEST 1.5: Role Enforcement - Admin Donations (Pending)")
    
    headers = {"Authorization": f"Bearer {pending_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donations", headers=headers)
    
    passed = response.status_code == 403
    print_test(
        "GET /api/admin/donations with pending role returns 403",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_admin_donations_admin():
    """Test that GET /api/admin/donations returns 200 for admin user"""
    print_section("TEST 1.6: Role Enforcement - Admin Donations (Admin)")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donations", headers=headers)
    
    passed = response.status_code == 200
    print_test(
        "GET /api/admin/donations with admin role returns 200",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_admin_team_pending():
    """Test that GET /api/admin/team returns 403 for pending user"""
    print_section("TEST 1.7: Role Enforcement - Admin Team (Pending)")
    
    headers = {"Authorization": f"Bearer {pending_session_token}"}
    response = requests.get(f"{API_BASE}/admin/team", headers=headers)
    
    passed = response.status_code == 403
    print_test(
        "GET /api/admin/team with pending role returns 403",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_admin_team_admin():
    """Test that GET /api/admin/team returns 200 for admin user"""
    print_section("TEST 1.8: Role Enforcement - Admin Team (Admin)")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/team", headers=headers)
    
    passed = response.status_code == 200
    print_test(
        "GET /api/admin/team with admin role returns 200",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_role_media_upload_pending():
    """Test that POST /api/media returns 403 for pending user"""
    print_section("TEST 1.9: Role Enforcement - Media Upload (Pending)")
    
    headers = {"Authorization": f"Bearer {pending_session_token}"}
    with open('/tmp/test.png', 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        data = {'category': 'gallery', 'title': 'Test Photo'}
        response = requests.post(f"{API_BASE}/media", files=files, data=data, headers=headers)
    
    passed = response.status_code == 403
    print_test(
        "POST /api/media with pending role returns 403",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

# ============================================================================
# TEST 2: TEAM MANAGEMENT
# ============================================================================

def test_team_get_structure():
    """Test that GET /api/admin/team returns correct structure"""
    print_section("TEST 2.1: Team Management - Get Team Structure")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/team", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        has_users = 'users' in data and isinstance(data['users'], list)
        has_allowed = 'allowed_emails' in data and isinstance(data['allowed_emails'], list)
        has_me = 'me' in data and data['me'] == admin_user_id
        
        if has_users and has_allowed and has_me:
            passed = True
            print_test(
                "GET /api/admin/team returns {users, allowed_emails, me}",
                True,
                f"Users count: {len(data['users'])}, Allowed emails: {len(data['allowed_emails'])}, Me: {data['me']}"
            )
        else:
            print_test(
                "GET /api/admin/team returns {users, allowed_emails, me}",
                False,
                f"Missing fields. Has users: {has_users}, Has allowed: {has_allowed}, Has me: {has_me}"
            )
    else:
        print_test(
            "GET /api/admin/team returns {users, allowed_emails, me}",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_team_allow_email():
    """Test POST /api/admin/team/allow adds email to allowlist"""
    print_section("TEST 2.2: Team Management - Allow Email")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    payload = {"email": "newperson@example.com"}
    response = requests.post(f"{API_BASE}/admin/team/allow", json=payload, headers=headers)
    
    passed = False
    if response.status_code == 200:
        # Verify email appears in allowed_emails
        get_response = requests.get(f"{API_BASE}/admin/team", headers=headers)
        if get_response.status_code == 200:
            data = get_response.json()
            if "newperson@example.com" in data.get('allowed_emails', []):
                passed = True
                print_test(
                    "POST /api/admin/team/allow adds email to allowlist",
                    True,
                    "Email 'newperson@example.com' appears in allowed_emails"
                )
            else:
                print_test(
                    "POST /api/admin/team/allow adds email to allowlist",
                    False,
                    f"Email not found in allowed_emails: {data.get('allowed_emails', [])}"
                )
        else:
            print_test(
                "POST /api/admin/team/allow adds email to allowlist",
                False,
                f"Failed to verify: GET /api/admin/team returned {get_response.status_code}"
            )
    else:
        print_test(
            "POST /api/admin/team/allow adds email to allowlist",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_team_role_update_self_fail():
    """Test POST /api/admin/team/{user_id}/role returns 400 when removing own admin"""
    print_section("TEST 2.3: Team Management - Cannot Remove Own Admin")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    payload = {"role": "pending"}
    response = requests.post(f"{API_BASE}/admin/team/{admin_user_id}/role", json=payload, headers=headers)
    
    passed = response.status_code == 400
    print_test(
        "POST /api/admin/team/{self_user_id}/role with role='pending' returns 400",
        passed,
        f"Status: {response.status_code}, Detail: {response.json().get('detail', '') if response.status_code == 400 else response.text}"
    )
    
    return passed

def test_team_role_update_other_success():
    """Test POST /api/admin/team/{user_id}/role updates other user's role"""
    print_section("TEST 2.4: Team Management - Update Other User Role")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    payload = {"role": "admin"}
    response = requests.post(f"{API_BASE}/admin/team/{other_user_id}/role", json=payload, headers=headers)
    
    passed = False
    if response.status_code == 200:
        # Verify role was updated in database
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        user = db.users.find_one({"user_id": other_user_id})
        client.close()
        
        if user and user.get('role') == 'admin':
            passed = True
            print_test(
                "POST /api/admin/team/{other_user_id}/role updates role to admin",
                True,
                f"User {other_user_id} role updated to 'admin'"
            )
        else:
            print_test(
                "POST /api/admin/team/{other_user_id}/role updates role to admin",
                False,
                f"Role not updated in database: {user.get('role') if user else 'user not found'}"
            )
    else:
        print_test(
            "POST /api/admin/team/{other_user_id}/role updates role to admin",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_team_revoke_email():
    """Test POST /api/admin/team/revoke-email removes email from allowlist"""
    print_section("TEST 2.5: Team Management - Revoke Email")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    payload = {"email": "newperson@example.com"}
    response = requests.post(f"{API_BASE}/admin/team/revoke-email", json=payload, headers=headers)
    
    passed = False
    if response.status_code == 200:
        # Verify email is removed from allowed_emails
        get_response = requests.get(f"{API_BASE}/admin/team", headers=headers)
        if get_response.status_code == 200:
            data = get_response.json()
            if "newperson@example.com" not in data.get('allowed_emails', []):
                passed = True
                print_test(
                    "POST /api/admin/team/revoke-email removes email from allowlist",
                    True,
                    "Email 'newperson@example.com' removed from allowed_emails"
                )
            else:
                print_test(
                    "POST /api/admin/team/revoke-email removes email from allowlist",
                    False,
                    f"Email still in allowed_emails: {data.get('allowed_emails', [])}"
                )
        else:
            print_test(
                "POST /api/admin/team/revoke-email removes email from allowlist",
                False,
                f"Failed to verify: GET /api/admin/team returned {get_response.status_code}"
            )
    else:
        print_test(
            "POST /api/admin/team/revoke-email removes email from allowlist",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

# ============================================================================
# TEST 3: DONOR WALL (PUBLIC)
# ============================================================================

def test_donor_wall_public():
    """Test GET /api/donations/public returns correct structure and data"""
    print_section("TEST 3.1: Donor Wall - Public Endpoint")
    
    # No authentication needed - public endpoint
    response = requests.get(f"{API_BASE}/donations/public")
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        
        has_total = 'total_raised' in data
        has_goal = 'goal' in data and data['goal'] == 50000
        has_count = 'donor_count' in data
        has_recent = 'recent' in data and isinstance(data['recent'], list)
        
        if has_total and has_goal and has_count and has_recent:
            # Verify totals are correct (at least 125 from our seeded data)
            total_ok = data['total_raised'] >= 125
            count_ok = data['donor_count'] >= 2
            
            # Check recent donors for anonymization
            recent_names = [d.get('name') for d in data['recent']]
            has_anonymous = 'Anonymous' in recent_names
            has_jane = any('Jane D.' in name for name in recent_names)
            
            if total_ok and count_ok:
                passed = True
                print_test(
                    "GET /api/donations/public returns correct structure and data",
                    True,
                    f"Total: ${data['total_raised']}, Goal: ${data['goal']}, Donors: {data['donor_count']}, Recent: {len(data['recent'])}, Has Anonymous: {has_anonymous}, Has Jane D.: {has_jane}"
                )
            else:
                print_test(
                    "GET /api/donations/public returns correct structure and data",
                    False,
                    f"Totals incorrect. Total: ${data['total_raised']} (expected >=125), Count: {data['donor_count']} (expected >=2)"
                )
        else:
            print_test(
                "GET /api/donations/public returns correct structure and data",
                False,
                f"Missing fields. Has total: {has_total}, Has goal: {has_goal}, Has count: {has_count}, Has recent: {has_recent}"
            )
    else:
        print_test(
            "GET /api/donations/public returns correct structure and data",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_donor_wall_anonymization():
    """Test that donor names are properly anonymized"""
    print_section("TEST 3.2: Donor Wall - Name Anonymization")
    
    response = requests.get(f"{API_BASE}/donations/public")
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        recent = data.get('recent', [])
        
        # Find our seeded donors
        jane_donor = None
        secret_donor = None
        
        for donor in recent:
            name = donor.get('name', '')
            amount = donor.get('amount')
            
            # Jane Doe should appear as "Jane D." (non-anonymous)
            if amount == 100.0 and 'Jane' in name:
                jane_donor = donor
            
            # Secret Giver should appear as "Anonymous" (anonymous=True)
            if amount == 25.0 and name == 'Anonymous':
                secret_donor = donor
        
        jane_ok = jane_donor is not None and 'Jane D.' in jane_donor.get('name', '')
        secret_ok = secret_donor is not None and secret_donor.get('name') == 'Anonymous'
        
        if jane_ok and secret_ok:
            passed = True
            print_test(
                "Donor names properly anonymized",
                True,
                f"Jane Doe -> '{jane_donor.get('name')}', Secret Giver (anonymous) -> '{secret_donor.get('name')}'"
            )
        else:
            print_test(
                "Donor names properly anonymized",
                False,
                f"Jane found: {jane_ok} ({jane_donor}), Secret found: {secret_ok} ({secret_donor})"
            )
    else:
        print_test(
            "Donor names properly anonymized",
            False,
            f"Status: {response.status_code}"
        )
    
    return passed

# ============================================================================
# TEST 4: ADMIN DONATIONS
# ============================================================================

def test_admin_donations_structure():
    """Test GET /api/admin/donations returns correct structure"""
    print_section("TEST 4.1: Admin Donations - Structure")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donations", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        
        has_items = 'items' in data and isinstance(data['items'], list)
        has_summary = 'summary' in data and isinstance(data['summary'], dict)
        
        if has_items and has_summary:
            summary = data['summary']
            has_total = 'total_raised' in summary
            has_count = 'count' in summary
            has_monthly = 'monthly_count' in summary
            has_onetime = 'onetime_count' in summary
            
            if has_total and has_count and has_monthly and has_onetime:
                # Verify counts match our seeded data
                total_ok = summary['total_raised'] >= 125
                count_ok = summary['count'] >= 2
                monthly_ok = summary['monthly_count'] >= 1
                onetime_ok = summary['onetime_count'] >= 1
                
                if total_ok and count_ok and monthly_ok and onetime_ok:
                    passed = True
                    print_test(
                        "GET /api/admin/donations returns {items, summary} with correct data",
                        True,
                        f"Total: ${summary['total_raised']}, Count: {summary['count']}, Monthly: {summary['monthly_count']}, One-time: {summary['onetime_count']}"
                    )
                else:
                    print_test(
                        "GET /api/admin/donations returns {items, summary} with correct data",
                        False,
                        f"Counts incorrect: {summary}"
                    )
            else:
                print_test(
                    "GET /api/admin/donations returns {items, summary} with correct data",
                    False,
                    f"Summary missing fields: {summary}"
                )
        else:
            print_test(
                "GET /api/admin/donations returns {items, summary} with correct data",
                False,
                f"Missing items or summary. Has items: {has_items}, Has summary: {has_summary}"
            )
    else:
        print_test(
            "GET /api/admin/donations returns {items, summary} with correct data",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_admin_donations_filter_monthly():
    """Test GET /api/admin/donations?frequency=monthly filters correctly"""
    print_section("TEST 4.2: Admin Donations - Filter by Monthly")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donations?frequency=monthly", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        
        # All items should have frequency='monthly'
        all_monthly = all(item.get('frequency') == 'monthly' for item in items)
        has_monthly = any(item.get('frequency') == 'monthly' for item in items)
        
        if all_monthly and has_monthly:
            passed = True
            print_test(
                "GET /api/admin/donations?frequency=monthly returns only monthly donations",
                True,
                f"Found {len(items)} monthly donation(s)"
            )
        else:
            print_test(
                "GET /api/admin/donations?frequency=monthly returns only monthly donations",
                False,
                f"All monthly: {all_monthly}, Has monthly: {has_monthly}, Items: {items}"
            )
    else:
        print_test(
            "GET /api/admin/donations?frequency=monthly returns only monthly donations",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_admin_donations_filter_onetime():
    """Test GET /api/admin/donations?frequency=one-time filters correctly"""
    print_section("TEST 4.3: Admin Donations - Filter by One-Time")
    
    headers = {"Authorization": f"Bearer {admin_session_token}"}
    response = requests.get(f"{API_BASE}/admin/donations?frequency=one-time", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        
        # All items should have frequency='one-time'
        all_onetime = all(item.get('frequency') == 'one-time' for item in items)
        has_onetime = any(item.get('frequency') == 'one-time' for item in items)
        
        if all_onetime and has_onetime:
            passed = True
            print_test(
                "GET /api/admin/donations?frequency=one-time returns only one-time donations",
                True,
                f"Found {len(items)} one-time donation(s)"
            )
        else:
            print_test(
                "GET /api/admin/donations?frequency=one-time returns only one-time donations",
                False,
                f"All one-time: {all_onetime}, Has one-time: {has_onetime}, Items: {items}"
            )
    else:
        print_test(
            "GET /api/admin/donations?frequency=one-time returns only one-time donations",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all new feature tests"""
    print("\n" + "="*70)
    print("  CARING SISTERS CLUB - NEW FEATURES BACKEND TESTS")
    print("="*70)
    
    results = {}
    
    try:
        # Setup
        seed_test_users()
        seed_donor_data()
        
        # Test 1: Role Enforcement
        results['role_submissions_list_pending'] = test_role_submissions_list_pending()
        results['role_submissions_list_admin'] = test_role_submissions_list_admin()
        results['role_submissions_counts_pending'] = test_role_submissions_counts_pending()
        results['role_submissions_counts_admin'] = test_role_submissions_counts_admin()
        results['role_admin_donations_pending'] = test_role_admin_donations_pending()
        results['role_admin_donations_admin'] = test_role_admin_donations_admin()
        results['role_admin_team_pending'] = test_role_admin_team_pending()
        results['role_admin_team_admin'] = test_role_admin_team_admin()
        results['role_media_upload_pending'] = test_role_media_upload_pending()
        
        # Test 2: Team Management
        results['team_get_structure'] = test_team_get_structure()
        results['team_allow_email'] = test_team_allow_email()
        results['team_role_update_self_fail'] = test_team_role_update_self_fail()
        results['team_role_update_other_success'] = test_team_role_update_other_success()
        results['team_revoke_email'] = test_team_revoke_email()
        
        # Test 3: Donor Wall (Public)
        results['donor_wall_public'] = test_donor_wall_public()
        results['donor_wall_anonymization'] = test_donor_wall_anonymization()
        
        # Test 4: Admin Donations
        results['admin_donations_structure'] = test_admin_donations_structure()
        results['admin_donations_filter_monthly'] = test_admin_donations_filter_monthly()
        results['admin_donations_filter_onetime'] = test_admin_donations_filter_onetime()
        
    finally:
        # Cleanup
        cleanup_test_data()
    
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
