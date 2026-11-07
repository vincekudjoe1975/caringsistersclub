"""Iteration 61 UI seed: python _qa61_ui.py up|down"""
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
FUT = "2099-01-01T00:00:00+00:00"
EM = ["test.qa61.ui@example.com", "qa@example.com"]
if sys.argv[1] == "up":
    owner = db.users.find_one({"email": "vincekudjoe@gmail.com"}, {"_id": 0, "user_id": 1})
    db.user_sessions.insert_one({"session_token": "qa_owner_tok", "user_id": owner["user_id"], "expires_at": FUT})
    db.users.insert_one({"user_id": "qa_user", "email": "qa@example.com", "name": "QA", "role": "admin"})
    db.user_sessions.insert_one({"session_token": "qa_tok_123", "user_id": "qa_user", "expires_at": FUT})
    db.users.insert_one({"user_id": "TEST_qa61_ui", "email": EM[0], "name": "TEST UiStaff", "role": "admin", "staff_level": "full", "created_at": FUT})
    print("up")
else:
    db.user_sessions.delete_many({"session_token": {"$in": ["qa_owner_tok", "qa_tok_123"]}})
    db.users.delete_many({"user_id": {"$in": ["qa_user", "TEST_qa61_ui"]}})
    print("log", db.staff_log.delete_many({"target.email": {"$in": EM}}).deleted_count)
    print("down")
