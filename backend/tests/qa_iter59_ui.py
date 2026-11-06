"""Iteration 59 UI QA helper: python qa_iter59_ui.py up|code|celebrate_reset|down"""
import sys
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
import bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
U = {"admin": "ui59_admin", "staff": "ui59_staff", "mem": "ui59_mem", "newmem": "ui59_newmem"}
BK = "/tmp/ui59_settings_backup.json"
now = lambda d=timedelta(): (datetime.now(timezone.utc) + d).isoformat()
cmd = sys.argv[1]
if cmd == "up":
    docs = {k: db.member_settings.find_one({"key": k}, {"_id": 0}) for k in ("welcome", "approval_email")}
    json.dump(docs, open(BK, "w"))
    db.users.insert_many([
        {"user_id": U["admin"], "email": "ui59.admin@example.com", "name": "Grace Tester", "role": "admin", "created_at": now()},
        {"user_id": U["staff"], "email": "ui59.staff@example.com", "name": "Staff Tester", "role": "admin", "email_verified": True,
         "auth_providers": ["email"], "require_login_code": True, "created_at": now()},
        {"user_id": U["mem"], "email": "ui59.mem@example.com", "name": "Ama Sister", "role": "member", "member_status": "active",
         "portal_welcome_seen_at": now(), "created_at": now()},
        {"user_id": U["newmem"], "email": "ui59.newmem@example.com", "name": "Efua New", "role": "member", "member_status": "active", "created_at": now()},
    ])
    db.user_credentials.insert_one({"user_id": U["staff"], "password_hash": bcrypt.hashpw(b"QaPass1234", bcrypt.gensalt()).decode()})
    db.user_sessions.insert_many([{"session_token": f"{u}_tok", "user_id": u, "expires_at": now(timedelta(days=1))} for u in (U["admin"], U["mem"], U["newmem"])])
elif cmd == "code":
    uid = U["staff"]
    print(db.auth_tokens.update_many({"user_id": uid, "kind": "staff_code"}, {"$set": {"token_hash": hashlib.sha256(f"{uid}:123456".encode()).hexdigest()}}).modified_count)
elif cmd == "celebrate_reset":
    db.users.update_one({"user_id": U["mem"]}, {"$unset": {"app_celebrated_at": "", "app_installed_at": ""}})
elif cmd == "state":
    for u in db.users.find({"user_id": {"$in": list(U.values())}}, {"_id": 0, "user_id": 1, "app_celebrated_at": 1, "app_installed_at": 1, "portal_welcome_seen_at": 1, "require_login_code": 1}):
        print(u)
    print(list(db.member_settings.find({"key": {"$in": ["welcome", "approval_email"]}}, {"_id": 0})))
else:
    ids = list(U.values())
    for c in ("users", "user_sessions", "auth_tokens", "user_credentials"):
        db[c].delete_many({"user_id": {"$in": ids}})
    db.rate_hits.delete_many({"key": {"$regex": "ui59|^(member_email_test|staff_code)"}})
    db.login_attempts.delete_many({"identifier": {"$regex": "ui59"}})
    if os.path.exists(BK):
        docs = json.load(open(BK))
        for k, d in docs.items():
            if d:
                db.member_settings.replace_one({"key": k}, d, upsert=True)
            else:
                db.member_settings.delete_one({"key": k})
        os.remove(BK)
    print("cleaned")
