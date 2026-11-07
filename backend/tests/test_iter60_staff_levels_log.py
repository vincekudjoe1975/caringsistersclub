"""Iteration 60: staff permission levels, staff change log, team role/level/make-member.
Requires: python3 qa_session.py up && python3 _qa60_sessions.py up (run in that order)."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
H = {"X-Requested-With": "XMLHttpRequest"}


def sess(tok):
    s = requests.Session()
    s.cookies.set("session_token", tok)
    s.headers.update(H)
    return s


FULL = sess("qa_tok_123")
CONTENT = sess("TEST_qa60_tok_content")
MEMBERS = sess("TEST_qa60_tok_members")
MONEY = sess("TEST_qa60_tok_money")


# --- /auth/me returns staff_level + is_owner
@pytest.mark.parametrize("s,lvl", [(FULL, "full"), (CONTENT, "content"), (MEMBERS, "members"), (MONEY, "money")])
def test_me_level(s, lvl):
    r = s.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    d = r.json()
    assert d["staff_level"] == lvl
    assert d["is_owner"] is False


# --- path-based enforcement
CASES = [
    (CONTENT, ["/api/admin/programs", "/api/admin/events", "/api/admin/gallery"], ["/api/admin/members/waiting", "/api/admin/donations", "/api/admin/team"]),
    (MEMBERS, ["/api/admin/members/waiting", "/api/admin/member-emails/welcome"], ["/api/admin/programs", "/api/admin/donations", "/api/admin/team"]),
    (MONEY, ["/api/admin/donations", "/api/admin/donors"], ["/api/admin/programs", "/api/admin/members/waiting", "/api/admin/team"]),
]


@pytest.mark.parametrize("s,ok,blocked", CASES)
def test_level_enforcement(s, ok, blocked):
    for p in ok:
        r = s.get(f"{BASE_URL}{p}")
        assert r.status_code == 200, f"{p} -> {r.status_code} {r.text[:120]}"
    for p in blocked:
        r = s.get(f"{BASE_URL}{p}")
        assert r.status_code == 403, f"{p} -> {r.status_code}"
        assert "staff access" in r.json()["detail"].lower()


@pytest.mark.parametrize("s", [CONTENT, MEMBERS, MONEY, FULL])
def test_shared_paths(s):
    for p in ["/api/submissions/counts", "/api/admin/security/spam", "/api/auth/staff-code/pref"]:
        r = s.get(f"{BASE_URL}{p}")
        assert r.status_code == 200, f"{p} -> {r.status_code} {r.text[:120]}"


def test_team_log_full_only():
    assert FULL.get(f"{BASE_URL}/api/admin/team/log").status_code == 200
    for s in (CONTENT, MEMBERS, MONEY):
        assert s.get(f"{BASE_URL}/api/admin/team/log").status_code == 403


def test_limited_cannot_change_own_level():
    r = CONTENT.post(f"{BASE_URL}/api/admin/team/TEST_qa60_content/level", json={"level": "full"})
    assert r.status_code == 403


def test_full_self_level_400():
    r = FULL.post(f"{BASE_URL}/api/admin/team/qa_user/level", json={"level": "content"})
    assert r.status_code == 400


def test_invalid_level_400():
    assert FULL.post(f"{BASE_URL}/api/admin/team/TEST_qa60_demote/level", json={"level": "boss"}).status_code == 400
    assert FULL.post(f"{BASE_URL}/api/admin/team/TEST_qa60_target/role", json={"role": "admin", "level": "boss"}).status_code == 400


def test_owner_level_400():
    team = FULL.get(f"{BASE_URL}/api/admin/team").json()
    owner = next(u for u in team["users"] if u["is_owner"])
    assert owner["staff_level"] == "full"
    r = FULL.post(f"{BASE_URL}/api/admin/team/{owner['user_id']}/level", json={"level": "content"})
    assert r.status_code == 400


def _log():
    return FULL.get(f"{BASE_URL}/api/admin/team/log").json()


def test_level_change_and_log():
    r = FULL.post(f"{BASE_URL}/api/admin/team/TEST_qa60_demote/level", json={"level": "money"})
    assert r.status_code == 200 and r.json()["level"] == "money"
    team = FULL.get(f"{BASE_URL}/api/admin/team").json()
    u = next(x for x in team["users"] if x["user_id"] == "TEST_qa60_demote")
    assert u["staff_level"] == "money"
    top = _log()[0]
    assert top["action"] == "level" and top["level"] == "money" and top["target"]["email"] == "test.qa60.demote@example.com"
    assert top["by"]["email"] == "qa@example.com"
    # same level -> no new log row
    n = len(_log())
    FULL.post(f"{BASE_URL}/api/admin/team/TEST_qa60_demote/level", json={"level": "money"})
    assert len(_log()) == n


def test_level_on_non_admin_404():
    r = FULL.post(f"{BASE_URL}/api/admin/team/TEST_qa60_target2/level", json={"level": "money"})
    assert r.status_code == 404


def test_grant_with_level_then_member():
    # ONE real grant (sends alert emails to owners)
    r = FULL.post(f"{BASE_URL}/api/admin/team/TEST_qa60_target/role", json={"role": "admin", "level": "members"})
    assert r.status_code == 200
    me = sess("x")  # placeholder
    team = FULL.get(f"{BASE_URL}/api/admin/team").json()
    u = next(x for x in team["users"] if x["user_id"] == "TEST_qa60_target")
    assert u["role"] == "admin" and u["staff_level"] == "members"
    top = _log()[0]
    assert top["action"] == "granted" and top["level"] == "members" and top["target"]["email"] == "test.qa60.target@example.com"
    # make-member
    r = FULL.post(f"{BASE_URL}/api/admin/team/TEST_qa60_target/make-member")
    assert r.status_code == 200 and r.json()["member_status"] == "active"
    top = _log()[0]
    assert top["action"] == "to_member" and top["target"]["email"] == "test.qa60.target@example.com"


def test_log_sorted_newest_first():
    rows = _log()
    ats = [r["at"] for r in rows]
    assert ats == sorted(ats, reverse=True)
    assert all("_id" not in r for r in rows)
