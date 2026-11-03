"""Iteration 54 — retest of hours fixes: DELETE requires removed, milestone re-award on restore/upward edit,
program change on portal entry updates activity. Own temp admin + TEST_ rows, cleaned by id."""
import os
import uuid
from datetime import datetime, timezone
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + "/api"
XHR = {"X-Requested-With": "XMLHttpRequest"}
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
SUF = uuid.uuid4().hex[:8]
ADMIN_UID, ADMIN_TOK = f"it54_admin_{SUF}", f"it54_admtok_{SUF}"
ADMIN = {"session_token": ADMIN_TOK}
TODAY = datetime.now(timezone.utc).date().isoformat()
YEAR = TODAY[:4]
created, emails = [], []


@pytest.fixture(scope="module", autouse=True)
def setup():
    db.users.insert_one({"user_id": ADMIN_UID, "email": f"it54_admin_{SUF}@example.com", "name": "TEST_ Admin", "role": "admin"})
    db.user_sessions.insert_one({"session_token": ADMIN_TOK, "user_id": ADMIN_UID, "expires_at": "2099-01-01T00:00:00+00:00"})
    yield
    db.volunteer_hours.delete_many({"id": {"$in": created}})
    db.volunteer_milestones.delete_many({"email": {"$in": emails}})
    db.user_sessions.delete_one({"session_token": ADMIN_TOK})
    db.users.delete_one({"user_id": ADMIN_UID})


def new_email():
    e = f"test_it54_{uuid.uuid4().hex[:8]}@example.com"
    emails.append(e)
    return e


def mk(email, hours=2.0, status="approved", portal=False, program=None):
    hid = str(uuid.uuid4())
    prog = program or db.programs.find_one({}, {"_id": 0, "id": 1, "title": 1})
    doc = {"id": hid, "name": "TEST_ It54", "email": email, "date": TODAY, "hours": hours, "note": "TEST_", "status": status,
           "leaderboard": False, "thanked": True, "created_at": datetime.now(timezone.utc).isoformat(),
           "program_id": prog["id"], "program": prog["title"]}
    if portal:
        doc.update({"source": "portal", "activity": "TEST_ Old Activity", "program": "TEST_ Old Activity"})
    db.volunteer_hours.insert_one(doc)
    created.append(hid)
    return hid


def post(hid, action, body=None):
    return requests.post(f"{API}/admin/volunteer-hours/{hid}/{action}", json=body or {}, cookies=ADMIN, headers=XHR)


def delete(hid):
    return requests.delete(f"{API}/admin/volunteer-hours/{hid}", cookies=ADMIN, headers=XHR)


def ms(email, scope="all", t=10):
    return db.volunteer_milestones.find_one({"email": email, "scope": scope, "threshold": t}, {"_id": 0})


# --- (2) DELETE only for removed entries ---
class TestDeleteGuard:
    @pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
    def test_delete_non_removed_400(self, status):
        hid = mk(new_email(), status=status)
        r = delete(hid)
        assert r.status_code == 400, r.text
        assert "Remove the entry first" in r.json()["detail"]
        assert db.volunteer_hours.find_one({"id": hid})["status"] == status

    def test_delete_removed_ok_then_404(self):
        hid = mk(new_email())
        assert post(hid, "remove").status_code == 200
        r = delete(hid)
        assert r.status_code == 200 and r.json()["ok"] is True
        assert db.volunteer_hours.find_one({"id": hid}) is None
        assert delete(hid).status_code == 404


# --- (3) milestone re-award ---
class TestMilestoneReaward:
    def test_remove_then_restore_reawards(self):
        e = new_email()
        h1 = mk(e, hours=12.0)
        # trigger an award by doing a no-op-ish recheck: move another entry through pending
        h2 = mk(e, hours=1.0)
        assert post(h2, "pending").status_code == 200
        assert ms(e) is not None, "recheck should award all-time 10h for 12 approved hours"
        assert ms(e, f"year:{YEAR}") is not None
        assert post(h1, "remove", {"reason": "TEST_"}).status_code == 200
        assert ms(e) is None and ms(e, f"year:{YEAR}") is None
        assert post(h1, "restore").status_code == 200
        m = ms(e)
        assert m is not None and m["label"] == "10 Hours All-Time"
        assert ms(e, f"year:{YEAR}") is not None
        assert ms(e, t=50) is None

    def test_upward_edit_awards(self):
        e = new_email()
        hid = mk(e, hours=5.0)
        r = requests.put(f"{API}/admin/volunteer-hours/{hid}", json={"hours": 11, "date": TODAY}, cookies=ADMIN, headers=XHR)
        assert r.status_code == 200, r.text
        assert ms(e) is not None
        r = requests.put(f"{API}/admin/volunteer-hours/{hid}", json={"hours": 4, "date": TODAY}, cookies=ADMIN, headers=XHR)
        assert r.status_code == 200
        assert ms(e) is None

    def test_pending_entries_not_counted(self):
        e = new_email()
        hid = mk(e, hours=12.0, status="pending")
        r = requests.put(f"{API}/admin/volunteer-hours/{hid}", json={"hours": 13, "date": TODAY}, cookies=ADMIN, headers=XHR)
        assert r.status_code == 200
        assert ms(e) is None


# --- (4) program change on portal entry with activity ---
class TestPortalProgramChange:
    def test_program_change_updates_activity(self):
        progs = list(db.programs.find({}, {"_id": 0, "id": 1, "title": 1}).limit(2))
        if len(progs) < 2:
            pytest.skip("need 2 programs")
        hid = mk(new_email(), portal=True, program=progs[0])
        r = requests.put(f"{API}/admin/volunteer-hours/{hid}", json={"hours": 2, "date": TODAY, "program_id": progs[1]["id"],
                                                                    "activity": "TEST_ Old Activity"}, cookies=ADMIN, headers=XHR)
        assert r.status_code == 200, r.text
        row = db.volunteer_hours.find_one({"id": hid}, {"_id": 0})
        assert row["program_id"] == progs[1]["id"]
        assert row["program"] == progs[1]["title"] and row["activity"] == progs[1]["title"]
        assert row["edits"][-1]["changes"]["activity"] == ["TEST_ Old Activity", progs[1]["title"]]
