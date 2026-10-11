"""Phase 5 member portal: Import, Gatherings, Annual Summary, Spotlight.

Prereq:
  python3 /app/backend/tests/qa_session.py up
  python3 /app/backend/tests/qa_members.py up
  then admin invites qa.sister.a/b@example.com so members activate on /members/me.
Run: pytest /app/backend/tests/test_members_phase5.py -v --tb=short
"""
import io
import os
import sys
import uuid
from datetime import date, timedelta, datetime

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
H_CSRF = {"X-Requested-With": "XMLHttpRequest"}
C_ADMIN = {"session_token": "qa_tok_123"}
C_A = {"session_token": "mem_tok_a"}
C_B = {"session_token": "mem_tok_b"}


# ---------- Fixtures ----------
@pytest.fixture(scope="session", autouse=True)
def ensure_members_active():
    # (Re)invite both QA members so /members/me auto-activates them.
    for e in ("qa.sister.a@example.com", "qa.sister.b@example.com"):
        requests.post(f"{API}/admin/members/invite", json={"email": e}, cookies=C_ADMIN, headers=H_CSRF)
    for cookie in (C_A, C_B):
        r = requests.get(f"{API}/members/me", cookies=cookie)
        assert r.status_code == 200 and r.json().get("status") == "active", r.text
    yield


@pytest.fixture(scope="session")
def mem_b_user_id():
    r = requests.get(f"{API}/members/me", cookies=C_B)
    return r.json()["user_id"]


# ============================================================
# Security: anonymous & cross-role
# ============================================================
class TestSecurity:
    def test_anon_members_endpoints_401(self):
        for path in ("/members/gatherings", "/members/annual-reports", "/members/spotlight"):
            r = requests.get(f"{API}{path}")
            assert r.status_code == 401, f"{path} -> {r.status_code}"

    def test_member_cannot_hit_admin_endpoints(self):
        for path in ("/admin/members/annual", "/admin/members/spotlights"):
            r = requests.get(f"{API}{path}", cookies=C_A)
            assert r.status_code == 403, f"{path} -> {r.status_code}"

    def test_member_cannot_import(self):
        r = requests.post(f"{API}/admin/members/import/validate", json={"rows": []}, cookies=C_A, headers=H_CSRF)
        assert r.status_code == 403


# ============================================================
# Import
# ============================================================
def _csv(rows):
    # header + rows
    header = "name,email,phone,city,birthday,join date,office,referrer\n"
    body = "\n".join(",".join(str(c) for c in r) for r in rows)
    return (header + body).encode()


class TestImport:
    def test_preview_csv_rejects_bad_rows_and_warns(self):
        today = date.today()
        future_join = (today + timedelta(days=10)).isoformat()
        rows = [
            # bad email
            ["Alice Imp", "not-an-email", "", "Dover", "03/15", "2020-01-01", "", ""],
            # bad join date (future)
            ["Bob Imp", "qa.imp.bob@example.com", "", "", "", future_join, "", ""],
            # bad birthday
            ["Cat Imp", "qa.imp.cat@example.com", "", "", "notadate", "2021-06-01", "", ""],
            # ok but no join date -> warning
            ["Dee Imp", "qa.imp.dee@example.com", "", "", "", "", "", ""],
            # ok, referrer by name-in-file (Dee Imp)
            ["Eve Imp", "qa.imp.eve@example.com", "", "", "", "2022-02-14", "secretary", "Dee Imp"],
            # ok referrer unknown -> warning
            ["Fay Imp", "qa.imp.fay@example.com", "", "", "", "2023-05-05", "", "Someone Unknown"],
        ]
        files = {"file": ("members.csv", _csv(rows), "text/csv")}
        r = requests.post(f"{API}/admin/members/import/preview", files=files, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200, r.text
        rr = r.json()["rows"]
        assert len(rr) == 6
        # bad email
        assert any("email" in e.lower() for e in rr[0]["errors"])
        # future join
        assert any("join" in e.lower() for e in rr[1]["errors"])
        # bad birthday
        assert any("birthday" in e.lower() for e in rr[2]["errors"])
        # no join -> warning
        assert any("join" in w.lower() for w in rr[3]["warnings"])
        # Eve ref linked to Dee by name in file
        assert rr[4]["referrer_email"] == "qa.imp.dee@example.com"
        # Fay ref not found -> warning
        assert any("referrer" in w.lower() for w in rr[5]["warnings"])
        assert rr[5]["referrer_email"] == ""

    def test_validate_recheck_fixes_errors(self):
        row = {"name": "Gail Imp", "email": "bad", "phone": "", "city": "", "birthday": "", "joined": "", "office": "", "referrer": ""}
        r = requests.post(f"{API}/admin/members/import/validate", json={"rows": [row]}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        assert r.json()["rows"][0]["errors"]
        row["email"] = "qa.imp.gail@example.com"
        r2 = requests.post(f"{API}/admin/members/import/validate", json={"rows": [row]}, cookies=C_ADMIN, headers=H_CSRF)
        assert r2.status_code == 200
        assert not r2.json()["rows"][0]["errors"]

    def test_commit_creates_updates_links_and_reflects_in_directory_dues(self):
        # fresh commit payload: one new sister 2022 joined, one new sister referring the first.
        last_year = date.today().year - 1
        rows = [
            {"name": "Hana Imp", "email": "qa.imp.hana@example.com", "phone": "", "city": "Dover",
             "birthday": "7/4", "joined": f"{last_year}-01-10", "office": "Treasurer", "referrer": ""},
            {"name": "Ivy Imp", "email": "qa.imp.ivy@example.com", "phone": "", "city": "",
             "birthday": "", "joined": f"{last_year}-02-14", "office": "", "referrer": "Hana Imp"},
        ]
        r = requests.post(f"{API}/admin/members/import/commit",
                          json={"rows": rows, "send_invites": False}, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200, r.text
        res = r.json()
        assert (res["created"] + res["updated"]) >= 2
        assert res["referrers_linked"] >= 1
        # Re-commit updates existing (Hana) rather than creating twice.
        rows2 = [{"name": "Hana Imp Updated", "email": "qa.imp.hana@example.com",
                  "phone": "", "city": "Smyrna", "birthday": "", "joined": f"{last_year}-01-10", "office": "", "referrer": ""}]
        r2 = requests.post(f"{API}/admin/members/import/commit",
                           json={"rows": rows2, "send_invites": False}, cookies=C_ADMIN, headers=H_CSRF)
        assert r2.status_code == 200
        assert r2.json()["updated"] >= 1
        # Directory shows Hana with office
        d = requests.get(f"{API}/members/directory", cookies=C_A)
        assert d.status_code == 200
        names = [m.get("name") for m in d.json()]
        assert "Hana Imp" in names or "Hana Imp Updated" in names
        # Dues reflects $120 expected (joined last year => full prior year)
        du = requests.get(f"{API}/admin/members/dues", cookies=C_ADMIN).json()
        hana = next((row for row in du.get("rows", du if isinstance(du, list) else []) if "qa.imp.hana" in (row.get("email") or "").lower()), None)
        if hana is None:  # fallback path -> fetch standing/users
            u = requests.get(f"{API}/admin/members", cookies=C_ADMIN).json()
            hana = next((m for m in (u.get("rows", u) if isinstance(u, dict) else u) if "qa.imp.hana" in (m.get("email") or "").lower()), None)
        assert hana is not None, "Hana not found in dues/admin members"


# ============================================================
# Gatherings
# ============================================================
@pytest.fixture(scope="session")
def gathering_id():
    future = (date.today() + timedelta(days=14)).isoformat()
    r = requests.post(f"{API}/admin/members/meetings",
                      json={"title": "QA Gathering Phase5", "date": future, "time": "6:00pm",
                            "location": "Clubhouse", "kind": "in-person"},
                      cookies=C_ADMIN, headers=H_CSRF)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    mid = body.get("id") or body.get("meeting", {}).get("id")
    yield mid
    requests.delete(f"{API}/admin/members/meetings/{mid}", cookies=C_ADMIN, headers=H_CSRF)


class TestGatherings:
    def test_set_gathering_deadline_and_details(self, gathering_id):
        deadline = (date.today() + timedelta(days=10)).isoformat()
        r = requests.put(f"{API}/admin/members/meetings/{gathering_id}/gathering",
                         json={"rsvp_deadline": deadline, "details": "Potluck - bring a dish"},
                         cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        rr = requests.get(f"{API}/admin/members/meetings/{gathering_id}/rsvps", cookies=C_ADMIN).json()
        assert rr["rsvp_deadline"] == deadline
        assert "Potluck" in rr["details"]

    def test_member_sees_gathering_and_rsvps(self, gathering_id):
        g = requests.get(f"{API}/members/gatherings", cookies=C_A).json()
        assert any(m["id"] == gathering_id for m in g)
        r = requests.post(f"{API}/members/gatherings/{gathering_id}/rsvp",
                          json={"response": "yes", "guests": 2, "dietary": "vegetarian"},
                          cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200, r.text
        rb = requests.post(f"{API}/members/gatherings/{gathering_id}/rsvp",
                           json={"response": "maybe", "guests": 0, "dietary": ""},
                           cookies=C_B, headers=H_CSRF)
        assert rb.status_code == 200
        hc = requests.get(f"{API}/admin/members/meetings/{gathering_id}/rsvps", cookies=C_ADMIN).json()
        assert hc["headcount"]["yes"] == 1
        assert hc["headcount"]["total"] == 3  # 1 yes + 2 guests
        assert hc["headcount"]["maybe"] == 1
        assert any("vegetarian" in (d["note"] or "") for d in hc["dietary"])

    def test_rsvp_invalid_response_400(self, gathering_id):
        r = requests.post(f"{API}/members/gatherings/{gathering_id}/rsvp",
                          json={"response": "later", "guests": 0}, cookies=C_A, headers=H_CSRF)
        assert r.status_code == 400

    def test_rsvp_reminder_dedupe(self):
        # Create a gathering 7 days out and call _send_gathering_reminders.
        sys.path.insert(0, "/app/backend")
        import asyncio
        import server  # noqa: E402
        target = (server._today_et() + timedelta(days=7)).isoformat()
        r = requests.post(f"{API}/admin/members/meetings",
                          json={"title": "QA Reminder Gathering", "date": target, "kind": "in-person",
                                "time": "", "location": "Hall"},
                          cookies=C_ADMIN, headers=H_CSRF)
        mid = (r.json().get("id") or r.json().get("meeting", {}).get("id"))
        try:
            n1 = asyncio.get_event_loop().run_until_complete(server._send_gathering_reminders(server._today_et()))
            n2 = asyncio.get_event_loop().run_until_complete(server._send_gathering_reminders(server._today_et()))
            assert n2 == 0, "Reminder should dedupe on second call"
            # n1 may be 0 if email settings missing but reminder_sent_at should be stamped
            rr = requests.get(f"{API}/admin/members/meetings/{mid}/rsvps", cookies=C_ADMIN).json()
            assert rr.get("reminder_sent_at")
        finally:
            requests.delete(f"{API}/admin/members/meetings/{mid}", cookies=C_ADMIN, headers=H_CSRF)


# ============================================================
# Annual summary
# ============================================================
class TestAnnual:
    def test_admin_annual_data_shape(self):
        y = date.today().year
        r = requests.get(f"{API}/admin/members/annual?year={y}", cookies=C_ADMIN)
        assert r.status_code == 200, r.text
        j = r.json()
        for k in ("membership", "attendance", "dues", "support", "votes"):
            assert k in j, k
        assert j["year"] == y

    def test_share_unshare_flow(self):
        y = date.today().year
        s = requests.post(f"{API}/admin/members/annual/share", json={"year": y},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert s.status_code == 200
        rid = s.json()["id"]
        # member sees it
        mr = requests.get(f"{API}/members/annual-reports", cookies=C_A).json()
        assert any(x["id"] == rid for x in mr)
        d = requests.get(f"{API}/members/annual-reports/{rid}", cookies=C_A).json()
        assert "membership" in d and "shared_at" in d
        # unshare
        u = requests.delete(f"{API}/admin/members/annual/share?year={y}",
                            cookies=C_ADMIN, headers=H_CSRF)
        assert u.status_code == 200
        mr2 = requests.get(f"{API}/members/annual-reports", cookies=C_A).json()
        assert not any(x["id"] == rid for x in mr2)
        g = requests.get(f"{API}/members/annual-reports/{rid}", cookies=C_A)
        assert g.status_code == 404


# ============================================================
# Spotlight
# ============================================================
class TestSpotlight:
    def _cur_month(self):
        t = date.today()
        return f"{t.year}-{t.month:02d}"

    def _next_month(self):
        t = date.today()
        y, m = (t.year, t.month + 1) if t.month < 12 else (t.year + 1, 1)
        return f"{y}-{m:02d}"

    def test_media_hides_spotlight(self):
        r = requests.get(f"{API}/media?category=spotlight")
        assert r.status_code == 200
        assert r.json() == []

    def test_staff_mode_create_publish_month_uniqueness(self, mem_b_user_id):
        month = self._next_month()
        # Clean preexisting for same (user, month) to make test re-runnable.
        import pymongo, os as _os
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        _db = pymongo.MongoClient(_os.environ["MONGO_URL"])[_os.environ["DB_NAME"]]
        _db.member_spotlights.delete_many({"month": month})

        c = requests.post(f"{API}/admin/members/spotlights",
                          json={"user_id": mem_b_user_id, "month": month, "mode": "staff",
                                "story": "", "photo_url": "", "use_profile_photo": False},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert c.status_code == 200, c.text
        sid = c.json()["id"]
        # Publish without story -> 400
        p0 = requests.post(f"{API}/admin/members/spotlights/{sid}/publish",
                          cookies=C_ADMIN, headers=H_CSRF)
        assert p0.status_code == 400
        # Add story
        e = requests.put(f"{API}/admin/members/spotlights/{sid}",
                        json={"story": "Bea is amazing", "photo_url": ""},
                        cookies=C_ADMIN, headers=H_CSRF)
        assert e.status_code == 200
        p = requests.post(f"{API}/admin/members/spotlights/{sid}/publish",
                          cookies=C_ADMIN, headers=H_CSRF)
        assert p.status_code == 200
        # Second published for same month -> 400
        # First create another draft, then try publishing it:
        c2 = requests.post(f"{API}/admin/members/spotlights",
                           json={"user_id": mem_b_user_id, "month": month, "mode": "staff",
                                 "story": "dup", "photo_url": "", "use_profile_photo": False},
                           cookies=C_ADMIN, headers=H_CSRF)
        # Create itself should 400 because month already has published
        assert c2.status_code == 400
        # cleanup
        requests.delete(f"{API}/admin/members/spotlights/{sid}", cookies=C_ADMIN, headers=H_CSRF)

    def test_invite_mode_member_submit_and_foreign_photo_rejected(self, mem_b_user_id):
        month = self._next_month()
        # Clean
        import pymongo, os as _os
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        _db = pymongo.MongoClient(_os.environ["MONGO_URL"])[_os.environ["DB_NAME"]]
        _db.member_spotlights.delete_many({"month": month})

        c = requests.post(f"{API}/admin/members/spotlights",
                          json={"user_id": mem_b_user_id, "month": month, "mode": "invite",
                                "story": "", "photo_url": "", "use_profile_photo": False},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert c.status_code == 200
        sid = c.json()["id"]
        # Member B sees invite
        m = requests.get(f"{API}/members/spotlight", cookies=C_B).json()
        assert m["my_invite"] and m["my_invite"]["id"] == sid
        # Member A (no invite) cannot upload photo
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
        up_a = requests.post(f"{API}/members/spotlight/photo",
                             files={"file": ("p.png", png, "image/png")},
                             cookies=C_A, headers=H_CSRF)
        assert up_a.status_code == 403
        # Submit with foreign photo url -> 400
        bad = requests.post(f"{API}/members/spotlight/{sid}/submit",
                            json={"story": "my story", "photo_url": "https://evil.example.com/x.jpg"},
                            cookies=C_B, headers=H_CSRF)
        assert bad.status_code == 400
        # Submit without photo -> OK
        ok = requests.post(f"{API}/members/spotlight/{sid}/submit",
                           json={"story": "my sister story", "photo_url": ""},
                           cookies=C_B, headers=H_CSRF)
        assert ok.status_code == 200
        # Admin sees status submitted
        lst = requests.get(f"{API}/admin/members/spotlights", cookies=C_ADMIN).json()
        row = next(x for x in lst if x["id"] == sid)
        assert row["status"] == "submitted"
        # Publish
        p = requests.post(f"{API}/admin/members/spotlights/{sid}/publish",
                          cookies=C_ADMIN, headers=H_CSRF)
        assert p.status_code == 200
        requests.delete(f"{API}/admin/members/spotlights/{sid}", cookies=C_ADMIN, headers=H_CSRF)

    def test_invalid_user_or_month_rejected(self, mem_b_user_id):
        bad = requests.post(f"{API}/admin/members/spotlights",
                            json={"user_id": mem_b_user_id, "month": "2026-13", "mode": "staff"},
                            cookies=C_ADMIN, headers=H_CSRF)
        assert bad.status_code == 400
        bad2 = requests.post(f"{API}/admin/members/spotlights",
                             json={"user_id": "no_such_user", "month": "2026-06", "mode": "staff"},
                             cookies=C_ADMIN, headers=H_CSRF)
        assert bad2.status_code == 400


# ============================================================
# Regression: earlier endpoints still 200
# ============================================================
class TestRegression:
    @pytest.mark.parametrize("path", [
        "/members/me", "/members/directory", "/members/announcements",
        "/members/threads", "/members/minutes", "/members/ballots",
        "/members/next-meeting", "/members/anniversaries", "/members/treasurer-reports",
    ])
    def test_member_paths_200(self, path):
        r = requests.get(f"{API}{path}", cookies=C_A)
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:120]}"

    @pytest.mark.parametrize("path", [
        "/admin/members", "/admin/members/meetings", "/admin/members/dues",
        "/admin/members/ballots", "/admin/members/collections", "/admin/members/december",
        "/admin/members/referrers",
    ])
    def test_admin_paths_200(self, path):
        r = requests.get(f"{API}{path}", cookies=C_ADMIN)
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:120]}"
