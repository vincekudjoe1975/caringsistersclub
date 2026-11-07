# Iter64: Open questions (staff visibility/answered/reopen) + member FAQ + club team badge migration
import os
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
H = {"X-Requested-With": "XMLHttpRequest"}


def s(tok):
    x = requests.Session()
    x.headers.update(H)
    x.cookies.set("session_token", tok)
    return x


OWNER, STAFF, STAFF2, CONTENT, MEM, PEND = (s(t) for t in ("qa64_owner_tok", "qa64_staff_tok", "qa64_staff2_tok", "qa64_content_tok", "qa64_mem_tok", "qa64_pending_tok"))
STATE = {}


@pytest.fixture(scope="module", autouse=True)
def questions():
    r1 = MEM.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa64_staff", "text": "TEST_QA64 How do I sign up for events?"})
    r2 = MEM.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa64_staff2", "text": "TEST_QA64 Where is the meetup?"})
    assert r1.status_code == 200 and r2.status_code == 200, (r1.text, r2.text)
    STATE["q1"], STATE["q2"] = r1.json()["id"], r2.json()["id"]
    yield
    OWNER.put(f"{BASE_URL}/api/admin/team-questions/settings", json={"all_staff": False})


def ids(sess):
    r = sess.get(f"{BASE_URL}/api/admin/team-questions")
    assert r.status_code == 200, r.text
    return {q["id"] for q in r.json()}


class TestMigration:
    def test_key_exists_and_admins_badged(self):
        assert db.scheduled_runs.find_one({"key": "migrate:club_team_badges_2026_06"})
        for e in ("vincekudjoe@gmail.com", "caringsistersclub@gmail.com"):
            u = db.users.find_one({"email": e}, {"club_team_badge": 1})
            assert u and u.get("club_team_badge") is True


class TestVisibility:
    def test_owner_sees_all(self):
        got = ids(OWNER)
        assert STATE["q1"] in got and STATE["q2"] in got

    def test_staff_sees_own_only(self):
        got = ids(STAFF)
        assert STATE["q1"] in got and STATE["q2"] not in got
        assert STATE["q1"] not in ids(STAFF2) and STATE["q2"] in ids(STAFF2)

    def test_content_level_access_shared(self):
        assert ids(CONTENT).isdisjoint({STATE["q1"], STATE["q2"]})
        assert CONTENT.get(f"{BASE_URL}/api/admin/faq").status_code == 200

    def test_member_forbidden(self):
        assert MEM.get(f"{BASE_URL}/api/admin/team-questions").status_code in (401, 403)

    def test_settings_get(self):
        assert OWNER.get(f"{BASE_URL}/api/admin/team-questions/settings").json() == {"all_staff": False, "can_edit": True}
        assert STAFF.get(f"{BASE_URL}/api/admin/team-questions/settings").json()["can_edit"] is False

    def test_settings_put_owner_only(self):
        assert STAFF.put(f"{BASE_URL}/api/admin/team-questions/settings", json={"all_staff": True}).status_code == 403
        assert CONTENT.put(f"{BASE_URL}/api/admin/team-questions/settings", json={"all_staff": True}).status_code == 403

    def test_all_staff_toggle(self):
        r = OWNER.put(f"{BASE_URL}/api/admin/team-questions/settings", json={"all_staff": True})
        assert r.status_code == 200 and r.json()["all_staff"] is True
        assert {STATE["q1"], STATE["q2"]} <= ids(STAFF)
        assert {STATE["q1"], STATE["q2"]} <= ids(CONTENT)
        OWNER.put(f"{BASE_URL}/api/admin/team-questions/settings", json={"all_staff": False})
        assert STATE["q2"] not in ids(STAFF)


class TestAnswered:
    def test_mark_outside_scope_404(self):
        r = STAFF.post(f"{BASE_URL}/api/admin/team-questions/{STATE['q2']}/answered", json={"answered": True})
        assert r.status_code == 404

    def test_mark_and_unmark(self):
        q = STATE["q1"]
        r = STAFF.post(f"{BASE_URL}/api/admin/team-questions/{q}/answered", json={"answered": True})
        assert r.status_code == 200 and r.json() == {"answered": True}
        row = next(x for x in STAFF.get(f"{BASE_URL}/api/admin/team-questions").json() if x["id"] == q)
        assert row["answered_at"] and row["answered_by"] == "QA64 Staff"
        STAFF.post(f"{BASE_URL}/api/admin/team-questions/{q}/answered", json={"answered": False})
        row = next(x for x in STAFF.get(f"{BASE_URL}/api/admin/team-questions").json() if x["id"] == q)
        assert row["answered_at"] is None

    def test_owner_can_mark_any(self):
        r = OWNER.post(f"{BASE_URL}/api/admin/team-questions/{STATE['q2']}/answered", json={"answered": True})
        assert r.status_code == 200
        OWNER.post(f"{BASE_URL}/api/admin/team-questions/{STATE['q2']}/answered", json={"answered": False})

    def test_unknown_404(self):
        assert OWNER.post(f"{BASE_URL}/api/admin/team-questions/nope/answered", json={"answered": True}).status_code == 404

    def test_asker_followup_reopens(self):
        q = STATE["q1"]
        STAFF.post(f"{BASE_URL}/api/members/team-questions/{q}/reply", json={"text": "Use the Events tab."})
        STAFF.post(f"{BASE_URL}/api/admin/team-questions/{q}/answered", json={"answered": True})
        r = MEM.post(f"{BASE_URL}/api/members/team-questions/{q}/reply", json={"text": "Thanks, one more thing?"})
        assert r.status_code == 200
        row = next(x for x in STAFF.get(f"{BASE_URL}/api/admin/team-questions").json() if x["id"] == q)
        assert row["answered_at"] is None, "asker follow-up should re-open (clear answered_at)"


class TestFaq:
    def test_validation(self):
        assert OWNER.post(f"{BASE_URL}/api/admin/faq", json={"question": "ab", "answer": "ok"}).status_code == 400
        assert OWNER.post(f"{BASE_URL}/api/admin/faq", json={"question": "TEST_QA64 valid?", "answer": "x"}).status_code == 400

    def test_crud_and_member_view(self):
        r = STAFF.post(f"{BASE_URL}/api/admin/faq", json={"question": "TEST_QA64 Pub?", "answer": "Yes", "published": True, "source_question_id": STATE["q1"]})
        assert r.status_code == 200
        pub = r.json()
        assert pub["published"] is True and pub["source_question_id"] == STATE["q1"] and "_id" not in pub
        hid = CONTENT.post(f"{BASE_URL}/api/admin/faq", json={"question": "TEST_QA64 Hid?", "answer": "No", "published": False}).json()
        admin_ids = {x["id"] for x in OWNER.get(f"{BASE_URL}/api/admin/faq").json()}
        assert {pub["id"], hid["id"]} <= admin_ids
        mem = MEM.get(f"{BASE_URL}/api/members/faq").json()
        mids = {x["id"] for x in mem}
        assert pub["id"] in mids and hid["id"] not in mids
        assert set(mem[0].keys()) == {"id", "question", "answer"}
        u = OWNER.put(f"{BASE_URL}/api/admin/faq/{hid['id']}", json={"question": "TEST_QA64 Hid edited?", "answer": "Now yes", "published": True})
        assert u.status_code == 200
        m2 = {x["id"]: x for x in MEM.get(f"{BASE_URL}/api/members/faq").json()}
        assert m2[hid["id"]]["question"] == "TEST_QA64 Hid edited?"
        assert OWNER.put(f"{BASE_URL}/api/admin/faq/nope", json={"question": "abc", "answer": "ok"}).status_code == 404
        assert OWNER.put(f"{BASE_URL}/api/admin/faq/{hid['id']}", json={"question": "a", "answer": "ok"}).status_code == 400
        for f in (pub, hid):
            assert OWNER.delete(f"{BASE_URL}/api/admin/faq/{f['id']}").status_code == 200
        assert not {pub["id"], hid["id"]} & {x["id"] for x in OWNER.get(f"{BASE_URL}/api/admin/faq").json()}

    def test_member_faq_requires_active_member(self):
        assert PEND.get(f"{BASE_URL}/api/members/faq").status_code in (401, 403)
        assert requests.get(f"{BASE_URL}/api/members/faq").status_code == 401
        assert MEM.get(f"{BASE_URL}/api/admin/faq").status_code in (401, 403)

    def test_csrf_required(self):
        x = requests.Session()
        x.cookies.set("session_token", "qa64_owner_tok")
        assert x.post(f"{BASE_URL}/api/admin/faq", json={"question": "TEST_QA64 csrf", "answer": "no"}).status_code == 403
