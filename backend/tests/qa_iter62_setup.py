"""Iter62 QA helper: python qa_iter62_setup.py up|down
Creates temp staff users + owner session (qa_owner_tok) for Team Access sign-in activity / expiry / club team badge tests."""
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
OWNER_EMAIL = "vincekudjoe@gmail.com"
STATE = "/tmp/qa_iter62_state.json"
TEMP = [
    # active member + staff, opened Admin 5 days ago
    {"user_id": "qa62_staff_a", "email": "qa62.staff.a@example.com", "name": "QA62 Staff A", "role": "admin", "staff_level": "full",
     "member_status": "active", "member_since": "2026-01-01T00:00:00+00:00", "created_at": "2026-01-01T00:00:00+00:00",
     "admin_last_seen_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()},
    # staff, never opened Admin
    {"user_id": "qa62_staff_b", "email": "qa62.staff.b@example.com", "name": "QA62 Staff B", "role": "admin", "staff_level": "full",
     "member_status": "active", "member_since": "2026-01-01T00:00:00+00:00", "created_at": "2026-01-01T00:00:01+00:00"},
    # staff, opened 45 days ago
    {"user_id": "qa62_staff_c", "email": "qa62.staff.c@example.com", "name": "QA62 Staff C", "role": "admin", "staff_level": "full",
     "created_at": "2026-01-01T00:00:02+00:00", "admin_last_seen_at": (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()},
]

if sys.argv[1] == "up":
    owner = db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0})
    json.dump({"owner_id": owner["user_id"], "owner_seen": owner.get("admin_last_seen_at")}, open(STATE, "w"))
    for u in TEMP:
        db.users.replace_one({"user_id": u["user_id"]}, u, upsert=True)
    db.user_sessions.insert_one({"session_token": "qa_owner_tok", "user_id": owner["user_id"], "expires_at": "2099-01-01T00:00:00+00:00"})
    print("up", owner["user_id"])
else:
    st = json.load(open(STATE))
    db.users.delete_many({"user_id": {"$in": [u["user_id"] for u in TEMP]}})
    db.user_sessions.delete_one({"session_token": "qa_owner_tok"})
    # restore owner's admin_last_seen_at (owner requests bump it)
    if st.get("owner_seen"):
        db.users.update_one({"user_id": st["owner_id"]}, {"$set": {"admin_last_seen_at": st["owner_seen"]}})
    else:
        db.users.update_one({"user_id": st["owner_id"]}, {"$unset": {"admin_last_seen_at": ""}})
    n = db.staff_log.delete_many({"target.email": {"$regex": r"^qa62\..*@example\.com$"}}).deleted_count
    db.allowed_emails.delete_many({"email": {"$regex": r"^qa62\..*@example\.com$"}})
    print("down; staff_log removed", n)
