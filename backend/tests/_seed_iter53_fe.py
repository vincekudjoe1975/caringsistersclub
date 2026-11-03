"""FE QA seed for iteration 53 hours edit/remove: python _seed_iter53_fe.py up|down (admin cookie it53fe_tok)"""
import sys
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
IDS = ["it53fe-h1", "it53fe-h2", "it53fe-h3"]
EMAIL = "test_it53fe_sister@example.com"
if sys.argv[1] == "up":
    db.users.insert_one({"user_id": "it53fe_admin", "email": "it53fe_admin@example.com", "name": "TEST_ FE Admin", "role": "admin"})
    db.user_sessions.insert_one({"session_token": "it53fe_tok", "user_id": "it53fe_admin", "expires_at": "2099-01-01T00:00:00+00:00"})
    prog = db.programs.find_one({"published": True}, {"_id": 0, "id": 1, "title": 1})
    today = datetime.now(timezone.utc).date().isoformat()
    base = {"name": "TEST_ FE Sister", "email": EMAIL, "date": today, "note": "TEST_ fe", "leaderboard": False, "thanked": True,
            "created_at": datetime.now(timezone.utc).isoformat(), "program_id": prog["id"], "program": prog["title"]}
    db.volunteer_hours.insert_many([{**base, "id": IDS[0], "hours": 2.0, "status": "pending"},
                                    {**base, "id": IDS[1], "hours": 3.0, "status": "approved"},
                                    {**base, "id": IDS[2], "hours": 1.0, "status": "approved", "program_id": "", "activity": "TEST_ Portal Activity",
                                     "program": "TEST_ Portal Activity", "source": "portal"}])
else:
    print(db.volunteer_hours.delete_many({"id": {"$in": IDS}}).deleted_count)
    db.volunteer_milestones.delete_many({"email": EMAIL})
    db.user_sessions.delete_one({"session_token": "it53fe_tok"})
    db.users.delete_one({"user_id": "it53fe_admin"})
