"""Iteration 11 tests: program capacity+waitlist, overdue signups, milestones, year-in-review."""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
COOKIE = {"session_token": "qa_tok_123"}
H = {"X-Requested-With": "XMLHttpRequest"}

mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

# Pick an existing published program (the problem-statement slug 'caring-sisters-clone' doesn't exist)
PROG_SLUG = "wellness-workshops"
PROG = mdb.programs.find_one({"slug": PROG_SLUG})
PROG_ID = PROG["id"]
ORIG_CAP = PROG.get("capacity", 0)

TEST_EMAILS = []  # created @example.com emails to clean up


def _program_payload(**over):
    """Build a full ProgramIn payload from the existing program."""
    base = {
        "title": PROG["title"],
        "category": PROG.get("category", ""),
        "image_url": PROG.get("image_url", ""),
        "summary": PROG.get("summary", ""),
        "body": PROG.get("body", ""),
        "goals": PROG.get("goals", []),
        "impact": PROG.get("impact", []),
        "cta_text": PROG.get("cta_text", "Get Involved"),
        "cta_link": PROG.get("cta_link", "/volunteer"),
        "published": True,
        "capacity": 0,
        "gallery": PROG.get("gallery", []),
        "testimonials": PROG.get("testimonials", []),
        "home_testimonial_ids": PROG.get("home_testimonial_ids", []),
    }
    base.update(over)
    return base


def _set_capacity(cap):
    r = requests.put(f"{API}/admin/programs/{PROG_ID}", json=_program_payload(capacity=cap), cookies=COOKIE, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def _signup(name_suffix=""):
    em = f"test_{uuid.uuid4().hex[:8]}@example.com"
    TEST_EMAILS.append(em)
    r = requests.post(f"{API}/programs/{PROG_SLUG}/signup",
                      json={"name": f"QA Tester{name_suffix}", "email": em, "phone": "", "message": ""})
    return r, em


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    # Reset capacity
    try:
        _set_capacity(ORIG_CAP)
    except Exception:
        pass
    # Remove any test submissions
    mdb.submissions.delete_many({"data.email": {"$regex": "example.com$"}})
    mdb.volunteer_hours.delete_many({"email": {"$regex": "example.com$"}})
    mdb.volunteer_milestones.delete_many({"email": {"$regex": "example.com$"}})
    mdb.volunteer_thanks.delete_many({"email": {"$regex": "example.com$"}})
    # Reset yir
    mdb.settings.update_one({"key": "site"}, {"$pull": {"yir_public": 2026}})


# ---------- Program capacity + waitlist ----------
class TestCapacityWaitlist:
    def test_capacity_0_hides_seats_fields(self):
        _set_capacity(0)
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert "seats_left" not in p and "full" not in p
        assert p.get("capacity", 0) == 0

    def test_capacity_returns_seats_left_full(self):
        _set_capacity(2)
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert p["capacity"] == 2
        assert p["seats_left"] == 2
        assert p["full"] is False
        # listing should also include seats_left
        items = requests.get(f"{API}/programs").json()["items"]
        row = next(x for x in items if x["slug"] == PROG_SLUG)
        assert row["seats_left"] == 2 and row["full"] is False

    def test_signup_fills_seats_then_waitlist(self):
        _set_capacity(2)
        # clear prior to isolate
        mdb.submissions.delete_many({"program_id": PROG_ID, "data.email": {"$regex": "example.com$"}})
        r1, _ = _signup("A")
        assert r1.status_code == 200 and r1.json()["waitlist"] is False
        r2, _ = _signup("B")
        assert r2.status_code == 200 and r2.json()["waitlist"] is False
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert p["seats_left"] == 0 and p["full"] is True
        r3, em3 = _signup("C")
        assert r3.status_code == 200 and r3.json()["waitlist"] is True
        s = mdb.submissions.find_one({"data.email": em3})
        assert s["waitlist"] is True
        assert s["data"].get("list") == "Waitlist"

    def test_not_fit_frees_seat_and_enrolled_waitlist_consumes(self):
        """Insert signups directly to DB (avoid 5-sign-up/min rate limit); exercise _seats_taken logic."""
        _set_capacity(2)
        mdb.submissions.delete_many({"program_id": PROG_ID, "data.email": {"$regex": "example.com$"}})

        def _insert(stage=None, waitlist=False):
            em = f"test_{uuid.uuid4().hex[:6]}@example.com"
            doc = {"id": str(uuid.uuid4()), "type": "program_signup", "program_id": PROG_ID,
                   "waitlist": waitlist, "data": {"program": PROG["title"], "program_slug": PROG_SLUG,
                                                   "name": "QA", "email": em, "phone": "", "message": ""},
                   "read": False, "created_at": datetime.now(timezone.utc).isoformat()}
            if waitlist:
                doc["data"]["list"] = "Waitlist"
            if stage:
                doc["stage"] = stage
            mdb.submissions.insert_one(doc)
            return doc["id"], em

        id1, em1 = _insert()
        _insert()
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert p["full"] is True and p["seats_left"] == 0
        # Mark one as not_fit -> frees a seat
        pr = requests.put(f"{API}/admin/submissions/{id1}/stage", json={"stage": "not_fit"}, cookies=COOKIE, headers=H)
        assert pr.status_code == 200, pr.text
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert p["seats_left"] == 1
        # Add waitlisted entry; promoting it to enrolled should consume a seat
        id_wl, _ = _insert(waitlist=True)
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert p["seats_left"] == 1  # waitlisted doesn't count yet
        pr = requests.put(f"{API}/admin/submissions/{id_wl}/stage", json={"stage": "enrolled"}, cookies=COOKIE, headers=H)
        assert pr.status_code == 200
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert p["seats_left"] == 0 and p["full"] is True


# ---------- Overdue counts + reminders ----------
class TestOverdueAndReminders:
    def test_overdue_count_includes_old_new_signup(self):
        # Seed an "old" program_signup directly in Mongo
        old_id = str(uuid.uuid4())
        em = f"TEST_overdue_{uuid.uuid4().hex[:6]}@example.com"
        TEST_EMAILS.append(em)
        old_dt = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        mdb.submissions.insert_one({
            "id": old_id, "type": "program_signup", "program_id": PROG_ID,
            "data": {"program": PROG["title"], "program_slug": PROG_SLUG, "name": "OldTester", "email": em, "phone": "", "message": ""},
            "read": False, "created_at": old_dt, "stage": "new",
        })
        r = requests.get(f"{API}/submissions/counts", cookies=COOKIE, headers=H)
        assert r.status_code == 200
        counts = r.json()
        assert counts["program_signup"]["overdue"] >= 1
        # cleanup
        mdb.submissions.delete_one({"id": old_id})

    def test_send_reminders_requires_auth(self):
        r = requests.post(f"{API}/admin/signups/send-reminders")
        assert r.status_code == 401


# ---------- Volunteer milestones ----------
class TestMilestones:
    def test_bug_milestones_symbol_shadowed(self):
        """BUG: `MILESTONES = [25, 50, 100]` on line 3932 of server.py shadows the volunteer
        tuple `MILESTONES = (10, 50, 100)` on line 3590. Volunteer badges never trigger at 10h."""
        import sys as _sys
        _sys.path.insert(0, "/app/backend")
        from server import VOL_MILESTONES as M
        assert M == (10, 50, 100), f"EXPECTED volunteer MILESTONES=(10,50,100), GOT {M} — shadowed by fundraising MILESTONES at line 3932"

    def test_milestones_recorded_once(self):
        em = f"test_milestone_{uuid.uuid4().hex[:6]}@example.com"
        TEST_EMAILS.append(em)
        year = str(datetime.now(timezone.utc).year)
        today = datetime.now(timezone.utc).date().isoformat()
        # Use 26 hrs so we cross the shadowed-25h threshold too (survives bug).
        hid = str(uuid.uuid4())
        mdb.volunteer_hours.insert_one({
            "id": hid, "email": em, "name": "QA Milestone", "hours": 26, "program": "QA", "note": "", "date": today,
            "leaderboard": False, "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{API}/admin/volunteer-hours/{hid}/approve", cookies=COOKIE, headers=H)
        assert r.status_code == 200, r.text
        import time
        for _ in range(15):
            time.sleep(1)
            if mdb.volunteer_milestones.count_documents({"email": em}) >= 2:
                break
        docs = list(mdb.volunteer_milestones.find({"email": em}))
        scopes = {d["scope"] for d in docs}
        thresholds = sorted({d["threshold"] for d in docs})
        assert "all" in scopes and f"year:{year}" in scopes, f"got scopes={scopes}"
        # With buggy MILESTONES=[25,50,100] only 25 is crossed at 26 hrs
        assert thresholds == [10], f"got thresholds={thresholds}"
        # Idempotency: approve another small batch, no new milestones
        hid2 = str(uuid.uuid4())
        mdb.volunteer_hours.insert_one({
            "id": hid2, "email": em, "name": "QA Milestone", "hours": 1, "program": "QA", "note": "", "date": today,
            "leaderboard": False, "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{API}/admin/volunteer-hours/{hid2}/approve", cookies=COOKIE, headers=H)
        assert r.status_code == 200
        time.sleep(3)
        n = mdb.volunteer_milestones.count_documents({"email": em})
        assert n == 2, f"Milestones duplicated: found {n}"


# ---------- Year in Review ----------
class TestYearInReview:
    def test_admin_requires_auth(self):
        assert requests.get(f"{API}/admin/year-in-review/2026").status_code == 401
        assert requests.put(f"{API}/admin/year-in-review/2026", json={"public": True}).status_code == 401

    def test_public_404_until_published_then_200(self):
        # Make sure not published
        mdb.settings.update_one({"key": "site"}, {"$pull": {"yir_public": 2026}})
        assert requests.get(f"{API}/year-in-review/2026").status_code == 404
        # Admin view
        r = requests.get(f"{API}/admin/year-in-review/2026", cookies=COOKIE, headers=H)
        assert r.status_code == 200
        d = r.json()
        for k in ("donations_total", "donors", "volunteer_hours", "volunteers", "stories", "signups", "public"):
            assert k in d
        assert d["public"] is False
        # Publish
        pr = requests.put(f"{API}/admin/year-in-review/2026", json={"public": True}, cookies=COOKIE, headers=H)
        assert pr.status_code == 200 and pr.json()["public"] is True
        r2 = requests.get(f"{API}/year-in-review/2026")
        assert r2.status_code == 200
        # Unpublish
        pr = requests.put(f"{API}/admin/year-in-review/2026", json={"public": False}, cookies=COOKIE, headers=H)
        assert pr.status_code == 200
        assert requests.get(f"{API}/year-in-review/2026").status_code == 404
