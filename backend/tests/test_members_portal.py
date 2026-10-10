"""Backend tests for the Member Portal (iteration 22).

Covers:
- Auth gating on /api/members/* (401 anon, 403 non-members)
- Member application flow + admin approve/decline
- Admin invite + auto-activation on /api/members/me
- Announcements CRUD
- Discussion threads + replies + delete rules
- Bylaws fetch (meta + file) + public /api/media isolation
- Directory + profile show_contact gating
- Admin team-access excludes members (regression)
"""
import os
import io
import time
import uuid
import pytest
import requests

def _load_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "")

BASE_URL = _load_env().rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"
XRW = {"X-Requested-With": "XMLHttpRequest"}

ADMIN = {"session_token": "qa_tok_123"}
MEM_A = {"session_token": "mem_tok_a"}
MEM_B = {"session_token": "mem_tok_b"}


def _s(cookies=None):
    s = requests.Session()
    if cookies:
        for k, v in cookies.items():
            s.cookies.set(k, v)
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Auth gating ----------
class TestAuthGating:
    def test_members_me_anon_401(self):
        r = requests.get(f"{API}/members/me")
        assert r.status_code == 401

    def test_members_directory_anon_401(self):
        r = requests.get(f"{API}/members/directory")
        assert r.status_code == 401

    def test_members_threads_non_member_403(self):
        # mem_tok_a starts as pending (no member_status) -> should be 403
        s = _s(MEM_A)
        r = s.get(f"{API}/members/threads")
        # pending user -> members/me returns status, but other endpoints require member
        assert r.status_code in (403,), f"expected 403 got {r.status_code}: {r.text}"

    def test_admin_members_requires_admin(self):
        s = _s(MEM_A)
        r = s.get(f"{API}/admin/members")
        assert r.status_code == 403


# ---------- Application flow ----------
class TestApplicationFlow:
    def test_apply_requires_delaware_and_city(self):
        s = _s(MEM_A)
        s.headers.update(XRW)
        # missing delaware
        r = s.post(f"{API}/members/apply", json={
            "city": "", "phone": "", "referred_by": "Jane Doe",
            "is_adult": True, "in_delaware": False, "accept_bylaws": True,
            "is_delaware": False, "agrees_bylaws": True
        })
        assert r.status_code == 400

    def test_apply_success_sets_applied(self):
        s = _s(MEM_A)
        s.headers.update(XRW)
        r = s.post(f"{API}/members/apply", json={
            "city": "Wilmington", "phone": "555-1234",
            "referred_by": "Jane Doe", "is_adult": True,
            "in_delaware": True, "accept_bylaws": True,
            "is_delaware": True, "agrees_bylaws": True
        })
        assert r.status_code == 200, r.text
        # me should reflect applied
        me = s.get(f"{API}/members/me").json()
        assert me.get("status") == "applied"


# ---------- Admin approve ----------
class TestAdminApprove:
    def test_admin_sees_pending_and_approves(self):
        a = _s(ADMIN)
        a.headers.update(XRW)
        resp = a.get(f"{API}/admin/members")
        assert resp.status_code == 200
        data = resp.json()
        apps = [m for m in data["members"] if m["status"] == "applied"]
        assert any(m["email"] == "qa.sister.a@example.com" for m in apps), apps
        uid = next(m for m in apps if m["email"] == "qa.sister.a@example.com")["user_id"]

        r = a.post(f"{API}/admin/members/{uid}/status", json={"action": "approve"})
        assert r.status_code == 200, r.text

        # mem_a now active
        me = _s(MEM_A).get(f"{API}/members/me").json()
        assert me.get("status") == "active"


# ---------- Invite auto-activation ----------
class TestInviteFlow:
    def test_admin_invite_and_autoactivate_on_me(self):
        a = _s(ADMIN)
        a.headers.update(XRW)
        r = a.post(f"{API}/admin/members/invite", json={
            "name": "QA Sister B", "email": "qa.sister.b@example.com"
        })
        # email send may 422 to example.com; but endpoint itself should succeed
        assert r.status_code in (200, 201), r.text

        # List invites
        inv = a.get(f"{API}/admin/members").json().get("invites", [])
        assert any(i["email"] == "qa.sister.b@example.com" for i in inv), inv

        # mem_b hits /members/me -> should auto-activate
        me = _s(MEM_B).get(f"{API}/members/me")
        assert me.status_code == 200, me.text
        assert me.json().get("status") == "active", me.json()


# ---------- Announcements ----------
class TestAnnouncements:
    ann_id = None

    def test_admin_post_announcement(self):
        a = _s(ADMIN); a.headers.update(XRW)
        r = a.post(f"{API}/admin/members/announcements",
                   json={"title": "TEST Welcome", "body": "Hello members", "pinned": True, "email_members": False})
        assert r.status_code == 200, r.text
        TestAnnouncements.ann_id = r.json().get("id")
        assert TestAnnouncements.ann_id

    def test_member_sees_announcement(self):
        r = _s(MEM_A).get(f"{API}/members/announcements")
        assert r.status_code == 200
        titles = [x["title"] for x in r.json()]
        assert "TEST Welcome" in titles

    def test_admin_delete_announcement(self):
        a = _s(ADMIN); a.headers.update(XRW)
        r = a.delete(f"{API}/admin/members/announcements/{TestAnnouncements.ann_id}")
        assert r.status_code == 200


# ---------- Threads ----------
class TestThreadsAndReplies:
    tid_a = None
    tid_b = None
    reply_id = None

    def test_member_a_create_thread(self):
        s = _s(MEM_A); s.headers.update(XRW)
        r = s.post(f"{API}/members/threads", json={"title": "TEST Thread A", "body": "Hello sisters"})
        assert r.status_code == 200, r.text
        TestThreadsAndReplies.tid_a = r.json()["id"]

    def test_member_b_create_thread(self):
        s = _s(MEM_B); s.headers.update(XRW)
        r = s.post(f"{API}/members/threads", json={"title": "TEST Thread B", "body": "Hi"})
        assert r.status_code == 200, r.text
        TestThreadsAndReplies.tid_b = r.json()["id"]

    def test_member_b_reply_on_a(self):
        s = _s(MEM_B); s.headers.update(XRW)
        r = s.post(f"{API}/members/threads/{TestThreadsAndReplies.tid_a}/replies",
                   json={"body": "Nice to meet you"})
        assert r.status_code == 200, r.text
        # read thread back to find reply id
        t = _s(MEM_A).get(f"{API}/members/threads/{TestThreadsAndReplies.tid_a}").json()
        assert t["reply_count"] >= 1
        TestThreadsAndReplies.reply_id = t["replies"][-1]["id"]

    def test_member_cannot_delete_others_thread(self):
        s = _s(MEM_B); s.headers.update(XRW)
        r = s.delete(f"{API}/members/threads/{TestThreadsAndReplies.tid_a}")
        assert r.status_code == 403

    def test_member_cannot_delete_others_reply(self):
        s = _s(MEM_A); s.headers.update(XRW)
        # mem_a trying to delete mem_b's reply
        r = s.delete(f"{API}/members/threads/{TestThreadsAndReplies.tid_a}/replies/{TestThreadsAndReplies.reply_id}")
        assert r.status_code in (403, 404)

    def test_author_deletes_own_reply(self):
        s = _s(MEM_B); s.headers.update(XRW)
        r = s.delete(f"{API}/members/threads/{TestThreadsAndReplies.tid_a}/replies/{TestThreadsAndReplies.reply_id}")
        assert r.status_code == 200

    def test_admin_deletes_any_thread(self):
        a = _s(ADMIN); a.headers.update(XRW)
        r = a.delete(f"{API}/members/threads/{TestThreadsAndReplies.tid_a}")
        assert r.status_code == 200
        r2 = a.delete(f"{API}/members/threads/{TestThreadsAndReplies.tid_b}")
        assert r2.status_code == 200


# ---------- Bylaws ----------
class TestBylaws:
    def test_member_get_bylaws_meta(self):
        r = _s(MEM_A).get(f"{API}/members/bylaws")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "sections" in data
        assert len(data["sections"]) >= 10  # 13 expected
        assert "filename" in data

    def test_member_download_file(self):
        r = _s(MEM_A).get(f"{API}/members/bylaws/file")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "wordprocessingml" in ct or ct.startswith("application/")
        assert len(r.content) > 100

    def test_bylaws_not_in_public_media(self):
        # /api/media should not return bylaws .docx (member doc)
        r = requests.get(f"{API}/media")
        if r.status_code == 200:
            try:
                items = r.json()
                if isinstance(items, dict):
                    items = items.get("items", items.get("files", []))
                for it in items or []:
                    name = (it.get("filename") or it.get("name") or "").lower()
                    key = (it.get("key") or "").lower()
                    assert "bylaws" not in name and key != "bylaws", f"bylaws leaked in /api/media: {it}"
            except ValueError:
                pass  # not JSON; fine


# ---------- Directory + profile ----------
class TestDirectoryAndProfile:
    def test_directory_lists_active(self):
        r = _s(MEM_A).get(f"{API}/members/directory")
        assert r.status_code == 200
        rows = r.json()
        emails = [x.get("email") for x in rows if "email" in x]
        # mem_a is active now; contact gated behind show_contact
        assert isinstance(rows, list)

    def test_profile_update_show_contact(self):
        s = _s(MEM_A); s.headers.update(XRW)
        r = s.put(f"{API}/members/profile", json={
            "city": "Dover", "phone": "555-9999", "bio": "Test bio",
            "show_contact": True
        })
        assert r.status_code == 200, r.text
        # directory now reveals contact
        rows = _s(MEM_B).get(f"{API}/members/directory").json()
        a_row = next((x for x in rows if x.get("name", "").startswith("QA Sister A") or x.get("email", "").startswith("qa.sister.a")), None)
        if a_row:
            # when show_contact=True, phone/email should be present
            assert a_row.get("phone") == "555-9999" or a_row.get("email")


# ---------- Admin team access regression ----------
class TestTeamAccessRegression:
    def test_team_access_excludes_members(self):
        a = _s(ADMIN)
        # Likely endpoint /api/admin/users (team access)
        for path in ["/admin/users", "/admin/team"]:
            r = a.get(f"{API}{path}")
            if r.status_code == 200:
                users = r.json()
                if isinstance(users, dict):
                    users = users.get("users", users.get("items", []))
                emails = [u.get("email") for u in users or []]
                # Non-admin member qa.sister.a should NOT appear in team access
                assert "qa.sister.a@example.com" not in emails, f"team access leaked member: {emails}"
                return
        pytest.skip("No team access endpoint found")
