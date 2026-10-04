#!/usr/bin/env python3
"""
Test campaign settings, webhook signature validation, and light regression.
Per /app/auth_testing.md pattern: seed admin user with role:"admin" and pending user with role:"pending".
"""
import requests
import time
import json
from datetime import datetime, timedelta

# Backend URL from frontend/.env
BASE_URL = "https://caring-sisters-clone.preview.emergentagent.com/api"

# MongoDB connection for seeding
from pymongo import MongoClient
mongo_client = MongoClient("mongodb://localhost:27017")
db = mongo_client["test_database"]

def seed_test_users():
    """Seed admin and pending users with sessions per auth_testing.md pattern."""
    timestamp = int(time.time() * 1000)
    
    # Admin user
    admin_user_id = f"user_test_admin_{timestamp}"
    admin_session_token = f"test_session_admin_{timestamp}"
    admin_email = f"test.admin.{timestamp}@example.com"
    
    db.users.insert_one({
        "user_id": admin_user_id,
        "email": admin_email,
        "name": "Test Admin",
        "picture": "https://via.placeholder.com/150",
        "role": "admin",
        "created_at": datetime.utcnow().isoformat()
    })
    
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    db.user_sessions.insert_one({
        "user_id": admin_user_id,
        "session_token": admin_session_token,
        "expires_at": expires_at,
        "created_at": datetime.utcnow().isoformat()
    })
    
    # Pending user
    pending_user_id = f"user_test_pending_{timestamp}"
    pending_session_token = f"test_session_pending_{timestamp}"
    pending_email = f"test.pending.{timestamp}@example.com"
    
    db.users.insert_one({
        "user_id": pending_user_id,
        "email": pending_email,
        "name": "Test Pending",
        "picture": "https://via.placeholder.com/150",
        "role": "pending",
        "created_at": datetime.utcnow().isoformat()
    })
    
    db.user_sessions.insert_one({
        "user_id": pending_user_id,
        "session_token": pending_session_token,
        "expires_at": expires_at,
        "created_at": datetime.utcnow().isoformat()
    })
    
    print(f"✓ Seeded admin user: {admin_email} with session token: {admin_session_token}")
    print(f"✓ Seeded pending user: {pending_email} with session token: {pending_session_token}")
    
    return {
        "admin_token": admin_session_token,
        "admin_user_id": admin_user_id,
        "admin_email": admin_email,
        "pending_token": pending_session_token,
        "pending_user_id": pending_user_id,
        "pending_email": pending_email
    }

def cleanup_test_data(test_data):
    """Clean up all test data from MongoDB."""
    # Delete test users
    db.users.delete_many({"email": {"$regex": "test\\.(admin|pending)\\."}})
    # Delete test sessions
    db.user_sessions.delete_many({"session_token": {"$regex": "test_session"}})
    # Delete test settings
    db.settings.delete_one({"key": "site"})
    # Delete test payment transactions
    db.payment_transactions.delete_many({"donor_email": {"$regex": "test@example\\.com"}})
    print("✓ Cleaned up all test data from MongoDB")

def test_campaign_settings():
    """Test campaign settings endpoints."""
    print("\n=== TESTING CAMPAIGN SETTINGS ===")
    
    # Seed test users
    test_data = seed_test_users()
    admin_token = test_data["admin_token"]
    pending_token = test_data["pending_token"]
    
    results = []
    
    try:
        # Test 1: GET /api/settings is PUBLIC -> 200 with default goal=50000
        print("\n[1] Testing GET /api/settings (PUBLIC)...")
        resp = requests.get(f"{BASE_URL}/settings", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "campaign_title" in data, "Missing campaign_title"
        assert "campaign_subtitle" in data, "Missing campaign_subtitle"
        assert "goal" in data, "Missing goal"
        # Default goal should be 50000 if never set
        assert data["goal"] == 50000, f"Expected default goal=50000, got {data['goal']}"
        print(f"✅ GET /api/settings returns 200 with default goal=50000: {data}")
        results.append(("GET /api/settings (PUBLIC)", True, "Returns 200 with default goal=50000"))
        
        # Test 2: PUT /api/admin/settings without auth -> 401
        print("\n[2] Testing PUT /api/admin/settings without auth...")
        resp = requests.put(
            f"{BASE_URL}/admin/settings",
            json={"campaign_title": "Test", "goal": 75000},
            timeout=10
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print(f"✅ PUT /api/admin/settings without auth returns 401")
        results.append(("PUT /api/admin/settings without auth", True, "Returns 401"))
        
        # Test 3: PUT /api/admin/settings with pending role -> 403
        print("\n[3] Testing PUT /api/admin/settings with pending role...")
        resp = requests.put(
            f"{BASE_URL}/admin/settings",
            headers={"Authorization": f"Bearer {pending_token}"},
            json={"campaign_title": "Test", "goal": 75000},
            timeout=10
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print(f"✅ PUT /api/admin/settings with pending role returns 403")
        results.append(("PUT /api/admin/settings with pending role", True, "Returns 403"))
        
        # Test 4: PUT /api/admin/settings with admin token and valid body -> 200
        print("\n[4] Testing PUT /api/admin/settings with admin token...")
        resp = requests.put(
            f"{BASE_URL}/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "campaign_title": "Build the Center",
                "campaign_subtitle": "Capital Campaign",
                "goal": 75000
            },
            timeout=10
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["campaign_title"] == "Build the Center", f"Expected 'Build the Center', got {data['campaign_title']}"
        assert data["campaign_subtitle"] == "Capital Campaign", f"Expected 'Capital Campaign', got {data['campaign_subtitle']}"
        assert data["goal"] == 75000, f"Expected goal=75000, got {data['goal']}"
        print(f"✅ PUT /api/admin/settings with admin token returns 200 with updated values: {data}")
        results.append(("PUT /api/admin/settings with admin token", True, "Returns 200 with updated values"))
        
        # Test 5: PUT /api/admin/settings with negative goal -> 400
        print("\n[5] Testing PUT /api/admin/settings with negative goal...")
        resp = requests.put(
            f"{BASE_URL}/admin/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"goal": -5},
            timeout=10
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print(f"✅ PUT /api/admin/settings with negative goal returns 400")
        results.append(("PUT /api/admin/settings with negative goal", True, "Returns 400"))
        
        # Test 6: GET /api/settings reflects new values
        print("\n[6] Testing GET /api/settings reflects new values...")
        resp = requests.get(f"{BASE_URL}/settings", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["campaign_title"] == "Build the Center", f"Expected 'Build the Center', got {data['campaign_title']}"
        assert data["campaign_subtitle"] == "Capital Campaign", f"Expected 'Capital Campaign', got {data['campaign_subtitle']}"
        assert data["goal"] == 75000, f"Expected goal=75000, got {data['goal']}"
        print(f"✅ GET /api/settings reflects new values: {data}")
        results.append(("GET /api/settings reflects new values", True, "Returns updated campaign_title, campaign_subtitle, goal"))
        
        # Test 7: GET /api/donations/public includes new goal and campaign_title/subtitle
        print("\n[7] Testing GET /api/donations/public includes new settings...")
        resp = requests.get(f"{BASE_URL}/donations/public", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["goal"] == 75000, f"Expected goal=75000, got {data['goal']}"
        assert data["campaign_title"] == "Build the Center", f"Expected 'Build the Center', got {data['campaign_title']}"
        assert data["campaign_subtitle"] == "Capital Campaign", f"Expected 'Capital Campaign', got {data['campaign_subtitle']}"
        print(f"✅ GET /api/donations/public includes new goal=75000, campaign_title='Build the Center', campaign_subtitle='Capital Campaign'")
        results.append(("GET /api/donations/public includes new settings", True, "Returns updated goal, campaign_title, campaign_subtitle"))
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        results.append(("Campaign settings test", False, str(e)))
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        results.append(("Campaign settings test", False, f"Unexpected error: {e}"))
    finally:
        cleanup_test_data(test_data)
    
    return results

def test_webhook_signature():
    """Test webhook signature validation."""
    print("\n=== TESTING WEBHOOK SIGNATURE ===")
    
    results = []
    
    try:
        # Test: POST /api/stripe/webhook with no/invalid stripe-signature header -> 400 (not 500)
        print("\n[1] Testing POST /api/stripe/webhook with no stripe-signature header...")
        resp = requests.post(
            f"{BASE_URL}/stripe/webhook",
            json={"type": "test.event", "data": {"object": {}}},
            timeout=10
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print(f"✅ POST /api/stripe/webhook with no stripe-signature header returns 400 (not 500)")
        results.append(("POST /api/stripe/webhook without signature", True, "Returns 400 (signature verification active)"))
        
        # Test with invalid signature
        print("\n[2] Testing POST /api/stripe/webhook with invalid stripe-signature header...")
        resp = requests.post(
            f"{BASE_URL}/stripe/webhook",
            headers={"stripe-signature": "invalid_signature"},
            json={"type": "test.event", "data": {"object": {}}},
            timeout=10
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print(f"✅ POST /api/stripe/webhook with invalid stripe-signature header returns 400 (not 500)")
        results.append(("POST /api/stripe/webhook with invalid signature", True, "Returns 400 (signature verification active)"))
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        results.append(("Webhook signature test", False, str(e)))
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        results.append(("Webhook signature test", False, f"Unexpected error: {e}"))
    
    return results

def test_light_regression():
    """Test light regression: checkout and donations/public."""
    print("\n=== TESTING LIGHT REGRESSION ===")
    
    results = []
    session_ids = []
    
    try:
        # Test 1: POST /api/payments/checkout -> 200 with checkout_url + session_id
        print("\n[1] Testing POST /api/payments/checkout...")
        resp = requests.post(
            f"{BASE_URL}/payments/checkout",
            json={
                "amount": 40,
                "frequency": "one-time",
                "origin_url": "https://example.com"
            },
            timeout=10
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "checkout_url" in data, "Missing checkout_url"
        assert "session_id" in data, "Missing session_id"
        assert "stripe.com" in data["checkout_url"], f"Invalid checkout_url: {data['checkout_url']}"
        session_ids.append(data["session_id"])
        print(f"✅ POST /api/payments/checkout returns 200 with checkout_url and session_id: {data['session_id']}")
        results.append(("POST /api/payments/checkout", True, "Returns 200 with checkout_url + session_id"))
        
        # Test 2: GET /api/donations/public -> 200
        print("\n[2] Testing GET /api/donations/public...")
        resp = requests.get(f"{BASE_URL}/donations/public", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "total_raised" in data, "Missing total_raised"
        assert "goal" in data, "Missing goal"
        assert "donor_count" in data, "Missing donor_count"
        assert "recent" in data, "Missing recent"
        print(f"✅ GET /api/donations/public returns 200: {data}")
        results.append(("GET /api/donations/public", True, "Returns 200 with correct structure"))
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        results.append(("Light regression test", False, str(e)))
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        results.append(("Light regression test", False, f"Unexpected error: {e}"))
    finally:
        # Clean up test payment transactions
        if session_ids:
            db.payment_transactions.delete_many({"session_id": {"$in": session_ids}})
            print(f"✓ Cleaned up {len(session_ids)} test payment transactions")
    
    return results

def main():
    print("=" * 80)
    print("BACKEND TEST: Campaign Settings, Webhook Signature, Light Regression")
    print("=" * 80)
    
    all_results = []
    
    # Run all tests
    all_results.extend(test_campaign_settings())
    all_results.extend(test_webhook_signature())
    all_results.extend(test_light_regression())
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success, _ in all_results if success)
    total = len(all_results)
    
    for test_name, success, message in all_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
