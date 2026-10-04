#!/usr/bin/env python3
"""
Backend API Testing for Caring Sisters Club
Tests Emergent Google Auth and File/Media Storage
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
uploaded_image_id = None
uploaded_pdf_id = None
submission_ids = {}  # Store submission IDs by type

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

def seed_test_user():
    """Seed a test user and session directly in MongoDB"""
    global test_user_id, test_session_token, test_email
    
    print_section("SETUP: Seeding Test User & Session")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Generate unique identifiers
    timestamp = int(time.time() * 1000)
    test_user_id = f"user_test{timestamp}"
    test_session_token = f"test_session_{timestamp}"
    test_email = f"test.admin.{timestamp}@example.com"
    
    # Insert test user
    user_doc = {
        "user_id": test_user_id,
        "email": test_email,
        "name": "Test Admin",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.utcnow().isoformat()
    }
    db.users.insert_one(user_doc)
    print(f"✓ Created test user: {test_email}")
    
    # Insert test session (expires in 7 days)
    expires_at = datetime.utcnow() + timedelta(days=7)
    session_doc = {
        "user_id": test_user_id,
        "session_token": test_session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    db.user_sessions.insert_one(session_doc)
    print(f"✓ Created test session: {test_session_token[:20]}...")
    
    client.close()
    return test_session_token

def cleanup_test_data():
    """Remove all test data from MongoDB"""
    print_section("CLEANUP: Removing Test Data")
    
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Delete test users
    result = db.users.delete_many({"email": {"$regex": "test\\.admin\\."}})
    print(f"✓ Deleted {result.deleted_count} test user(s)")
    
    # Delete test sessions
    result = db.user_sessions.delete_many({"session_token": {"$regex": "test_session"}})
    print(f"✓ Deleted {result.deleted_count} test session(s)")
    
    # Delete test media
    result = db.media.delete_many({"uploaded_by": {"$regex": "test\\.admin\\."}})
    print(f"✓ Deleted {result.deleted_count} test media item(s)")
    
    # Delete test submissions
    result = db.submissions.delete_many({"data.email": {"$regex": "test\\.submission\\."}})
    print(f"✓ Deleted {result.deleted_count} test submission(s)")
    
    client.close()

# ============================================================================
# TEST 1: Emergent Google Auth
# ============================================================================

def test_auth_unauthenticated():
    """Test that /api/auth/me returns 401 when unauthenticated"""
    print_section("TEST 1.1: Auth - Unauthenticated Access")
    
    response = requests.get(f"{API_BASE}/auth/me")
    
    passed = response.status_code == 401
    print_test(
        "GET /api/auth/me without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_auth_with_bearer_token():
    """Test that /api/auth/me returns user data with valid Bearer token"""
    print_section("TEST 1.2: Auth - Bearer Token Authentication")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.get(f"{API_BASE}/auth/me", headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if (data.get("email") == test_email and 
            data.get("name") == "Test Admin" and 
            data.get("role") == "admin"):
            passed = True
            print_test(
                "GET /api/auth/me with Bearer token returns correct user",
                True,
                f"Email: {data.get('email')}, Role: {data.get('role')}"
            )
        else:
            print_test(
                "GET /api/auth/me with Bearer token returns correct user",
                False,
                f"User data mismatch: {data}"
            )
    else:
        print_test(
            "GET /api/auth/me with Bearer token returns correct user",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_auth_logout():
    """Test that /api/auth/logout succeeds"""
    print_section("TEST 1.3: Auth - Logout")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.post(f"{API_BASE}/auth/logout", headers=headers)
    
    passed = response.status_code == 200
    print_test(
        "POST /api/auth/logout succeeds",
        passed,
        f"Status: {response.status_code}"
    )
    
    # Re-seed session for subsequent tests
    if passed:
        print("\n⚠ Re-seeding session for media tests...")
        seed_test_user()
    
    return passed

# ============================================================================
# TEST 2: File & Media Storage
# ============================================================================

def test_media_upload_unauthenticated():
    """Test that POST /api/media returns 401 when unauthenticated"""
    print_section("TEST 2.1: Media - Unauthenticated Upload")
    
    with open('/tmp/test.png', 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        data = {'category': 'gallery', 'title': 'Test Photo'}
        response = requests.post(f"{API_BASE}/media", files=files, data=data)
    
    passed = response.status_code == 401
    print_test(
        "POST /api/media without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_media_upload_image():
    """Test uploading an image with authentication"""
    print_section("TEST 2.2: Media - Upload Image (Authenticated)")
    
    global uploaded_image_id
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    with open('/tmp/test.png', 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        data = {'category': 'gallery', 'title': 'Test Photo'}
        response = requests.post(f"{API_BASE}/media", files=files, data=data, headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if all(k in data for k in ['id', 'url', 'storage_path', 'size']):
            uploaded_image_id = data['id']
            passed = True
            print_test(
                "POST /api/media uploads image successfully",
                True,
                f"ID: {data['id']}, Size: {data['size']} bytes"
            )
        else:
            print_test(
                "POST /api/media uploads image successfully",
                False,
                f"Missing fields in response: {data}"
            )
    else:
        print_test(
            "POST /api/media uploads image successfully",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_media_upload_pdf():
    """Test uploading a PDF with authentication"""
    print_section("TEST 2.3: Media - Upload PDF (Authenticated)")
    
    global uploaded_pdf_id
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    with open('/tmp/test.pdf', 'rb') as f:
        files = {'file': ('form990.pdf', f, 'application/pdf')}
        data = {'category': 'document', 'title': 'Form 990 2024', 'subtitle': '2024'}
        response = requests.post(f"{API_BASE}/media", files=files, data=data, headers=headers)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if all(k in data for k in ['id', 'url', 'storage_path', 'size']):
            uploaded_pdf_id = data['id']
            passed = True
            print_test(
                "POST /api/media uploads PDF successfully",
                True,
                f"ID: {data['id']}, Title: {data.get('title')}"
            )
        else:
            print_test(
                "POST /api/media uploads PDF successfully",
                False,
                f"Missing fields in response: {data}"
            )
    else:
        print_test(
            "POST /api/media uploads PDF successfully",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_media_upload_invalid_category():
    """Test that invalid category returns 400"""
    print_section("TEST 2.4: Media - Invalid Category")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    with open('/tmp/test.png', 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        data = {'category': 'invalid_category', 'title': 'Test'}
        response = requests.post(f"{API_BASE}/media", files=files, data=data, headers=headers)
    
    passed = response.status_code == 400
    print_test(
        "POST /api/media with invalid category returns 400",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_media_list_gallery():
    """Test listing gallery media items"""
    print_section("TEST 2.5: Media - List Gallery Items")
    
    response = requests.get(f"{API_BASE}/media?category=gallery")
    
    passed = False
    if response.status_code == 200:
        items = response.json()
        if isinstance(items, list):
            # Check if our uploaded image is in the list
            found = any(item.get('id') == uploaded_image_id for item in items)
            if found:
                passed = True
                print_test(
                    "GET /api/media?category=gallery lists uploaded image",
                    True,
                    f"Found {len(items)} item(s), including our test image"
                )
            else:
                print_test(
                    "GET /api/media?category=gallery lists uploaded image",
                    False,
                    f"Uploaded image not found in list of {len(items)} items"
                )
        else:
            print_test(
                "GET /api/media?category=gallery lists uploaded image",
                False,
                f"Response is not a list: {items}"
            )
    else:
        print_test(
            "GET /api/media?category=gallery lists uploaded image",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_media_list_documents():
    """Test listing document media items"""
    print_section("TEST 2.6: Media - List Document Items")
    
    response = requests.get(f"{API_BASE}/media?category=document")
    
    passed = False
    if response.status_code == 200:
        items = response.json()
        if isinstance(items, list):
            # Check if our uploaded PDF is in the list
            found = any(item.get('id') == uploaded_pdf_id for item in items)
            if found:
                passed = True
                print_test(
                    "GET /api/media?category=document lists uploaded PDF",
                    True,
                    f"Found {len(items)} item(s), including our test PDF"
                )
            else:
                print_test(
                    "GET /api/media?category=document lists uploaded PDF",
                    False,
                    f"Uploaded PDF not found in list of {len(items)} items"
                )
        else:
            print_test(
                "GET /api/media?category=document lists uploaded PDF",
                False,
                f"Response is not a list: {items}"
            )
    else:
        print_test(
            "GET /api/media?category=document lists uploaded PDF",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_media_fetch_image_file():
    """Test fetching image file bytes"""
    print_section("TEST 2.7: Media - Fetch Image File")
    
    response = requests.get(f"{API_BASE}/media/file/{uploaded_image_id}")
    
    passed = False
    if response.status_code == 200:
        content_type = response.headers.get('Content-Type', '')
        content_length = len(response.content)
        if 'image/png' in content_type and content_length > 0:
            passed = True
            print_test(
                "GET /api/media/file/{id} returns image with correct Content-Type",
                True,
                f"Content-Type: {content_type}, Size: {content_length} bytes"
            )
        else:
            print_test(
                "GET /api/media/file/{id} returns image with correct Content-Type",
                False,
                f"Content-Type: {content_type}, Size: {content_length} bytes"
            )
    else:
        print_test(
            "GET /api/media/file/{id} returns image with correct Content-Type",
            False,
            f"Status: {response.status_code}"
        )
    
    return passed

def test_media_fetch_pdf_file():
    """Test fetching PDF file bytes"""
    print_section("TEST 2.8: Media - Fetch PDF File")
    
    response = requests.get(f"{API_BASE}/media/file/{uploaded_pdf_id}")
    
    passed = False
    if response.status_code == 200:
        content_type = response.headers.get('Content-Type', '')
        content_length = len(response.content)
        if 'application/pdf' in content_type and content_length > 0:
            passed = True
            print_test(
                "GET /api/media/file/{id} returns PDF with correct Content-Type",
                True,
                f"Content-Type: {content_type}, Size: {content_length} bytes"
            )
        else:
            print_test(
                "GET /api/media/file/{id} returns PDF with correct Content-Type",
                False,
                f"Content-Type: {content_type}, Size: {content_length} bytes"
            )
    else:
        print_test(
            "GET /api/media/file/{id} returns PDF with correct Content-Type",
            False,
            f"Status: {response.status_code}"
        )
    
    return passed

def test_media_delete_unauthenticated():
    """Test that DELETE /api/media/{id} returns 401 when unauthenticated"""
    print_section("TEST 2.9: Media - Unauthenticated Delete")
    
    response = requests.delete(f"{API_BASE}/media/{uploaded_image_id}")
    
    passed = response.status_code == 401
    print_test(
        "DELETE /api/media/{id} without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_media_delete_authenticated():
    """Test soft-deleting media with authentication"""
    print_section("TEST 2.10: Media - Soft Delete (Authenticated)")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.delete(f"{API_BASE}/media/{uploaded_image_id}", headers=headers)
    
    passed = response.status_code == 200
    print_test(
        "DELETE /api/media/{id} with auth succeeds",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_media_list_after_delete():
    """Test that soft-deleted item is not in list"""
    print_section("TEST 2.11: Media - List After Soft Delete")
    
    response = requests.get(f"{API_BASE}/media?category=gallery")
    
    passed = False
    if response.status_code == 200:
        items = response.json()
        if isinstance(items, list):
            # Check that our deleted image is NOT in the list
            found = any(item.get('id') == uploaded_image_id for item in items)
            if not found:
                passed = True
                print_test(
                    "Soft-deleted item not in GET /api/media list",
                    True,
                    f"Deleted image correctly excluded from {len(items)} item(s)"
                )
            else:
                print_test(
                    "Soft-deleted item not in GET /api/media list",
                    False,
                    "Deleted image still appears in list"
                )
        else:
            print_test(
                "Soft-deleted item not in GET /api/media list",
                False,
                f"Response is not a list: {items}"
            )
    else:
        print_test(
            "Soft-deleted item not in GET /api/media list",
            False,
            f"Status: {response.status_code}"
        )
    
    return passed

def test_media_fetch_deleted_file():
    """Test that fetching soft-deleted file returns 404"""
    print_section("TEST 2.12: Media - Fetch Deleted File")
    
    response = requests.get(f"{API_BASE}/media/file/{uploaded_image_id}")
    
    passed = response.status_code == 404
    print_test(
        "GET /api/media/file/{id} for deleted item returns 404",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

# ============================================================================
# TEST 3: Form Submissions
# ============================================================================

def test_submission_create_volunteer():
    """Test creating a volunteer submission (PUBLIC)"""
    print_section("TEST 3.1: Submissions - Create Volunteer (Public)")
    
    global submission_ids
    
    payload = {
        "type": "volunteer",
        "name": "John Volunteer",
        "email": "test.submission.volunteer@example.com",
        "interest": "Community outreach"
    }
    
    response = requests.post(f"{API_BASE}/submissions", json=payload)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if 'id' in data:
            submission_ids['volunteer'] = data['id']
            passed = True
            print_test(
                "POST /api/submissions (volunteer) returns 200 with id",
                True,
                f"ID: {data['id']}"
            )
        else:
            print_test(
                "POST /api/submissions (volunteer) returns 200 with id",
                False,
                f"Missing 'id' in response: {data}"
            )
    else:
        print_test(
            "POST /api/submissions (volunteer) returns 200 with id",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_create_member():
    """Test creating a member submission (PUBLIC)"""
    print_section("TEST 3.2: Submissions - Create Member (Public)")
    
    global submission_ids
    
    payload = {
        "type": "member",
        "name": "Jane Member",
        "email": "test.submission.member@example.com",
        "phone": "555-1234"
    }
    
    response = requests.post(f"{API_BASE}/submissions", json=payload)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if 'id' in data:
            submission_ids['member'] = data['id']
            passed = True
            print_test(
                "POST /api/submissions (member) returns 200 with id",
                True,
                f"ID: {data['id']}"
            )
        else:
            print_test(
                "POST /api/submissions (member) returns 200 with id",
                False,
                f"Missing 'id' in response: {data}"
            )
    else:
        print_test(
            "POST /api/submissions (member) returns 200 with id",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_create_contact():
    """Test creating a contact submission (PUBLIC)"""
    print_section("TEST 3.3: Submissions - Create Contact (Public)")
    
    global submission_ids
    
    payload = {
        "type": "contact",
        "name": "Bob Contact",
        "email": "test.submission.contact@example.com",
        "subject": "General inquiry",
        "message": "I have a question about your organization."
    }
    
    response = requests.post(f"{API_BASE}/submissions", json=payload)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if 'id' in data:
            submission_ids['contact'] = data['id']
            passed = True
            print_test(
                "POST /api/submissions (contact) returns 200 with id",
                True,
                f"ID: {data['id']}"
            )
        else:
            print_test(
                "POST /api/submissions (contact) returns 200 with id",
                False,
                f"Missing 'id' in response: {data}"
            )
    else:
        print_test(
            "POST /api/submissions (contact) returns 200 with id",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_create_rsvp():
    """Test creating an RSVP submission (PUBLIC)"""
    print_section("TEST 3.4: Submissions - Create RSVP (Public)")
    
    global submission_ids
    
    payload = {
        "type": "rsvp",
        "name": "Alice RSVP",
        "email": "test.submission.rsvp@example.com",
        "event": "Annual Gala 2024"
    }
    
    response = requests.post(f"{API_BASE}/submissions", json=payload)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if 'id' in data:
            submission_ids['rsvp'] = data['id']
            passed = True
            print_test(
                "POST /api/submissions (rsvp) returns 200 with id",
                True,
                f"ID: {data['id']}"
            )
        else:
            print_test(
                "POST /api/submissions (rsvp) returns 200 with id",
                False,
                f"Missing 'id' in response: {data}"
            )
    else:
        print_test(
            "POST /api/submissions (rsvp) returns 200 with id",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_create_donation():
    """Test creating a donation submission (PUBLIC)"""
    print_section("TEST 3.5: Submissions - Create Donation (Public)")
    
    global submission_ids
    
    payload = {
        "type": "donation",
        "amount": 100,
        "frequency": "monthly",
        "email": "test.submission.donation@example.com"
    }
    
    response = requests.post(f"{API_BASE}/submissions", json=payload)
    
    passed = False
    if response.status_code == 200:
        data = response.json()
        if 'id' in data:
            submission_ids['donation'] = data['id']
            passed = True
            print_test(
                "POST /api/submissions (donation) returns 200 with id",
                True,
                f"ID: {data['id']}"
            )
        else:
            print_test(
                "POST /api/submissions (donation) returns 200 with id",
                False,
                f"Missing 'id' in response: {data}"
            )
    else:
        print_test(
            "POST /api/submissions (donation) returns 200 with id",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_create_invalid_type():
    """Test that invalid submission type returns 400"""
    print_section("TEST 3.6: Submissions - Invalid Type")
    
    payload = {
        "type": "spam",
        "name": "Spammer"
    }
    
    response = requests.post(f"{API_BASE}/submissions", json=payload)
    
    passed = response.status_code == 400
    print_test(
        "POST /api/submissions with invalid type returns 400",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_submission_list_unauthenticated():
    """Test that GET /api/submissions returns 401 when unauthenticated"""
    print_section("TEST 3.7: Submissions - Unauthenticated List")
    
    response = requests.get(f"{API_BASE}/submissions")
    
    passed = response.status_code == 401
    print_test(
        "GET /api/submissions without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_submission_counts_unauthenticated():
    """Test that GET /api/submissions/counts returns 401 when unauthenticated"""
    print_section("TEST 3.8: Submissions - Unauthenticated Counts")
    
    response = requests.get(f"{API_BASE}/submissions/counts")
    
    passed = response.status_code == 401
    print_test(
        "GET /api/submissions/counts without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_submission_mark_read_unauthenticated():
    """Test that PATCH /api/submissions/{id}/read returns 401 when unauthenticated"""
    print_section("TEST 3.9: Submissions - Unauthenticated Mark Read")
    
    # Use any ID (doesn't matter if it exists for 401 test)
    response = requests.patch(f"{API_BASE}/submissions/anyid/read")
    
    passed = response.status_code == 401
    print_test(
        "PATCH /api/submissions/{id}/read without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_submission_delete_unauthenticated():
    """Test that DELETE /api/submissions/{id} returns 401 when unauthenticated"""
    print_section("TEST 3.10: Submissions - Unauthenticated Delete")
    
    # Use any ID (doesn't matter if it exists for 401 test)
    response = requests.delete(f"{API_BASE}/submissions/anyid")
    
    passed = response.status_code == 401
    print_test(
        "DELETE /api/submissions/{id} without auth returns 401",
        passed,
        f"Status: {response.status_code}"
    )
    
    return passed

def test_submission_list_by_type():
    """Test listing submissions filtered by type (authenticated)"""
    print_section("TEST 3.11: Submissions - List by Type (Authenticated)")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.get(f"{API_BASE}/submissions?type=volunteer", headers=headers)
    
    passed = False
    if response.status_code == 200:
        items = response.json()
        if isinstance(items, list):
            # Check if our volunteer submission is in the list
            found = any(item.get('id') == submission_ids.get('volunteer') for item in items)
            if found:
                passed = True
                print_test(
                    "GET /api/submissions?type=volunteer returns created submission",
                    True,
                    f"Found volunteer submission in list of {len(items)} item(s)"
                )
            else:
                print_test(
                    "GET /api/submissions?type=volunteer returns created submission",
                    False,
                    f"Volunteer submission not found in list of {len(items)} items"
                )
        else:
            print_test(
                "GET /api/submissions?type=volunteer returns created submission",
                False,
                f"Response is not a list: {items}"
            )
    else:
        print_test(
            "GET /api/submissions?type=volunteer returns created submission",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_counts():
    """Test getting submission counts (authenticated)"""
    print_section("TEST 3.12: Submissions - Counts (Authenticated)")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    response = requests.get(f"{API_BASE}/submissions/counts", headers=headers)
    
    passed = False
    if response.status_code == 200:
        counts = response.json()
        # Check that all types are present and have total/unread
        expected_types = ['volunteer', 'member', 'contact', 'rsvp', 'donation']
        all_present = all(t in counts for t in expected_types)
        all_have_fields = all(
            'total' in counts.get(t, {}) and 'unread' in counts.get(t, {})
            for t in expected_types
        )
        
        if all_present and all_have_fields:
            # Check that counts are correct (at least 1 for each type we created)
            correct_counts = all(
                counts[t]['total'] >= 1 and counts[t]['unread'] >= 1
                for t in expected_types
            )
            if correct_counts:
                passed = True
                print_test(
                    "GET /api/submissions/counts returns correct structure and counts",
                    True,
                    f"All types present with total/unread. Example: volunteer={counts['volunteer']}"
                )
            else:
                print_test(
                    "GET /api/submissions/counts returns correct structure and counts",
                    False,
                    f"Counts incorrect: {counts}"
                )
        else:
            print_test(
                "GET /api/submissions/counts returns correct structure and counts",
                False,
                f"Missing types or fields: {counts}"
            )
    else:
        print_test(
            "GET /api/submissions/counts returns correct structure and counts",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_mark_read():
    """Test marking a submission as read (authenticated)"""
    print_section("TEST 3.13: Submissions - Mark as Read (Authenticated)")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    volunteer_id = submission_ids.get('volunteer')
    
    # First get the initial unread count for volunteer
    counts_before = requests.get(f"{API_BASE}/submissions/counts", headers=headers).json()
    unread_before = counts_before.get('volunteer', {}).get('unread', 0)
    
    # Mark as read
    response = requests.patch(f"{API_BASE}/submissions/{volunteer_id}/read", headers=headers)
    
    passed = False
    if response.status_code == 200:
        # Check that unread count decreased
        counts_after = requests.get(f"{API_BASE}/submissions/counts", headers=headers).json()
        unread_after = counts_after.get('volunteer', {}).get('unread', 0)
        
        if unread_after == unread_before - 1:
            passed = True
            print_test(
                "PATCH /api/submissions/{id}/read decrements unread count",
                True,
                f"Unread count: {unread_before} -> {unread_after}"
            )
        else:
            print_test(
                "PATCH /api/submissions/{id}/read decrements unread count",
                False,
                f"Unread count did not decrease correctly: {unread_before} -> {unread_after}"
            )
    else:
        print_test(
            "PATCH /api/submissions/{id}/read decrements unread count",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

def test_submission_delete():
    """Test deleting a submission (authenticated)"""
    print_section("TEST 3.14: Submissions - Delete (Authenticated)")
    
    headers = {"Authorization": f"Bearer {test_session_token}"}
    contact_id = submission_ids.get('contact')
    
    # First get the initial total count for contact
    counts_before = requests.get(f"{API_BASE}/submissions/counts", headers=headers).json()
    total_before = counts_before.get('contact', {}).get('total', 0)
    
    # Delete the submission
    response = requests.delete(f"{API_BASE}/submissions/{contact_id}", headers=headers)
    
    passed = False
    if response.status_code == 200:
        # Check that it's no longer in the list
        list_response = requests.get(f"{API_BASE}/submissions?type=contact", headers=headers)
        items = list_response.json()
        found = any(item.get('id') == contact_id for item in items)
        
        # Check that total count decreased
        counts_after = requests.get(f"{API_BASE}/submissions/counts", headers=headers).json()
        total_after = counts_after.get('contact', {}).get('total', 0)
        
        if not found and total_after == total_before - 1:
            passed = True
            print_test(
                "DELETE /api/submissions/{id} removes item and decrements total",
                True,
                f"Item removed from list, total count: {total_before} -> {total_after}"
            )
        else:
            print_test(
                "DELETE /api/submissions/{id} removes item and decrements total",
                False,
                f"Item still in list: {found}, total: {total_before} -> {total_after}"
            )
    else:
        print_test(
            "DELETE /api/submissions/{id} removes item and decrements total",
            False,
            f"Status: {response.status_code}, Body: {response.text}"
        )
    
    return passed

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all backend tests"""
    print("\n" + "="*70)
    print("  CARING SISTERS CLUB - BACKEND API TESTS")
    print("="*70)
    
    results = {}
    
    try:
        # Setup
        seed_test_user()
        
        # Test 1: Emergent Google Auth
        results['auth_unauthenticated'] = test_auth_unauthenticated()
        results['auth_bearer_token'] = test_auth_with_bearer_token()
        results['auth_logout'] = test_auth_logout()
        
        # Test 2: File & Media Storage
        results['media_upload_unauth'] = test_media_upload_unauthenticated()
        results['media_upload_image'] = test_media_upload_image()
        results['media_upload_pdf'] = test_media_upload_pdf()
        results['media_invalid_category'] = test_media_upload_invalid_category()
        results['media_list_gallery'] = test_media_list_gallery()
        results['media_list_documents'] = test_media_list_documents()
        results['media_fetch_image'] = test_media_fetch_image_file()
        results['media_fetch_pdf'] = test_media_fetch_pdf_file()
        results['media_delete_unauth'] = test_media_delete_unauthenticated()
        results['media_delete_auth'] = test_media_delete_authenticated()
        results['media_list_after_delete'] = test_media_list_after_delete()
        results['media_fetch_deleted'] = test_media_fetch_deleted_file()
        
        # Test 3: Form Submissions
        results['submission_create_volunteer'] = test_submission_create_volunteer()
        results['submission_create_member'] = test_submission_create_member()
        results['submission_create_contact'] = test_submission_create_contact()
        results['submission_create_rsvp'] = test_submission_create_rsvp()
        results['submission_create_donation'] = test_submission_create_donation()
        results['submission_invalid_type'] = test_submission_create_invalid_type()
        results['submission_list_unauth'] = test_submission_list_unauthenticated()
        results['submission_counts_unauth'] = test_submission_counts_unauthenticated()
        results['submission_mark_read_unauth'] = test_submission_mark_read_unauthenticated()
        results['submission_delete_unauth'] = test_submission_delete_unauthenticated()
        results['submission_list_by_type'] = test_submission_list_by_type()
        results['submission_counts'] = test_submission_counts()
        results['submission_mark_read'] = test_submission_mark_read()
        results['submission_delete'] = test_submission_delete()
        
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
