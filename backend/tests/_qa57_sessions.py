"""Iteration 57 temp 'applied' member session: python _qa57_sessions.py up|down"""
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
UID = "TEST_qa57_applied"
if sys.argv[1] == "up":
    db.users.insert_one({"user_id": UID, "email": "test.qa57.applied@example.com", "name": "TEST Applied57", "role": "pending", "member_status": "applied"})
    db.user_sessions.insert_one({"session_token": "TEST_qa57_apptok", "user_id": UID, "expires_at": "2099-01-01T00:00:00+00:00"})
    print("up")
else:
    db.users.delete_one({"user_id": UID})
    db.user_sessions.delete_many({"user_id": UID})
    db.members.delete_many({"user_id": UID})
    print("down")
