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
