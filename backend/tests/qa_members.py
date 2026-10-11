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
db.member_threads.delete_many({"key": {"$regex": "^birthday:qa_mem"}})
uids = [u[0] for u in USERS]
db.member_ledger.delete_many({"user_id": {"$in": uids}})
db.member_checkouts.delete_many({"user_id": {"$in": uids}})
db.member_birthday_collections.delete_many({"user_id": {"$in": uids}})
db.member_notices.delete_many({"key": {"$regex": "qa_mem"}})
db.member_meetings.delete_many({"title": {"$regex": "^QA"}})
db.member_pay_tokens.delete_many({"user_id": {"$in": uids}})
db.member_reports.delete_many({"shared_by": {"$regex": "^QA"}})
imp = [u["user_id"] for u in db.users.find({"email": {"$regex": "^qa\\.(imp|xl)"}}, {"user_id": 1})]
db.users.delete_many({"user_id": {"$in": imp}})
db.member_ledger.delete_many({"user_id": {"$in": imp}})
db.member_spotlights.delete_many({"user_id": {"$in": uids + imp}})
db.member_annual_reports.delete_many({"shared_by": {"$regex": "^QA"}})
db.member_prayers.delete_many({"author_id": {"$in": uids}})
db.member_gathering_photos.delete_many({"uploader_id": {"$in": uids + ["qa_user"]}})
db.member_settings.delete_many({"key": "welcome", "subject": "Hello {first}!"})
db.member_december.delete_many({"key": {"$regex": "qa_mem"}})
db.member_collections.delete_many({"beneficiary_id": {"$in": uids}})
bids = [b["id"] for b in db.member_ballots.find({"title": {"$regex": "^QA"}}, {"id": 1})]
db.member_votes.delete_many({"ballot_id": {"$in": bids}})
db.member_voters.delete_many({"ballot_id": {"$in": bids}})
db.member_ballots.delete_many({"id": {"$in": bids}})
if sys.argv[1] == "up":
    for uid, email, name, tok in USERS:
        db.users.insert_one({"user_id": uid, "email": email, "name": name, "role": "pending", "created_at": "2026-01-01T00:00:00+00:00"})
        db.user_sessions.insert_one({"session_token": tok, "user_id": uid, "expires_at": "2099-01-01T00:00:00+00:00"})
print("ok")
