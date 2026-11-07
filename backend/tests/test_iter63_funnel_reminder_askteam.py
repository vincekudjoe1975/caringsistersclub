# Iter63: join funnel, apply-reminder note, Ask the Club team (questions + replies), Team Access regression
# Setup: python3 tests/qa_session.py up && python3 tests/qa_iter63_setup.py up ; teardown with 'down'
import os
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
H = {"X-Requested-With": "XMLHttpRequest"}


def s(tok):
    x = requests.Session()
    x.headers.update(H)
    x.cookies.set("session_token", tok)
    return x


ADMIN, STAFF, NB, A, B, APPLIED = (s("qa_tok_123"), s("qa63_staff_tok"), s("qa63_nb_tok"), s("qa63_a_tok"), s("qa63_b_tok"), s("qa63_applied_tok"))


# ---- Join funnel ----
class TestFunnel:
    def test_funnel_shape(self):
        r = ADMIN.get(f"{BASE_URL}/api/admin/members/funnel")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("this_month", "last_month"):
            assert set(d[k]) >= {"label", "signed_up", "applied", "approved"}
            assert all(isinstance(d[k][f], int) for f in ("signed_up", "applied", "approved"))
        assert d["this_month"]["label"] != d["last_month"]["label"]
        print(d)

    def test_funnel_counts_match_db(self):
        d = ADMIN.get(f"{BASE_URL}/api/admin/members/funnel").json()["this_month"]
        # temp users created now (non-admin: mem_a, mem_b, applied, waiting) must be included
        assert d["signed_up"] >= 4

    def test_funnel_requires_admin(self):
        assert A.get(f"{BASE_URL}/api/admin/members/funnel").status_code in (401, 403)
        assert requests.get(f"{BASE_URL}/api/admin/members/funnel").status_code == 401


# ---- Apply reminder with note ----
class TestApplyReminder:
    def test_waiting_list_contains_temp(self):
        rows = ADMIN.get(f"{BASE_URL}/api/admin/members/waiting").json()["rows"]
        assert any(r["user_id"] == "qa63_waiting" for r in rows)

    def test_reminder_404_for_non_waiting(self):
        r = ADMIN.post(f"{BASE_URL}/api/admin/members/qa63_mem_a/apply-reminder", json={"note": "hi"})
        assert r.status_code == 404
        r = ADMIN.post(f"{BASE_URL}/api/admin/members/nope_zzz/apply-reminder", json={})
        assert r.status_code == 404

    def test_reminder_with_note_and_rate_limit(self):
        codes = []
        for _ in range(3):
            r = ADMIN.post(f"{BASE_URL}/api/admin/members/qa63_waiting/apply-reminder", json={"note": "TEST_ note from QA"})
            codes.append((r.status_code, r.json().get("detail")))
        print(codes)
        # example.com is rejected by the provider -> 400 'could not be sent'; 3rd must be 429
        assert codes[0][0] in (200, 400) and codes[1][0] in (200, 400)
        if codes[0][0] == 400:
            assert "could not be sent" in codes[0][1]
        assert codes[2][0] == 429

    def test_reminder_no_body_ok(self):
        # payload optional; rate limited for qa63_waiting already, so use 404 path via applied user to ensure no 422
        r = ADMIN.post(f"{BASE_URL}/api/admin/members/qa63_applied/apply-reminder")
        assert r.status_code == 404

    def test_reminder_requires_admin(self):
        assert A.post(f"{BASE_URL}/api/admin/members/qa63_waiting/apply-reminder", json={}).status_code == 403


# ---- Ask the Club team ----
class TestTeamQuestions:
    def test_directory_flags(self):
        rows = A.get(f"{BASE_URL}/api/members/directory").json()
        by = {r["user_id"]: r for r in rows}
        assert by["qa63_staff"]["club_team"] is True
        assert by["qa63_staff_nb"]["club_team"] is False
        assert by["qa63_mem_a"]["is_me"] is True and by["qa63_staff"]["is_me"] is False

    def test_invalid_targets(self):
        assert A.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa63_staff_nb", "text": "Hello there"}).status_code == 400
        assert A.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa63_mem_b", "text": "Hello there"}).status_code == 400
        assert STAFF.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa63_staff", "text": "Self question"}).status_code == 400
        assert A.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa63_staff", "text": "hi"}).status_code == 400

    def test_requires_member(self):
        r = APPLIED.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa63_staff", "text": "Hello there"})
        assert r.status_code == 403
        assert requests.post(f"{BASE_URL}/api/members/team-questions", headers=H, json={"to_user_id": "qa63_staff", "text": "Hello"}).status_code in (401, 403)

    def test_ask_and_reply_flow(self):
        r = A.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa63_staff", "text": "TEST_ When is the next gathering?"})
        assert r.status_code == 200, r.text
        q = r.json()
        assert q["from"]["user_id"] == "qa63_mem_a" and q["to"]["user_id"] == "qa63_staff" and q["replies"] == []
        qid = q["id"]
        assert "_id" not in q
        # persisted for both
        assert any(x["id"] == qid for x in A.get(f"{BASE_URL}/api/members/team-questions").json()["asked"])
        rec = STAFF.get(f"{BASE_URL}/api/members/team-questions").json()
        assert any(x["id"] == qid for x in rec["received"])
        # third party cannot reply / see
        assert B.post(f"{BASE_URL}/api/members/team-questions/{qid}/reply", json={"text": "intrude"}).status_code == 404
        bd = B.get(f"{BASE_URL}/api/members/team-questions").json()
        assert not any(x["id"] == qid for x in bd["asked"] + bd["received"])
        # empty reply
        assert STAFF.post(f"{BASE_URL}/api/members/team-questions/{qid}/reply", json={"text": "  "}).status_code == 400
        # staff reply, then sister follow-up
        assert STAFF.post(f"{BASE_URL}/api/members/team-questions/{qid}/reply", json={"text": "TEST_ Saturday at 10"}).status_code == 200
        assert A.post(f"{BASE_URL}/api/members/team-questions/{qid}/reply", json={"text": "TEST_ Thanks!"}).status_code == 200
        th = next(x for x in A.get(f"{BASE_URL}/api/members/team-questions").json()["asked"] if x["id"] == qid)
        assert [r["text"] for r in th["replies"]] == ["TEST_ Saturday at 10", "TEST_ Thanks!"]
        assert th["replies"][0]["by"]["user_id"] == "qa63_staff"
        th2 = next(x for x in STAFF.get(f"{BASE_URL}/api/members/team-questions").json()["received"] if x["id"] == qid)
        assert len(th2["replies"]) == 2

    def test_rate_limit_10_per_day(self):
        codes = [B.post(f"{BASE_URL}/api/members/team-questions", json={"to_user_id": "qa63_staff", "text": f"TEST_ q{i}"}).status_code for i in range(11)]
        print(codes)
        assert codes[:10] == [200] * 10 and codes[10] == 429


# ---- Regression: Team Access shows staff only ----
class TestTeamRegression:
    def test_admin_team_only_admins(self):
        d = ADMIN.get(f"{BASE_URL}/api/admin/team").json()
        assert d["users"] and all(u["role"] == "admin" for u in d["users"])
        ids = [u["user_id"] for u in d["users"]]
        assert "qa63_staff" in ids and "qa63_mem_a" not in ids
