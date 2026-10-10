"""
Iter-17: Program dates, launch-email attribution+report, volunteer anniversaries, public sessions.

Preconditions: run `python3 /app/backend/tests/qa_session.py up` (sets admin cookie session_token=qa_tok_123).
Mutating admin requests require header X-Requested-With: XMLHttpRequest.
"""
import os
import sys
import asyncio
import importlib
from datetime import datetime, date, timedelta, timezone

import pytest
import requests

_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MDB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
COOKIES = {"session_token": "qa_tok_123"}
HDR = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}

QA_LAUNCH_EMAIL = "qa.launch@example.com"
QA_ANNIV_EMAIL = "qa.anniv@example.com"
QA_PROG_TITLE = "QA Clone Program"
CLONE_SLUG = "caring-sisters-clone"


# ---------- Shared fixtures ----------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update(HDR)
    s.cookies.update(COOKIES)
    return s


@pytest.fixture(scope="module")
def target_program(api):
    """A real program we can mutate dates on. Pick 'business-elevation-lab'."""
    p = MDB.programs.find_one({"slug": "business-elevation-lab"}, {"_id": 0})
    assert p, "seed program missing"
    yield p
    # cleanup: restore dates to blank
    MDB.programs.update_one({"id": p["id"]}, {"$set": {"start_date": "", "end_date": "", "schedule": ""}})


def _payload_from(p: dict, **overrides) -> dict:
    """Build a valid ProgramIn payload from existing program."""
    base = {
        "title": p["title"], "category": p.get("category", ""), "image_url": p.get("image_url", ""),
        "summary": p.get("summary", ""), "body": p.get("body", ""), "goals": p.get("goals", []),
        "impact": p.get("impact", []), "cta_text": p.get("cta_text", "Get Involved"),
        "cta_link": p.get("cta_link", "/volunteer"), "published": p.get("published", True),
        "gallery": p.get("gallery", []), "testimonials": p.get("testimonials", []),
        "home_testimonial_ids": p.get("home_testimonial_ids", []),
        "capacity": p.get("capacity", 0), "waitlist_mode": p.get("waitlist_mode", "claim"),
        "start_date": p.get("start_date", ""), "end_date": p.get("end_date", ""),
        "schedule": p.get("schedule", ""),
    }
    base.update(overrides)
    return base


# ---------- Program dates ----------
class TestProgramDates:
    def test_persists(self, api, target_program):
        body = _payload_from(target_program, start_date="2026-12-01", end_date="2026-12-20", schedule="Tuesdays 6-8pm")
        r = api.put(f"{BASE}/api/admin/programs/{target_program['id']}", json=body)
        assert r.status_code == 200, r.text
        got = r.json()
        assert got["start_date"] == "2026-12-01"
        assert got["end_date"] == "2026-12-20"
        assert got["schedule"] == "Tuesdays 6-8pm"
        # verify via public program endpoint
        pub = requests.get(f"{BASE}/api/programs/{got['slug']}").json()
        assert pub["start_date"] == "2026-12-01"

    def test_invalid_date_400(self, api, target_program):
        body = _payload_from(target_program, start_date="abc", end_date="")
        r = api.put(f"{BASE}/api/admin/programs/{target_program['id']}", json=body)
        assert r.status_code == 400

    def test_end_before_start_400(self, api, target_program):
        body = _payload_from(target_program, start_date="2026-05-10", end_date="2026-05-01")
        r = api.put(f"{BASE}/api/admin/programs/{target_program['id']}", json=body)
        assert r.status_code == 400

    def test_end_without_start_400(self, api, target_program):
        body = _payload_from(target_program, start_date="", end_date="2026-05-01")
        r = api.put(f"{BASE}/api/admin/programs/{target_program['id']}", json=body)
        assert r.status_code == 400


# ---------- Public /api/sessions ----------
class TestPublicSessions:
    @pytest.fixture(scope="class")
    def seeds(self, api):
        """Create 3 programs: future (dated), past (dated), unpublished (dated)."""
        today = date.today()
        future_s = (today + timedelta(days=10)).isoformat()
        future_e = (today + timedelta(days=20)).isoformat()
        past_s = (today - timedelta(days=30)).isoformat()
        past_e = (today - timedelta(days=20)).isoformat()
        pids = []
        for title, pub, sd, ed in [
            ("QA Sess Future", True, future_s, future_e),
            ("QA Sess Past", True, past_s, past_e),
            ("QA Sess Unpub", False, future_s, future_e),
        ]:
            body = {
                "title": title, "category": "", "image_url": "", "summary": "", "body": "",
                "goals": [], "impact": [], "cta_text": "Get Involved", "cta_link": "/volunteer",
                "published": pub, "gallery": [], "testimonials": [], "home_testimonial_ids": [],
                "capacity": 10, "waitlist_mode": "claim",
                "start_date": sd, "end_date": ed, "schedule": "weekly",
            }
            r = api.post(f"{BASE}/api/admin/programs", json=body)
            assert r.status_code == 200, r.text
            pids.append(r.json()["id"])
        yield pids, future_s
        for pid in pids:
            api.delete(f"{BASE}/api/admin/programs/{pid}")

    def test_only_future_published(self, seeds):
        pids, future_s = seeds
        r = requests.get(f"{BASE}/api/sessions")
        assert r.status_code == 200
        items = r.json()["items"]
        titles = [i["title"] for i in items]
        assert "QA Sess Future" in titles
        assert "QA Sess Past" not in titles
        assert "QA Sess Unpub" not in titles
        # fields
        future_item = next(i for i in items if i["title"] == "QA Sess Future")
        for k in ("id", "slug", "title", "start_date", "end_date", "schedule", "capacity", "seats_left", "full"):
            assert k in future_item, f"missing {k}"
        # sorted
        starts = [i["start_date"] for i in items]
        assert starts == sorted(starts)


# ---------- Launch email attribution ----------
class TestLaunchAttribution:
    @pytest.fixture(scope="class")
    def clone_prog(self, api):
        # Ensure a 'caring-sisters-clone' program exists
        existing = MDB.programs.find_one({"slug": CLONE_SLUG}, {"_id": 0})
        if existing:
            yield existing, False
        else:
            body = {
                "title": QA_PROG_TITLE, "category": "", "image_url": "", "summary": "", "body": "",
                "goals": [], "impact": [], "cta_text": "Get Involved", "cta_link": "/volunteer",
                "published": True, "gallery": [], "testimonials": [], "home_testimonial_ids": [],
                "capacity": 20, "waitlist_mode": "claim",
                "start_date": "", "end_date": "", "schedule": "",
            }
            r = api.post(f"{BASE}/api/admin/programs", json=body)
            assert r.status_code == 200
            doc = r.json()
            # Force slug to caring-sisters-clone directly in DB
            MDB.programs.update_one({"id": doc["id"]}, {"$set": {"slug": CLONE_SLUG}})
            doc["slug"] = CLONE_SLUG
            yield doc, True
            api.delete(f"{BASE}/api/admin/programs/{doc['id']}")

    @pytest.fixture(autouse=True)
    def _cleanup_each(self, clone_prog):
        pid = clone_prog[0]["id"]
        MDB.session_launch_emails.delete_many({"program_id": pid})
        MDB.submissions.delete_many({"data.email": {"$regex": "^qa\\."}})
        yield
        MDB.session_launch_emails.delete_many({"program_id": pid})
        MDB.submissions.delete_many({"data.email": {"$regex": "^qa\\."}})

    def _signup(self, email):
        return requests.post(
            f"{BASE}/api/programs/{CLONE_SLUG}/signup",
            json={"name": "QA Launch", "email": email, "phone": "", "message": ""},
        )

    def test_attribution_sets_from_launch_and_converted_at(self, clone_prog):
        p, _ = clone_prog
        MDB.session_launch_emails.insert_one({
            "program_id": p["id"], "email": QA_LAUNCH_EMAIL,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        r = self._signup(QA_LAUNCH_EMAIL)
        assert r.status_code == 200, r.text
        sub = MDB.submissions.find_one({"data.email": QA_LAUNCH_EMAIL, "program_id": p["id"]})
        assert sub and sub.get("from_launch") is True
        le = MDB.session_launch_emails.find_one({"program_id": p["id"], "email": QA_LAUNCH_EMAIL})
        assert le.get("converted_at")
        assert le.get("submission_id") == sub["id"]

    def test_second_signup_does_not_double_count(self, clone_prog):
        p, _ = clone_prog
        MDB.session_launch_emails.insert_one({
            "program_id": p["id"], "email": QA_LAUNCH_EMAIL,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        self._signup(QA_LAUNCH_EMAIL)
        first = MDB.session_launch_emails.find_one({"program_id": p["id"], "email": QA_LAUNCH_EMAIL})
        import time
        time.sleep(1)
        self._signup(QA_LAUNCH_EMAIL)
        second = MDB.session_launch_emails.find_one({"program_id": p["id"], "email": QA_LAUNCH_EMAIL})
        assert second["converted_at"] == first["converted_at"], "converted_at should not change"
        assert second["submission_id"] == first["submission_id"]

    def test_old_launch_does_not_convert(self, clone_prog):
        p, _ = clone_prog
        old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        MDB.session_launch_emails.insert_one({"program_id": p["id"], "email": QA_LAUNCH_EMAIL, "at": old})
        r = self._signup(QA_LAUNCH_EMAIL)
        assert r.status_code == 200
        sub = MDB.submissions.find_one({"data.email": QA_LAUNCH_EMAIL, "program_id": p["id"]})
        assert sub and not sub.get("from_launch")
        le = MDB.session_launch_emails.find_one({"program_id": p["id"], "email": QA_LAUNCH_EMAIL})
        assert "converted_at" not in le

    def test_launch_results_report(self, api, clone_prog):
        p, _ = clone_prog
        MDB.session_launch_emails.insert_many([
            {"program_id": p["id"], "email": QA_LAUNCH_EMAIL, "at": datetime.now(timezone.utc).isoformat()},
            {"program_id": p["id"], "email": "qa.other@example.com", "at": datetime.now(timezone.utc).isoformat()},
        ])
        self._signup(QA_LAUNCH_EMAIL)
        r = api.get(f"{BASE}/api/admin/reports/launch-results")
        assert r.status_code == 200
        d = r.json()
        assert d["window_days"] == 30
        row = next((x for x in d["items"] if x["id"] == p["id"]), None)
        assert row, "row for QA program missing"
        assert row["emailed"] == 2
        assert row["signed_up"] == 1
        assert row["conversion"] == 50.0


# ---------- Volunteer anniversaries ----------
class TestAnniversaries:
    def setup_method(self):
        self._cleanup()
        # seed first-approved-hours exactly 2 years ago today, plus a recent one
        today = date.today()
        try:
            two_years = today.replace(year=today.year - 2).isoformat()
        except ValueError:
            # today is Feb 29 and year-2 isn't leap: fall back to Feb 28
            two_years = today.replace(year=today.year - 2, day=28).isoformat()
        MDB.volunteer_hours.insert_many([
            {"id": "qa_a1", "email": QA_ANNIV_EMAIL, "name": "QA Anniv", "status": "approved",
             "date": two_years, "hours": 5, "created_at": two_years + "T00:00:00+00:00", "scope": "all"},
            {"id": "qa_a2", "email": QA_ANNIV_EMAIL, "name": "QA Anniv", "status": "approved",
             "date": today.isoformat(), "hours": 3, "created_at": datetime.now(timezone.utc).isoformat(), "scope": "all"},
        ])

    def teardown_method(self):
        self._cleanup()

    def _cleanup(self):
        MDB.volunteer_hours.delete_many({"email": QA_ANNIV_EMAIL})
        MDB.volunteer_anniversaries.delete_many({"email": QA_ANNIV_EMAIL})
        MDB.volunteer_milestones.delete_many({"email": QA_ANNIV_EMAIL})

    def test_is_anniversary_feb29_leap_logic(self):
        sys.path.insert(0, "/app/backend")
        server = importlib.import_module("server")
        # 2027 is non-leap -> Feb 29 falls back to Feb 28
        assert server._is_anniversary("2024-02-29", date(2027, 2, 28)) is True
        # 2028 is leap -> Feb 29 only
        assert server._is_anniversary("2024-02-29", date(2028, 2, 28)) is False
        assert server._is_anniversary("2024-02-29", date(2028, 2, 29)) is True

    def test_send_anniversaries_creates_doc_and_idempotent(self):
        sys.path.insert(0, "/app/backend")
        server = importlib.import_module("server")
        _run(server._send_anniversaries())
        today = date.today()
        docs = list(MDB.volunteer_anniversaries.find({"email": QA_ANNIV_EMAIL}))
        assert len(docs) == 1, docs
        d = docs[0]
        assert d["year"] == today.year
        assert d["years"] == 2
        assert d.get("cert_token")
        tok = d["cert_token"]
        # re-run -> no new doc
        _run(server._send_anniversaries())
        docs2 = list(MDB.volunteer_anniversaries.find({"email": QA_ANNIV_EMAIL}))
        assert len(docs2) == 1
        # pdf fetch
        r = requests.get(f"{BASE}/api/certificates/anniversary/{tok}.pdf")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        # bad token
        r = requests.get(f"{BASE}/api/certificates/anniversary/bogus-token-xxx.pdf")
        assert r.status_code == 404

    def test_non_anniversary_skipped(self):
        # Replace seed with a date not matching today
        self._cleanup()
        not_today = (date.today() - timedelta(days=5)).replace(year=date.today().year - 2).isoformat()
        MDB.volunteer_hours.insert_one({
            "id": "qa_a3", "email": QA_ANNIV_EMAIL, "name": "QA", "status": "approved",
            "date": not_today, "hours": 2, "created_at": not_today + "T00:00:00+00:00", "scope": "all",
        })
        sys.path.insert(0, "/app/backend")
        server = importlib.import_module("server")
        _run(server._send_anniversaries())
        assert MDB.volunteer_anniversaries.count_documents({"email": QA_ANNIV_EMAIL}) == 0
