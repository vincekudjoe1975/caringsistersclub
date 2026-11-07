"""Iteration 60 temp staff-level sessions: python _qa60_sessions.py up|down"""
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
LEVELS = ["content", "members", "money"]
EXTRA = ["TEST_qa60_target", "TEST_qa60_target2", "TEST_qa60_demote"]
EMAILS = [f"test.qa60.{x}@example.com" for x in LEVELS + ["target", "target2", "demote", "preappr"]]
if sys.argv[1] == "up":
    for lv in LEVELS:
        uid = f"TEST_qa60_{lv}"
        db.users.insert_one({"user_id": uid, "email": f"test.qa60.{lv}@example.com", "name": f"TEST {lv.title()} Staff",
                             "role": "admin", "staff_level": lv, "created_at": "2099-01-01T00:00:00+00:00"})
        db.user_sessions.insert_one({"session_token": f"TEST_qa60_tok_{lv}", "user_id": uid, "expires_at": "2099-01-01T00:00:00+00:00"})
    # member accounts (no member_status) for grants
    db.users.insert_one({"user_id": "TEST_qa60_target", "email": "test.qa60.target@example.com", "name": "TEST Target60", "role": "pending", "created_at": "2099-01-02T00:00:00+00:00"})
    db.users.insert_one({"user_id": "TEST_qa60_target2", "email": "test.qa60.target2@example.com", "name": "TEST Target60b", "role": "pending", "created_at": "2099-01-03T00:00:00+00:00"})
    # existing admin to demote/level change (no grant alert)
    db.users.insert_one({"user_id": "TEST_qa60_demote", "email": "test.qa60.demote@example.com", "name": "TEST Demote60", "role": "admin", "staff_level": "full", "created_at": "2099-01-04T00:00:00+00:00"})
    print("up")
else:
    for lv in LEVELS:
        db.users.delete_one({"user_id": f"TEST_qa60_{lv}"})
        db.user_sessions.delete_many({"user_id": f"TEST_qa60_{lv}"})
    for uid in EXTRA:
        db.users.delete_one({"user_id": uid})
        db.user_sessions.delete_many({"user_id": uid})
    print("log", db.staff_log.delete_many({"target.email": {"$in": EMAILS}}).deleted_count,
          "allowed", db.allowed_emails.delete_many({"email": {"$in": EMAILS}}).deleted_count)
    print("down")
