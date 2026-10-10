"""Seed data for iter19 frontend tests. Call with argv: `up` or `down`."""
import os
import sys
import uuid
import secrets
from datetime import datetime, date, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
DB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

PID = "qa19fe-prog"
SLUG = "qa19fe-session"
CLONE_PID = "qa19fe-clone"
CLONE_SLUG = "caring-sisters-clone"  # exact slug the review requested
TOKEN = "qa19fetoken-" + secrets.token_urlsafe(16)

def up():
    down()
    today = date.today()
    DB.programs.insert_one({
        "id": PID, "slug": SLUG, "title": "QA19FE Dated Session",
        "category": "QA", "summary": "qa fe", "body": "", "goals": [], "impact": [],
        "cta_text": "Join", "cta_link": "/volunteer", "image_url": "",
        "published": True, "gallery": [], "testimonials": [], "home_testimonial_ids": [],
        "capacity": 10, "waitlist_mode": "claim",
        "start_date": (today + timedelta(days=4)).isoformat(),
        "end_date": (today + timedelta(days=4)).isoformat(),
        "schedule": "Thu 6-8pm", "order": 999, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Clone program (for ratings)
    DB.programs.insert_one({
        "id": CLONE_PID, "slug": CLONE_SLUG, "title": "QA19FE Clone For Ratings",
        "category": "QA", "summary": "qa clone", "body": "", "goals": [], "impact": [],
        "cta_text": "Join", "cta_link": "/volunteer", "image_url": "",
        "published": True, "gallery": [], "testimonials": [], "home_testimonial_ids": [],
        "capacity": 10, "waitlist_mode": "claim",
        "cloned_from": PID,
        "start_date": "", "end_date": "", "schedule": "",
        "order": 998, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Seated submissions
    sid1 = "qa19fe-sub-" + uuid.uuid4().hex[:8]
    sid2 = "qa19fe-sub-" + uuid.uuid4().hex[:8]
    for sid, nm in [(sid1, "FE Alice"), (sid2, "FE Bob")]:
        DB.submissions.insert_one({
            "id": sid, "type": "program_signup",
            "program_id": PID, "waitlist": False,
            "data": {"name": nm, "email": f"qa19fe.{sid[-4:]}@example.com", "program": "QA19FE", "program_slug": SLUG},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    # seated with release token for /release page
    DB.submissions.insert_one({
        "id": "qa19fe-rel-sub", "type": "program_signup",
        "program_id": PID, "waitlist": False,
        "data": {"name": "Release Sister", "email": "qa19fe.rel@example.com", "program": "QA19FE", "program_slug": SLUG},
        "release_token": TOKEN,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # 3 ratings for program ratings badge (shared across PID+CLONE_PID family)
    for rt in [5, 4, 5]:
        DB.session_feedback.insert_one({
            "id": str(uuid.uuid4()), "token": "fetok-" + uuid.uuid4().hex,
            "program_id": PID, "email": "x@example.com", "name": "X",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "rating": rt,
        })
    print("SEEDED", "PID=", PID, "TOKEN=", TOKEN, "CLONE_SLUG=", CLONE_SLUG)

def down():
    DB.programs.delete_many({"id": {"$regex": "^qa19fe-"}})
    # Also by exact clone slug
    DB.programs.delete_many({"slug": CLONE_SLUG, "title": {"$regex": "^QA19FE"}})
    DB.submissions.delete_many({"program_id": {"$regex": "^qa19fe-"}})
    DB.submissions.delete_many({"id": {"$regex": "^qa19fe-"}})
    DB.submissions.delete_many({"data.email": {"$regex": "qa19fe"}})
    DB.session_feedback.delete_many({"program_id": {"$regex": "^qa19fe-"}})

if __name__ == "__main__":
    (up if sys.argv[1] == "up" else down)()
