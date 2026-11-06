"""UI QA seed for iteration 58: python qa_iter58_ui.py up|down|code <code>"""
import sys
import os
import hashlib
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
now = datetime.now(timezone.utc)
IDS = ["ui58_admin", "ui58_a", "ui58_b", "ui58_c", "ui58_code"]
if sys.argv[1] == "up":
    db.users.insert_many([
        {"user_id": "ui58_admin", "email": "ui58.admin@example.com", "name": "TEST_ UI Admin", "role": "admin", "created_at": now.isoformat()},
        {"user_id": "ui58_a", "email": "ui58.a@example.com", "name": "TEST_ Ada", "role": "member", "member_status": "active", "created_at": now.isoformat(), "app_installed_at": now.isoformat()},
        {"user_id": "ui58_b", "email": "ui58.b@example.com", "name": "TEST_ Bea", "role": "member", "member_status": "active", "created_at": now.isoformat()},
        {"user_id": "ui58_c", "email": "ui58.c@example.com", "name": "TEST_ Cleo", "role": "member", "member_status": "active", "created_at": now.isoformat()},
        {"user_id": "ui58_code", "email": "ui58.code@example.com", "name": "TEST_ Coder", "role": "pending", "created_at": now.isoformat()},
    ])
    db.user_sessions.insert_one({"session_token": "ui58_admin_tok", "user_id": "ui58_admin", "expires_at": (now + timedelta(days=1)).isoformat()})
elif sys.argv[1] == "code":
    uid = sys.argv[3] if len(sys.argv) > 3 else "ui58_code"
    db.auth_tokens.delete_many({"user_id": uid, "kind": "code"})
    db.auth_tokens.insert_one({"token_hash": hashlib.sha256(f"{uid}:{sys.argv[2]}".encode()).hexdigest(), "user_id": uid, "kind": "code",
                               "used": False, "attempts": 0, "expires_at": now + timedelta(minutes=10), "created_at": now})
else:
    db.users.delete_many({"user_id": {"$in": IDS}})
    db.user_sessions.delete_many({"user_id": {"$in": IDS}})
    db.auth_tokens.delete_many({"user_id": {"$in": IDS}})
    db.rate_hits.delete_many({"key": {"$regex": "^(auth_code|app-nudge)"}})
