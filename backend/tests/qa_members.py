"""Temp member-portal QA users: python qa_members.py up|down (cookies mem_tok_a = applicant, mem_tok_b = second user)"""
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
USERS = [("qa_mem_a", "qa.sister.a@example.com", "Ama QA Sister", "mem_tok_a"), ("qa_mem_b", "qa.sister.b@example.com", "Bea QA Tester", "mem_tok_b")]
for uid, email, name, tok in USERS:
    db.users.delete_one({"user_id": uid})
    db.user_sessions.delete_one({"session_token": tok})
db.member_invites.delete_many({"email": {"$regex": "example.com$"}})
db.member_announcements.delete_many({"title": {"$regex": "^QA"}})
db.member_threads.delete_many({"title": {"$regex": "^QA"}})
if sys.argv[1] == "up":
    for uid, email, name, tok in USERS:
        db.users.insert_one({"user_id": uid, "email": email, "name": name, "role": "pending", "created_at": "2026-01-01T00:00:00+00:00"})
        db.user_sessions.insert_one({"session_token": tok, "user_id": uid, "expires_at": "2099-01-01T00:00:00+00:00"})
print("ok")
