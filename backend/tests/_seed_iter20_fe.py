"""Seed data for iter-20 FE tests. up|down."""
import sys, os, uuid, datetime as dt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

PID = "qa20fe-prog"
SLUG = "qa20fe-slug"
SUB_NS1 = "qa20fe-sub-ns1"
SUB_NS2 = "qa20fe-sub-ns2"
FB_IDS = ["qa20fe-fb1", "qa20fe-fb2", "qa20fe-fb3"]
BADGE_EMAIL = "qa20fe.faithful@example.com"
BADGE_TOKEN = "qa20fetok1234567"

def _day(n):
    return (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=n)).isoformat()

def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

if sys.argv[1] == "up":
    # Program (ended yesterday)
    db.programs.insert_one({
        "id": PID, "slug": SLUG, "title": "QA20FE No-Show Program",
        "summary": "QA20FE summary", "description": "QA20FE descr", "image_url": "",
        "category": "Caring", "published": True, "capacity": 10, "order": 998,
        "created_at": _now(), "schedule": "Sat 10am", "start_date": _day(-2), "end_date": _day(-1),
        "cta_text": "Get Involved", "cta_link": "/volunteer", "testimonials": [], "goals": [], "impact": [],
    })
    # Two seated subs, both no_show -> noshow-followup-btn should show pending=2
    db.submissions.insert_many([
        {"id": SUB_NS1, "type": "program_signup", "program_id": PID, "waitlist": False,
         "stage": "new", "attendance": "no_show",
         "data": {"name": "FE Alice", "email": "qa20fe.ns1@example.com", "program": "QA20FE No-Show Program", "program_slug": SLUG},
         "created_at": _now()},
        {"id": SUB_NS2, "type": "program_signup", "program_id": PID, "waitlist": False,
         "stage": "new", "attendance": "no_show",
         "data": {"name": "FE Beth", "email": "qa20fe.ns2@example.com", "program": "QA20FE No-Show Program", "program_slug": SLUG},
         "created_at": _now()},
    ])
    # Program for review-highlight on /initiatives card and /initiatives/{slug}
    # Already have one program; add 3 feedback for it so rating + highlight show
    now = dt.datetime.now(dt.timezone.utc)
    db.session_feedback.insert_many([
        {"id": FB_IDS[0], "program_id": PID, "name": "Nora Older", "email": "x1@ex.com", "rating": 5,
         "comment": "Older five star — such warmth here.", "submitted_at": (now - dt.timedelta(days=30)).isoformat()},
        {"id": FB_IDS[1], "program_id": PID, "name": "Nancy Newer", "email": "x2@ex.com", "rating": 5,
         "comment": "Newer five star — I felt completely seen.", "submitted_at": (now - dt.timedelta(days=5)).isoformat()},
        {"id": FB_IDS[2], "program_id": PID, "name": "Tara Three", "email": "x3@ex.com", "rating": 3,
         "comment": "It was okay overall.", "submitted_at": (now - dt.timedelta(days=1)).isoformat()},
    ])
    # Faithful badge for /badge/{token}
    db.participant_badges.insert_one({
        "email": BADGE_EMAIL, "kind": "faithful", "name": "Faith Sister", "label": "Faithful Sister",
        "seal": "3x", "share_token": BADGE_TOKEN, "awarded_at": _now(),
    })
    print("UP: seeded", PID, SLUG, FB_IDS, BADGE_TOKEN)
else:
    db.programs.delete_many({"id": PID})
    db.submissions.delete_many({"id": {"$in": [SUB_NS1, SUB_NS2]}})
    db.session_feedback.delete_many({"id": {"$in": FB_IDS}})
    db.noshow_emails.delete_many({"submission_id": {"$in": [SUB_NS1, SUB_NS2]}})
    db.participant_badges.delete_many({"share_token": BADGE_TOKEN})
    print("DOWN: cleaned")
