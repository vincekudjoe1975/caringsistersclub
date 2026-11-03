"""Iteration 53 — Admin correct / remove volunteer hours.
PUT /api/admin/volunteer-hours/{id}, POST .../{id}/remove|restore|pending, DELETE .../{id}, GET /api/admin/volunteer-hours (items/removed),
and that removed entries stop counting in member totals, public summary, leaderboard and CSV, plus milestone recheck.
Creates its own temp admin + member + session tokens and TEST_ hour rows; cleans up by id."""
import os
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"
XHR = {"X-Requested-With": "XMLHttpRequest"}
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

SUF = uuid.uuid4().hex[:8]
ADMIN_UID, ADMIN_TOK = f"it53_admin_{SUF}", f"it53_admtok_{SUF}"
MEM_UID, MEM_TOK = f"it53_mem_{SUF}", f"it53_memtok_{SUF}"
MEM_EMAIL = f"test_it53_{SUF}@example.com"
ADMIN = {"session_token": ADMIN_TOK}
MEMBER = {"session_token": MEM_TOK}
TODAY = datetime.now(timezone.utc).date()
YEAR = str(TODAY.year)
created_hours = []


@pytest.fixture(scope="module", autouse=True)
def setup_users():
    exp = "2099-01-01T00:00:00+00:00"
    db.users.insert_one({"user_id": ADMIN_UID, "email": f"it53_admin_{SUF}@example.com", "name": "TEST_ Admin", "role": "admin"})
    db.users.insert_one({"user_id": MEM_UID, "email": MEM_EMAIL, "name": "TEST_ Member Sister", "role": "pending", "member_status": "active",
                         "portal_welcome_seen_at": "2026-01-01T00:00:00+00:00"})
    db.user_sessions.insert_many([{"session_token": ADMIN_TOK, "user_id": ADMIN_UID, "expires_at": exp},
                                  {"session_token": MEM_TOK, "user_id": MEM_UID, "expires_at": exp}])
    yield
    db.volunteer_hours.delete_many({"id": {"$in": created_hours}})
    db.volunteer_milestones.delete_many({"email": MEM_EMAIL})
    db.user_sessions.delete_many({"session_token": {"$in": [ADMIN_TOK, MEM_TOK]}})
    db.users.delete_many({"user_id": {"$in": [ADMIN_UID, MEM_UID]}})


def mk(hours=2.0, status="approved", portal=False, date=None, program_id=None):
    hid = str(uuid.uuid4())
    prog = db.programs.find_one({"published": True}, {"_id": 0, "id": 1, "title": 1}) or {"id": "x", "title": "X"}
    doc = {"id": hid, "name": "TEST_ Member Sister", "email": MEM_EMAIL, "date": date or TODAY.isoformat(), "hours": hours,
           "note": "TEST_ note", "status": status, "leaderboard": False, "created_at": datetime.now(timezone.utc).isoformat(), "thanked": True}
    if portal:
        doc.update({"user_id": MEM_UID, "source": "portal", "program_id": "", "program": "TEST_ Activity", "activity": "TEST_ Activity"})
    else:
        doc.update({"program_id": program_id or prog["id"], "program": prog["title"]})
    db.volunteer_hours.insert_one(doc)
    created_hours.append(hid)
    return hid


def get_row(hid):
    return db.volunteer_hours.find_one({"id": hid}, {"_id": 0})


def put(hid, body, cookies=ADMIN):
    return requests.put(f"{API}/admin/volunteer-hours/{hid}", json=body, cookies=cookies, headers=XHR)


def post(hid, action, body=None, cookies=ADMIN):
    return requests.post(f"{API}/admin/volunteer-hours/{hid}/{action}", json=body or {}, cookies=cookies, headers=XHR)


# --- Auth ---
class TestAuth:
    def test_non_admin_blocked(self):
        hid = mk()
        assert put(hid, {"hours": 3, "date": TODAY.isoformat()}, cookies=MEMBER).status_code in (401, 403)
        assert post(hid, "remove", cookies=MEMBER).status_code in (401, 403)
        assert requests.delete(f"{API}/admin/volunteer-hours/{hid}", cookies=MEMBER, headers=XHR).status_code in (401, 403)
        assert requests.put(f"{API}/admin/volunteer-hours/{hid}", json={"hours": 3, "date": TODAY.isoformat()}, headers=XHR).status_code in (401, 403)
        assert get_row(hid)["hours"] == 2.0


# --- Edit ---
class TestEdit:
    def test_edit_persists_and_logs(self):
        hid = mk(hours=2.0)
        d = (TODAY - timedelta(days=3)).isoformat()
        r = put(hid, {"hours": 3.5, "date": d, "note": "  TEST_ corrected  "})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["hours"] == 3.5 and j["date"] == d and j["note"] == "TEST_ corrected"
        assert "_id" not in j
        row = get_row(hid)
        assert row["hours"] == 3.5 and len(row["edits"]) == 1
        assert row["edits"][0]["changes"]["hours"] == [2.0, 3.5]
        assert row["edits"][0]["by"] == f"it53_admin_{SUF}@example.com"
        assert row["status"] == "approved"

    def test_no_change_no_log(self):
        hid = mk(hours=2.0)
        row = get_row(hid)
        r = put(hid, {"hours": 2.0, "date": row["date"], "note": row["note"], "program_id": row["program_id"]})
        assert r.status_code == 200
        assert "edits" not in get_row(hid)

    @pytest.mark.parametrize("body,code", [
        ({"hours": 0, "date": None}, 400), ({"hours": 25, "date": None}, 400),
        ({"hours": 2, "date": "2026-13-40"}, 400), ({"hours": 2, "date": "FUTURE"}, 400),
        ({"hours": 2, "date": None, "program_id": "nope-not-a-program"}, 400)])
    def test_validation(self, body, code):
        hid = mk()
        b = dict(body)
        if b["date"] is None:
            b["date"] = TODAY.isoformat()
        elif b["date"] == "FUTURE":
            b["date"] = (TODAY + timedelta(days=5)).isoformat()
        r = put(hid, b)
        assert r.status_code == code, r.text
        assert isinstance(r.json().get("detail"), str)
        assert get_row(hid)["hours"] == 2.0

    def test_edit_missing_404(self):
        assert put("does-not-exist", {"hours": 2, "date": TODAY.isoformat()}).status_code == 404

    def test_edit_portal_activity(self):
        hid = mk(portal=True)
        r = put(hid, {"hours": 1.5, "date": TODAY.isoformat(), "activity": "TEST_ New Activity"})
        assert r.status_code == 200, r.text
        row = get_row(hid)
        assert row["activity"] == "TEST_ New Activity" and row["program"] == "TEST_ New Activity" and row["hours"] == 1.5

    def test_edit_program_change(self):
        progs = list(db.programs.find({}, {"_id": 0, "id": 1, "title": 1}).limit(2))
        if len(progs) < 2:
            pytest.skip("need 2 programs")
        hid = mk(program_id=progs[0]["id"])
        r = put(hid, {"hours": 2, "date": TODAY.isoformat(), "program_id": progs[1]["id"]})
        assert r.status_code == 200
        row = get_row(hid)
        assert row["program_id"] == progs[1]["id"] and row["program"] == progs[1]["title"]

    def test_edit_lowers_member_total(self):
        before = requests.get(f"{API}/members/hours", cookies=MEMBER).json()["total"]
        hid = mk(hours=4.0)
        assert requests.get(f"{API}/members/hours", cookies=MEMBER).json()["total"] == round(before + 4, 2)
        put(hid, {"hours": 1.0, "date": TODAY.isoformat()})
        assert requests.get(f"{API}/members/hours", cookies=MEMBER).json()["total"] == round(before + 1, 2)


# --- Milestone recheck ---
class TestMilestones:
    def test_edit_drops_milestone(self):
        hid = mk(hours=12.0)
        for scope in ("all", f"year:{YEAR}"):
            db.volunteer_milestones.update_one({"email": MEM_EMAIL, "scope": scope, "threshold": 10},
                                               {"$setOnInsert": {"hours": 12, "label": "TEST_", "awarded_at": "x"}}, upsert=True)
        r = put(hid, {"hours": 1.0, "date": TODAY.isoformat()})
        assert r.status_code == 200
        total = sum(x["hours"] for x in db.volunteer_hours.find({"email": MEM_EMAIL, "status": "approved"}))
        left = db.volunteer_milestones.count_documents({"email": MEM_EMAIL, "threshold": 10})
        if total < 10:
            assert left == 0

    def test_remove_drops_milestone(self):
        hid = mk(hours=20.0)
        db.volunteer_milestones.update_one({"email": MEM_EMAIL, "scope": "all", "threshold": 10},
                                           {"$setOnInsert": {"hours": 20, "label": "TEST_", "awarded_at": "x"}}, upsert=True)
        assert post(hid, "remove", {"reason": "TEST_ dup"}).status_code == 200
        total = sum(x["hours"] for x in db.volunteer_hours.find({"email": MEM_EMAIL, "status": "approved"}))
        if total < 10:
            assert db.volunteer_milestones.count_documents({"email": MEM_EMAIL, "scope": "all", "threshold": 10}) == 0


# --- Remove / restore / pending / delete ---
class TestRemoveRestore:
    def test_remove_flow(self):
        summ0 = requests.get(f"{API}/volunteer-hours/summary").json()["total_hours"]
        hid = mk(hours=3.0)
        summ1 = requests.get(f"{API}/volunteer-hours/summary").json()["total_hours"]
        assert round(summ1 - summ0, 1) == 3.0
        r = post(hid, "remove", {"reason": "  TEST_ duplicate  "})
        assert r.status_code == 200 and r.json()["ok"] is True
        row = get_row(hid)
        assert row["status"] == "removed" and row["prev_status"] == "approved"
        assert row["removed_reason"] == "TEST_ duplicate" and row["removed_by"] == f"it53_admin_{SUF}@example.com"
        lst = requests.get(f"{API}/admin/volunteer-hours", cookies=ADMIN).json()
        assert hid not in [x["id"] for x in lst["items"]] and hid in [x["id"] for x in lst["removed"]]
        mine = requests.get(f"{API}/members/hours", cookies=MEMBER).json()
        assert hid not in [x["id"] for x in mine["entries"]]
        assert round(requests.get(f"{API}/volunteer-hours/summary").json()["total_hours"], 1) == round(summ0, 1)
        board = requests.get(f"{API}/admin/members/hours", cookies=ADMIN).json()["leaderboard"]
        me = next((b for b in board if b["email"] == MEM_EMAIL), None)
        if me:
            assert me["approved"] == round(sum(x["hours"] for x in db.volunteer_hours.find({"email": MEM_EMAIL, "status": "approved"})), 2)
        csv = requests.get(f"{API}/admin/members/hours.csv", cookies=ADMIN).text
        assert "TEST_ duplicate" not in csv
        # remove again -> 400, edit removed -> 404
        assert post(hid, "remove").status_code == 400
        assert put(hid, {"hours": 2, "date": TODAY.isoformat()}).status_code == 404
        # restore -> back to approved
        assert post(hid, "restore").status_code == 200
        row = get_row(hid)
        assert row["status"] == "approved" and "removed_at" not in row and "prev_status" not in row
        assert post(hid, "restore").status_code == 400

    def test_remove_without_body(self):
        hid = mk(status="pending")
        r = requests.post(f"{API}/admin/volunteer-hours/{hid}/remove", cookies=ADMIN, headers=XHR)
        assert r.status_code == 200, r.text
        assert get_row(hid)["status"] == "removed"
        assert post(hid, "restore").status_code == 200
        assert get_row(hid)["status"] == "pending"

    def test_back_to_pending(self):
        hid = mk(status="approved")
        assert post(hid, "pending").status_code == 200
        assert get_row(hid)["status"] == "pending"
        assert post(hid, "pending").status_code == 400
        assert post(hid, "approve").status_code == 200
        assert get_row(hid)["status"] == "approved"
        hid2 = mk(status="rejected")
        assert post(hid2, "pending").status_code == 200

    def test_invalid_action_and_missing(self):
        hid = mk()
        assert post(hid, "explode").status_code == 400
        assert post("nope-missing", "remove").status_code == 404
        assert post("nope-missing", "restore").status_code == 404

    def test_delete_forever(self):
        hid = mk()
        post(hid, "remove")
        r = requests.delete(f"{API}/admin/volunteer-hours/{hid}", cookies=ADMIN, headers=XHR)
        assert r.status_code == 200 and r.json()["ok"] is True
        assert get_row(hid) is None
        assert requests.delete(f"{API}/admin/volunteer-hours/{hid}", cookies=ADMIN, headers=XHR).status_code == 404
