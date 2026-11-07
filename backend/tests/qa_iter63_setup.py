"""Iter63 QA helper: python qa_iter63_setup.py up|down
Temp users for join funnel / apply-reminder note / Ask the Club team tests (all example.com)."""
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
    {"user_id": "qa63_staff", "email": "qa63.staff@example.com", "name": "QA63 Staff", "role": "admin", "staff_level": "full",
     "member_status": "active", "member_since": NOW, "created_at": NOW, "club_team_badge": True, **SEEN},
    {"user_id": "qa63_staff_nb", "email": "qa63.staffnb@example.com", "name": "QA63 NoBadge", "role": "admin", "staff_level": "full",
     "member_status": "active", "member_since": NOW, "created_at": NOW, **SEEN},
    {"user_id": "qa63_mem_a", "email": "qa63.mem.a@example.com", "name": "QA63 Sister A", "role": "user", "member_status": "active",
     "member_since": NOW, "created_at": NOW, **SEEN},
    {"user_id": "qa63_mem_b", "email": "qa63.mem.b@example.com", "name": "QA63 Sister B", "role": "user", "member_status": "active",
     "member_since": NOW, "created_at": NOW, **SEEN},
    {"user_id": "qa63_applied", "email": "qa63.applied@example.com", "name": "QA63 Applied", "role": "pending", "member_status": "applied",
     "created_at": NOW, **SEEN},
    {"user_id": "qa63_waiting", "email": "qa63.waiting@example.com", "name": "QA63 Waiting", "role": "pending", "email_verified": True,
     "email_verified_at": NOW, "created_at": NOW, "auth_providers": ["password"]},
]
TOKENS = {"qa63_staff_tok": "qa63_staff", "qa63_nb_tok": "qa63_staff_nb", "qa63_a_tok": "qa63_mem_a", "qa63_b_tok": "qa63_mem_b",
          "qa63_applied_tok": "qa63_applied"}
IDS = [u["user_id"] for u in TEMP]

if sys.argv[1] == "up":
    for u in TEMP:
        db.users.replace_one({"user_id": u["user_id"]}, u, upsert=True)
    for t, uid in TOKENS.items():
        db.user_sessions.replace_one({"session_token": t}, {"session_token": t, "user_id": uid, "expires_at": "2099-01-01T00:00:00+00:00"}, upsert=True)
    print("up")
else:
    print("users", db.users.delete_many({"user_id": {"$in": IDS}}).deleted_count)
    print("sessions", db.user_sessions.delete_many({"session_token": {"$in": list(TOKENS)}}).deleted_count)
    print("questions", db.team_questions.delete_many({"$or": [{"from.user_id": {"$in": IDS}}, {"to.user_id": {"$in": IDS}}]}).deleted_count)
    print("rate_hits", db.rate_hits.delete_many({"key": {"$regex": "^(apply_manual:qa63|team_q:qa63|team_r:qa63)"}}).deleted_count)
    for c in ("push_subscriptions", "notifications", "member_notifications"):
        try:
            db[c].delete_many({"user_id": {"$in": IDS}})
        except Exception:
            pass
