"""Iteration 51 — merge accounts, approval alert, apply-reminders, members-apply submission flow.

Uses the QA admin session (cookie session_token=qa_tok_123) created by qa_session.py.
Only touches @example.com QA users. Full teardown at end.
"""
import os
import sys
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"
XHR = {"X-Requested-With": "XMLHttpRequest"}
ADMIN_COOKIE = {"session_token": "qa_tok_123"}

db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


def _mk_user(suffix, extra=None):
    uid = f"qa_user_{suffix}_{uuid.uuid4().hex[:6]}"
    email = f"qa.{suffix}.{uid[-6:]}@example.com"
    doc = {"user_id": uid, "email": email, "name": f"QA {suffix.title()}", "picture": "",
           "role": "pending", "auth_providers": ["email"], "email_verified": True,
           "email_verified_at": datetime.now(timezone.utc).isoformat(),
           "created_at": datetime.now(timezone.utc).isoformat()}
    if extra:
        doc.update(extra)
    db.users.insert_one(doc)
    return doc


def _session_for(uid):
    tok = f"qatok_{uuid.uuid4().hex[:16]}"
    db.user_sessions.insert_one({"session_token": tok, "user_id": uid,
                                  "expires_at": "2099-01-01T00:00:00+00:00"})
    return tok


# Track created QA data for teardown
CREATED = {"user_ids": set(), "emails": set(), "session_tokens": set()}


def _track(u):
    CREATED["user_ids"].add(u["user_id"])
    CREATED["emails"].add(u["email"].lower())
    return u


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    uids = list(CREATED["user_ids"])
    emails = list(CREATED["emails"])
    toks = list(CREATED["session_tokens"])
    db.users.delete_many({"user_id": {"$in": uids}})
    db.users.delete_many({"email": {"$in": emails}})
    db.user_credentials.delete_many({"user_id": {"$in": uids}})
    db.auth_tokens.delete_many({"user_id": {"$in": uids}})
    db.user_sessions.delete_many({"$or": [{"user_id": {"$in": uids}}, {"session_token": {"$in": toks}}]})
    db.push_subs.delete_many({"user_id": {"$in": uids}})
    db.submissions.delete_many({"user_id": {"$in": uids}})
    db.member_ledger.delete_many({"user_id": {"$in": uids}})
    db.account_merges.delete_many({"$or": [{"keep": {"$in": uids}}, {"dup": {"$in": uids}}]})
    # Ensure apply_reminders_since enabled is reset to default (enabled=True preserved)
    db.settings.update_one({"key": "apply_reminders_since"}, {"$set": {"enabled": True}}, upsert=False)


# ---------- Full journey ----------
class TestMemberApplyJourney:
    def test_signup_verify_apply_approve(self):
        # Ensure apply_reminders_since.at is in the past so submissions treat things normally
        email = f"qa.applicant.{uuid.uuid4().hex[:6]}@example.com"
        CREATED["emails"].add(email)
        r = requests.post(f"{API}/auth/signup",
                          json={"email": email, "password": "abc12345", "name": "QA Applicant"})
        assert r.status_code == 200, r.text
        u = db.users.find_one({"email": email})
        assert u and u["role"] == "pending" and u.get("email_verified") is False
        CREATED["user_ids"].add(u["user_id"])

        # mint and consume verify token (simulate link click) — call /auth/verify-email
        import hashlib
        import secrets as _s
        raw = _s.token_urlsafe(32)
        db.auth_tokens.insert_one({
            "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
            "user_id": u["user_id"], "kind": "verify", "used": False,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            "created_at": datetime.now(timezone.utc)})
        s = requests.Session()
        r = s.post(f"{API}/auth/verify-email", json={"token": raw}, headers=XHR)
        assert r.status_code == 200, r.text
        assert s.cookies.get("session_token"), "verify-email should set session cookie"
        CREATED["session_tokens"].add(s.cookies.get("session_token"))

        # require_member returns 403 before apply
        r = s.get(f"{API}/members/announcements")
        assert r.status_code == 403

        # Apply
        r = s.post(f"{API}/members/apply", headers=XHR, json={
            "phone": "555-1212", "city": "Wilmington", "referred_by": "QA Admin",
            "why": "QA test apply", "is_adult": True, "is_delaware": True, "agrees_bylaws": True})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "applied"

        # Submission created
        sub = db.submissions.find_one({"type": "member", "user_id": u["user_id"]})
        assert sub and sub["data"]["email"] == email and sub["data"]["city"] == "Wilmington"
        assert sub.get("read") is False

        # Admin: GET /api/submissions?type=member sees her with member_status=applied
        r = requests.get(f"{API}/submissions?type=member", cookies=ADMIN_COOKIE)
        assert r.status_code == 200
        hers = [x for x in r.json() if x.get("user_id") == u["user_id"]]
        assert hers and hers[0]["member_status"] == "applied"

        # Still 403 for require_member
        r = s.get(f"{API}/members/announcements")
        assert r.status_code == 403

        # Approve via admin status endpoint
        r = requests.post(f"{API}/admin/members/{u['user_id']}/status",
                          json={"action": "approve"}, cookies=ADMIN_COOKIE, headers=XHR)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "active"

        # Now require_member returns 200
        r = s.get(f"{API}/members/announcements")
        assert r.status_code == 200

        # Submission has member_decision=active and is marked read
        sub2 = db.submissions.find_one({"type": "member", "user_id": u["user_id"]})
        assert sub2.get("member_decision") == "active"
        assert sub2.get("read") is True

        # /api/submissions enrichment reflects active now
        r = requests.get(f"{API}/submissions?type=member", cookies=ADMIN_COOKIE)
        hers = [x for x in r.json() if x.get("user_id") == u["user_id"]]
        assert hers[0]["member_status"] == "active"

    def test_decline_path(self):
        u = _track(_mk_user("decline", {"member_status": "applied",
                                         "member_application": {"city": "Dover", "phone": "", "referred_by": "x",
                                                                  "why": "", "submitted_at": datetime.now(timezone.utc).isoformat()}}))
        db.submissions.insert_one({"id": str(uuid.uuid4()), "type": "member", "user_id": u["user_id"],
                                    "data": {"name": u["name"], "email": u["email"], "city": "Dover",
                                             "phone": "", "referred_by": "x", "why": "", "signed_up_with": "Email + password"},
                                    "read": False, "created_at": datetime.now(timezone.utc).isoformat()})
        r = requests.post(f"{API}/admin/members/{u['user_id']}/status",
                          json={"action": "decline"}, cookies=ADMIN_COOKIE, headers=XHR)
        assert r.status_code == 200
        assert db.users.find_one({"user_id": u["user_id"]})["member_status"] == "declined"
        sub = db.submissions.find_one({"user_id": u["user_id"], "type": "member"})
        assert sub["member_decision"] == "declined"


# ---------- Waiting list / apply reminders ----------
class TestWaitingToApply:
    def test_waiting_list_and_reminders(self):
        # Make sure reminders are enabled and at=epoch so new user is eligible
        db.settings.update_one({"key": "apply_reminders_since"},
                                {"$set": {"enabled": True, "at": "2000-01-01T00:00:00+00:00"}},
                                upsert=True)
        u = _track(_mk_user("waiter"))  # email_verified=True, no member_status

        r = requests.get(f"{API}/admin/members/waiting", cookies=ADMIN_COOKIE)
        assert r.status_code == 200
        rows = r.json()["rows"]
        row = next((x for x in rows if x["user_id"] == u["user_id"]), None)
        assert row and row["eligible"] is True and not row["reminder_1_at"]

        # Age user by 4 days: should set reminder_1
        four = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        db.users.update_one({"user_id": u["user_id"]},
                             {"$set": {"created_at": four, "email_verified_at": four}})

        # Import server module and invoke _send_apply_reminders
        sys.path.insert(0, "/app/backend")
        import server
        asyncio.get_event_loop().run_until_complete(server._send_apply_reminders())
        after1 = db.users.find_one({"user_id": u["user_id"]})
        assert after1.get("apply_reminder_1_at"), "reminder_1 should be set after 3+ days"
        assert not after1.get("apply_reminder_2_at")

        # Age to 8 days
        eight = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        db.users.update_one({"user_id": u["user_id"]},
                             {"$set": {"created_at": eight, "email_verified_at": eight}})
        asyncio.get_event_loop().run_until_complete(server._send_apply_reminders())
        after2 = db.users.find_one({"user_id": u["user_id"]})
        assert after2.get("apply_reminder_2_at"), "reminder_2 should be set after 7+ days"

        # Run again — nothing new
        snap = after2.get("apply_reminder_2_at")
        asyncio.get_event_loop().run_until_complete(server._send_apply_reminders())
        after3 = db.users.find_one({"user_id": u["user_id"]})
        assert after3.get("apply_reminder_2_at") == snap

        # Toggle reminders off
        r = requests.put(f"{API}/admin/members/apply-reminders",
                         json={"enabled": False}, cookies=ADMIN_COOKIE, headers=XHR)
        assert r.status_code == 200 and r.json()["enabled"] is False
        # Clear reminder flags on a fresh waiter — toggled off, should NOT send
        u2 = _track(_mk_user("waiter2"))
        far_back = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        db.users.update_one({"user_id": u2["user_id"]},
                             {"$set": {"created_at": far_back, "email_verified_at": far_back}})
        asyncio.get_event_loop().run_until_complete(server._send_apply_reminders())
        after = db.users.find_one({"user_id": u2["user_id"]})
        assert not after.get("apply_reminder_1_at")
        # Re-enable
        requests.put(f"{API}/admin/members/apply-reminders",
                     json={"enabled": True}, cookies=ADMIN_COOKIE, headers=XHR)


# ---------- Merge duplicate accounts ----------
class TestMergeAccounts:
    def test_merge_full_flow(self):
        keep = _track(_mk_user("keep", {"role": "admin", "auth_providers": ["google"], "picture": "x"}))
        dup = _track(_mk_user("dup", {"member_status": "active",
                                       "member_profile": {"city": "Newark", "phone": "555"},
                                       "auth_providers": ["email"]}))
        # Fake push_subs and user_sessions pointing at dup
        db.push_subs.insert_one({"user_id": dup["user_id"], "endpoint": "https://fcm.googleapis.com/qa", "keys": {}})
        dup_tok = f"qatok_dup_{uuid.uuid4().hex[:10]}"
        CREATED["session_tokens"].add(dup_tok)
        db.user_sessions.insert_one({"session_token": dup_tok, "user_id": dup["user_id"],
                                      "expires_at": "2099-01-01T00:00:00+00:00"})

        # Preview
        r = requests.post(f"{API}/admin/team/merge/preview",
                          json={"keep_email": keep["email"], "dup_email": dup["email"]},
                          cookies=ADMIN_COOKIE, headers=XHR)
        assert r.status_code == 200, r.text
        prev = r.json()
        assert prev["keep"]["email"].lower() == keep["email"].lower()
        assert prev["dup"]["email"].lower() == dup["email"].lower()
        assert "devices" in prev["dup"]

        # Confirm merge
        r = requests.post(f"{API}/admin/team/merge",
                          json={"keep_email": keep["email"], "dup_email": dup["email"]},
                          cookies=ADMIN_COOKIE, headers=XHR)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True and body["moved"] >= 2  # push_subs + user_sessions at least

        # dup user deleted
        assert db.users.find_one({"user_id": dup["user_id"]}) is None
        # push_subs & user_sessions re-pointed
        ps = db.push_subs.find_one({"user_id": keep["user_id"], "endpoint": "https://fcm.googleapis.com/qa"})
        assert ps is not None
        assert db.user_sessions.find_one({"session_token": dup_tok})["user_id"] == keep["user_id"]
        # keep is active member, alt_emails includes dup email
        k2 = db.users.find_one({"user_id": keep["user_id"]})
        assert k2["member_status"] == "active"
        assert dup["email"].lower() in (k2.get("alt_emails") or [])

        # Old dup session cookie now authenticates as keep
        r = requests.get(f"{API}/auth/me", cookies={"session_token": dup_tok})
        assert r.status_code == 200, r.text
        assert r.json()["user_id"] == keep["user_id"]

        # reset-password-request with alias email returns generic 200
        r = requests.post(f"{API}/auth/reset-password-request", json={"email": dup["email"]})
        assert r.status_code == 200
        tok = db.auth_tokens.find_one({"user_id": keep["user_id"], "kind": "reset"})
        assert tok, "Reset token should be minted for the KEEP user via alias"
        db.auth_tokens.delete_many({"user_id": keep["user_id"], "kind": "reset"})

    def test_merge_errors(self):
        u = _track(_mk_user("mergerr"))
        # Same email twice -> 400
        r = requests.post(f"{API}/admin/team/merge/preview",
                          json={"keep_email": u["email"], "dup_email": u["email"]},
                          cookies=ADMIN_COOKIE, headers=XHR)
        assert r.status_code == 400

        # Unknown email -> 404
        r = requests.post(f"{API}/admin/team/merge/preview",
                          json={"keep_email": u["email"], "dup_email": "qa.nope.xyz@example.com"},
                          cookies=ADMIN_COOKIE, headers=XHR)
        assert r.status_code == 404

        # Non-admin -> 403 (no cookie)
        r = requests.post(f"{API}/admin/team/merge/preview",
                          json={"keep_email": u["email"], "dup_email": u["email"]},
                          headers=XHR)
        assert r.status_code in (401, 403)
