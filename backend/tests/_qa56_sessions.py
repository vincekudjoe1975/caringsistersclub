"""Iteration 56 temp member+admin sessions for FE checks: python _qa56_sessions.py up|down"""
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
if sys.argv[1] == "up":
    db.users.insert_one({"user_id": "TEST_qa56_mem", "email": "test.qa56.mem@example.com", "name": "TEST Sister56", "role": "pending", "member_status": "active"})
    db.user_sessions.insert_one({"session_token": "TEST_qa56_memtok", "user_id": "TEST_qa56_mem", "expires_at": "2099-01-01T00:00:00+00:00"})
    db.users.insert_one({"user_id": "TEST_qa56_adm", "email": "test.qa56.adm@example.com", "name": "TEST Admin56", "role": "admin"})
    db.user_sessions.insert_one({"session_token": "TEST_qa56_admtok", "user_id": "TEST_qa56_adm", "expires_at": "2099-01-01T00:00:00+00:00"})
else:
    for u in ("TEST_qa56_mem", "TEST_qa56_adm"):
        db.users.delete_one({"user_id": u})
        db.user_sessions.delete_many({"user_id": u})
        db.members.delete_many({"user_id": u})
