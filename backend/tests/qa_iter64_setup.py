"""Iter64 QA helper: python qa_iter64_setup.py up|down
Temp users for Open questions / FAQ tests (all example.com) + temp owner session for vincekudjoe."""
import sys
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
NOW = datetime.now(timezone.utc).isoformat()
SEEN = {"portal_welcome_seen_at": NOW, "app_celebrated_at": NOW}
TEMP = [
    {"user_id": "qa64_staff", "email": "qa64.staff@example.com", "name": "QA64 Staff", "role": "admin", "staff_level": "full",
     "member_status": "active", "member_since": NOW, "created_at": NOW, "club_team_badge": True, **SEEN},
    {"user_id": "qa64_staff2", "email": "qa64.staff2@example.com", "name": "QA64 StaffTwo", "role": "admin", "staff_level": "full",
     "member_status": "active", "member_since": NOW, "created_at": NOW, "club_team_badge": True, **SEEN},
    {"user_id": "qa64_content", "email": "qa64.content@example.com", "name": "QA64 Content", "role": "admin", "staff_level": "content",
     "member_status": "active", "member_since": NOW, "created_at": NOW, "club_team_badge": True, **SEEN},
    {"user_id": "qa64_mem", "email": "qa64.mem@example.com", "name": "QA64 Sister", "role": "user", "member_status": "active",
     "member_since": NOW, "created_at": NOW, **SEEN},
    {"user_id": "qa64_pending", "email": "qa64.pending@example.com", "name": "QA64 Pending", "role": "pending", "created_at": NOW, **SEEN},
]
OWNER_EMAIL = "vincekudjoe@gmail.com"
TOKENS = {"qa64_staff_tok": "qa64_staff", "qa64_staff2_tok": "qa64_staff2", "qa64_content_tok": "qa64_content",
          "qa64_mem_tok": "qa64_mem", "qa64_pending_tok": "qa64_pending"}
IDS = [u["user_id"] for u in TEMP]

if sys.argv[1] == "up":
    for u in TEMP:
        db.users.replace_one({"user_id": u["user_id"]}, u, upsert=True)
    owner = db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "user_id": 1})
    toks = dict(TOKENS, qa64_owner_tok=owner["user_id"])
    for t, uid in toks.items():
        db.user_sessions.replace_one({"session_token": t}, {"session_token": t, "user_id": uid, "expires_at": "2099-01-01T00:00:00+00:00"}, upsert=True)
    print("up", owner["user_id"])
else:
    print("users", db.users.delete_many({"user_id": {"$in": IDS}}).deleted_count)
    print("sessions", db.user_sessions.delete_many({"session_token": {"$in": list(TOKENS) + ["qa64_owner_tok"]}}).deleted_count)
    print("questions", db.team_questions.delete_many({"$or": [{"from.user_id": {"$in": IDS}}, {"to.user_id": {"$in": IDS}}]}).deleted_count)
    print("faqs", db.faqs.delete_many({"question": {"$regex": "^TEST_QA64"}}).deleted_count)
    db.settings.update_one({"key": "team_questions"}, {"$set": {"all_staff": False}})
    print("rate_hits", db.rate_hits.delete_many({"key": {"$regex": "^(team_q:qa64|team_r:qa64)"}}).deleted_count)
    for c in ("push_subscriptions", "notifications", "member_notifications"):
        try:
            db[c].delete_many({"user_id": {"$in": IDS}})
        except Exception:
            pass
