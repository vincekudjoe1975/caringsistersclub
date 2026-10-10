"""Temp admin session helper for manual QA: python qa_session.py up|down"""
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
if sys.argv[1] == "up":
    db.users.insert_one({"user_id": "qa_user", "email": "qa@example.com", "name": "QA", "role": "admin"})
    db.user_sessions.insert_one({"session_token": "qa_tok_123", "user_id": "qa_user", "expires_at": "2099-01-01T00:00:00+00:00"})
    db.settings.update_one({"key": "site"}, {"$set": {"staff_notify_email": ""}}, upsert=True)
else:
    db.users.delete_one({"user_id": "qa_user"})
    db.user_sessions.delete_one({"session_token": "qa_tok_123"})
    db.settings.update_one({"key": "site"}, {"$set": {"staff_notify_email": "caringsistersclub@gmail.com"}})
    q = {"$regex": "example.com$"}
    print(db.events.delete_many({"title": {"$regex": "^QA"}}).deleted_count, db.event_rsvps.delete_many({"email": q}).deleted_count,
          db.event_waitlist.delete_many({"email": q}).deleted_count, db.submissions.delete_many({"data.email": q}).deleted_count)
