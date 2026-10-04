#!/usr/bin/env python3
"""
Quick Regression Test for Stripe Payments after refactor
Tests the specific scenarios requested in the review
"""

import requests
import json
from pymongo import MongoClient

# Configuration - use the public URL
BASE_URL = "https://caring-sisters-clone.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Track session IDs for cleanup
session_ids_to_cleanup = []

def print_test(name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")
    print()

def test_1_one_time_checkout():
    """Test 1: POST /api/payments/checkout with one-time donation"""
    print("=" * 70)
    print("TEST 1: One-Time Donation Checkout (amount=50)")
    print("=" * 70)
    
    payload = {
        "amount": 50,
        "frequency": "one-time",
        "origin_url": "https://example.com"
    }
    
    try:
        response = requests.post(f"{API_BASE}/payments/checkout", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            checkout_url = data.get('checkout_url', '')
            session_id = data.get('session_id', '')
            
            # Verify checkout_url contains stripe.com
            url_valid = 'stripe.com' in checkout_url
            # Verify session_id starts with 'cs_'
            session_valid = session_id.startswith('cs_')
            
            if url_valid and session_valid:
                session_ids_to_cleanup.append(session_id)
                print_test(
                    "One-time checkout (amount=50)",
                    True,
                    f"✓ Status: 200\n   ✓ checkout_url: {checkout_url[:50]}...\n   ✓ session_id: {session_id}"
                )
                return True, session_id
            else:
                print_test(
                    "One-time checkout (amount=50)",
                    False,
                    f"Invalid response format\n   checkout_url valid: {url_valid}\n   session_id valid: {session_valid}\n   Response: {data}"
                )
                return False, None
        else:
            print_test(
                "One-time checkout (amount=50)",
                False,
                f"Status: {response.status_code}\n   Body: {response.text}"
            )
            return False, None
    except Exception as e:
        print_test("One-time checkout (amount=50)", False, f"Exception: {str(e)}")
        return False, None

def test_2_monthly_checkout():
    """Test 2: POST /api/payments/checkout with monthly subscription"""
    print("=" * 70)
    print("TEST 2: Monthly Subscription Checkout (amount=25)")
    print("=" * 70)
    
    payload = {
        "amount": 25,
        "frequency": "monthly",
        "origin_url": "https://example.com"
    }
    
    try:
        response = requests.post(f"{API_BASE}/payments/checkout", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            checkout_url = data.get('checkout_url', '')
            session_id = data.get('session_id', '')
            
            # Verify checkout_url contains stripe.com
            url_valid = 'stripe.com' in checkout_url
            # Verify session_id starts with 'cs_'
            session_valid = session_id.startswith('cs_')
            
            if url_valid and session_valid:
                session_ids_to_cleanup.append(session_id)
                print_test(
                    "Monthly checkout (amount=25)",
                    True,
                    f"✓ Status: 200\n   ✓ checkout_url: {checkout_url[:50]}...\n   ✓ session_id: {session_id}"
                )
                return True
            else:
                print_test(
                    "Monthly checkout (amount=25)",
                    False,
                    f"Invalid response format\n   checkout_url valid: {url_valid}\n   session_id valid: {session_valid}\n   Response: {data}"
                )
                return False
        else:
            print_test(
                "Monthly checkout (amount=25)",
                False,
                f"Status: {response.status_code}\n   Body: {response.text}"
            )
            return False
    except Exception as e:
        print_test("Monthly checkout (amount=25)", False, f"Exception: {str(e)}")
        return False

def test_3_invalid_amounts():
    """Test 3: POST /api/payments/checkout with invalid amounts"""
    print("=" * 70)
    print("TEST 3: Invalid Amount Validation")
    print("=" * 70)
    
    results = []
    
    # Test 3a: Amount below minimum (0.5)
    payload_low = {
        "amount": 0.5,
        "frequency": "one-time",
        "origin_url": "https://example.com"
    }
    
    try:
        response = requests.post(f"{API_BASE}/payments/checkout", json=payload_low, timeout=30)
        passed = response.status_code == 400
        print_test(
            "Amount below minimum (0.5) returns 400",
            passed,
            f"Status: {response.status_code}\n   Body: {response.text[:100]}"
        )
        results.append(passed)
    except Exception as e:
        print_test("Amount below minimum (0.5) returns 400", False, f"Exception: {str(e)}")
        results.append(False)
    
    # Test 3b: Amount above maximum (200000)
    payload_high = {
        "amount": 200000,
        "frequency": "one-time",
        "origin_url": "https://example.com"
    }
    
    try:
        response = requests.post(f"{API_BASE}/payments/checkout", json=payload_high, timeout=30)
        passed = response.status_code == 400
        print_test(
            "Amount above maximum (200000) returns 400",
            passed,
            f"Status: {response.status_code}\n   Body: {response.text[:100]}"
        )
        results.append(passed)
    except Exception as e:
        print_test("Amount above maximum (200000) returns 400", False, f"Exception: {str(e)}")
        results.append(False)
    
    return all(results)

def test_4_payment_status(session_id):
    """Test 4: GET /api/payments/status/{session_id}"""
    print("=" * 70)
    print("TEST 4: Payment Status Check")
    print("=" * 70)
    
    if not session_id:
        print_test("Payment status check", False, "No session_id available from previous test")
        return False
    
    try:
        response = requests.get(f"{API_BASE}/payments/status/{session_id}", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            payment_status = data.get('payment_status')
            
            if payment_status == 'pending':
                print_test(
                    "Payment status returns 'pending'",
                    True,
                    f"✓ Status: 200\n   ✓ payment_status: {payment_status}\n   Full response: {json.dumps(data, indent=2)}"
                )
                return True
            else:
                print_test(
                    "Payment status returns 'pending'",
                    False,
                    f"Expected 'pending', got '{payment_status}'\n   Full response: {data}"
                )
                return False
        else:
            print_test(
                "Payment status returns 'pending'",
                False,
                f"Status: {response.status_code}\n   Body: {response.text}"
            )
            return False
    except Exception as e:
        print_test("Payment status returns 'pending'", False, f"Exception: {str(e)}")
        return False

def test_5_media_gallery():
    """Test 5: GET /api/media?category=gallery (public endpoint)"""
    print("=" * 70)
    print("TEST 5: Public Media Gallery List")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_BASE}/media?category=gallery", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print_test(
                    "GET /api/media?category=gallery returns 200 with list",
                    True,
                    f"✓ Status: 200\n   ✓ Response is a list\n   ✓ Items count: {len(data)}"
                )
                return True
            else:
                print_test(
                    "GET /api/media?category=gallery returns 200 with list",
                    False,
                    f"Response is not a list: {type(data)}\n   Response: {data}"
                )
                return False
        else:
            print_test(
                "GET /api/media?category=gallery returns 200 with list",
                False,
                f"Status: {response.status_code}\n   Body: {response.text}"
            )
            return False
    except Exception as e:
        print_test("GET /api/media?category=gallery returns 200 with list", False, f"Exception: {str(e)}")
        return False

def cleanup_payment_transactions():
    """Clean up test payment transactions from MongoDB"""
    print("=" * 70)
    print("CLEANUP: Removing Test Payment Transactions")
    print("=" * 70)
    
    if not session_ids_to_cleanup:
        print("No payment transactions to clean up.\n")
        return
    
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        result = db.payment_transactions.delete_many({"session_id": {"$in": session_ids_to_cleanup}})
        print(f"✓ Deleted {result.deleted_count} payment transaction(s)")
        print(f"  Session IDs cleaned: {session_ids_to_cleanup}\n")
        
        client.close()
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}\n")

def main():
    """Run all regression tests"""
    print("\n" + "=" * 70)
    print("  STRIPE PAYMENTS REGRESSION TEST")
    print("  Quick check after refactor")
    print("=" * 70 + "\n")
    
    results = {}
    session_id_for_status = None
    
    try:
        # Test 1: One-time checkout
        passed, session_id = test_1_one_time_checkout()
        results['test_1_one_time'] = passed
        if passed:
            session_id_for_status = session_id
        
        # Test 2: Monthly checkout
        results['test_2_monthly'] = test_2_monthly_checkout()
        
        # Test 3: Invalid amounts
        results['test_3_invalid_amounts'] = test_3_invalid_amounts()
        
        # Test 4: Payment status
        results['test_4_status'] = test_4_payment_status(session_id_for_status)
        
        # Test 5: Media gallery (public)
        results['test_5_media_gallery'] = test_5_media_gallery()
        
    finally:
        # Always cleanup
        cleanup_payment_transactions()
    
    # Summary
    print("=" * 70)
    print("  REGRESSION TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%\n")
    
    if failed > 0:
        print("Failed Tests:")
        for test_name, result in results.items():
            if not result:
                print(f"  - {test_name}")
        print()
    else:
        print("🎉 All regression tests passed! Stripe payments working correctly after refactor.\n")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
