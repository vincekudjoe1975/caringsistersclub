"""Phase 7 member portal: Avatars, Gathering albums, Self check-in, Prayer digests, Birthdays.

Prereq:
  python3 /app/backend/tests/qa_session.py up
  python3 /app/backend/tests/qa_members.py up
  (and set users.member_status='active', member_since for qa_mem_a/b)
Run: pytest /app/backend/tests/test_members_phase7.py -v --tb=short
"""
import io
import os
import sys
import struct
import zlib
import asyncio
import pytest
import requests
from datetime import date as _pydate, timedelta, datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
_MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

sys.path.insert(0, "/app/backend")
from server import _today_et  # noqa

class _DateProxy:
    @staticmethod
    def today():
        return _today_et()
date = _DateProxy()

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
H_CSRF = {"X-Requested-With": "XMLHttpRequest"}
C_ADMIN = {"session_token": "qa_tok_123"}
C_A = {"session_token": "mem_tok_a"}
C_B = {"session_token": "mem_tok_b"}

sys.path.insert(0, "/app/backend")


def _tiny_png() -> bytes:
    # 1x1 transparent PNG
    sig = b"\x89PNG\r\n\x1a\n"
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00"))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


PNG = _tiny_png()


@pytest.fixture(scope="session", autouse=True)
def ensure_members_active():
    # re-invite + activate
    for e in ("qa.sister.a@example.com", "qa.sister.b@example.com"):
        requests.post(f"{API}/admin/members/invite", json={"email": e}, cookies=C_ADMIN, headers=H_CSRF)
    _MONGO.users.update_many(
        {"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}},
        {"$set": {"member_status": "active", "member_since": "2026-01-01"}},
    )
    for cookie in (C_A, C_B):
        r = requests.get(f"{API}/members/me", cookies=cookie)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "active"
    yield
    # cleanup gathering photos uploaded by test users
    _MONGO.member_gathering_photos.delete_many({"uploader_id": {"$in": ["qa_mem_a", "qa_mem_b", "qa_user"]}})
    _MONGO.users.update_many(
        {"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}},
        {"$unset": {"picture": "", "picture_custom": "", "member_bday_sent_year": "", "member_profile": ""}},
    )


@pytest.fixture(scope="session")
def uid_a():
    return requests.get(f"{API}/members/me", cookies=C_A).json()["user_id"]


@pytest.fixture(scope="session")
def uid_b():
    return requests.get(f"{API}/members/me", cookies=C_B).json()["user_id"]


# ============================================================
# AVATAR
# ============================================================
class TestAvatar:
    def test_upload_sets_picture(self, uid_a):
        files = {"file": ("av.png", PNG, "image/png")}
        r = requests.post(f"{API}/members/photo", files=files, cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200, r.text
        pic = r.json()["picture"]
        assert pic.startswith("/api/media/file/")
        # verify DB
        u = _MONGO.users.find_one({"user_id": uid_a}, {"picture": 1, "picture_custom": 1})
        assert u["picture"] == pic and u["picture_custom"] is True

    def test_upload_rejects_non_image(self):
        files = {"file": ("x.txt", b"hello", "text/plain")}
        r = requests.post(f"{API}/members/photo", files=files, cookies=C_A, headers=H_CSRF)
        assert r.status_code in (400, 415), r.text

    def test_avatar_propagates_to_prayer_author(self, uid_a):
        pic = _MONGO.users.find_one({"user_id": uid_a}, {"picture": 1})["picture"]
        pr = requests.post(f"{API}/members/prayers", json={"kind": "request", "body": "QA phase7 prayer", "anonymous": False},
                          cookies=C_A, headers=H_CSRF)
        assert pr.status_code == 200, pr.text
        pid = pr.json()["id"]
        rows = requests.get(f"{API}/members/prayers", cookies=C_B).json()
        mine = next((p for p in rows if p["id"] == pid), None)
        assert mine and mine["author_picture"] == pic
        requests.delete(f"{API}/members/prayers/{pid}", cookies=C_A, headers=H_CSRF)

    def test_delete_clears_picture(self, uid_a):
        r = requests.delete(f"{API}/members/photo", cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200
        assert r.json()["picture"] == ""
        u = _MONGO.users.find_one({"user_id": uid_a}, {"picture": 1, "picture_custom": 1})
        assert u.get("picture", "") == "" and u.get("picture_custom") is False

    def test_admin_set_and_remove(self, uid_b):
        files = {"file": ("av.png", PNG, "image/png")}
        r = requests.post(f"{API}/admin/members/{uid_b}/photo", files=files, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200, r.text
        assert r.json()["picture"].startswith("/api/media/file/")
        r = requests.delete(f"{API}/admin/members/{uid_b}/photo", cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200

    def test_admin_photo_requires_admin(self, uid_a):
        files = {"file": ("av.png", PNG, "image/png")}
        r = requests.post(f"{API}/admin/members/{uid_a}/photo", files=files, cookies=C_B, headers=H_CSRF)
        assert r.status_code in (401, 403)

    def test_admin_photo_404_missing_user(self):
        files = {"file": ("av.png", PNG, "image/png")}
        r = requests.post(f"{API}/admin/members/does-not-exist-uid/photo", files=files, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 404

    def test_avatar_not_in_public_media_list(self, uid_a):
        files = {"file": ("av.png", PNG, "image/png")}
        up = requests.post(f"{API}/members/photo", files=files, cookies=C_A, headers=H_CSRF)
        pic_id = up.json()["picture"].rsplit("/", 1)[-1]
        all_media = requests.get(f"{API}/media").json()
        assert not any(m.get("id") == pic_id for m in all_media), "avatar leaked into public media"
        # cleanup
        requests.delete(f"{API}/members/photo", cookies=C_A, headers=H_CSRF)


# ============================================================
# GATHERING ALBUMS
# ============================================================
@pytest.fixture(scope="class")
def meeting_today():
    today = date.today().isoformat()
    mid = f"qa-ph7-meet-{today}"
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_meetings.insert_one({"id": mid, "title": "QA Phase7 Gathering", "kind": "in-person", "date": today, "location": "QA Hall"})
    yield mid
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_gathering_photos.delete_many({"meeting_id": mid})


@pytest.fixture(scope="class")
def meeting_future():
    future = (date.today() + timedelta(days=14)).isoformat()
    mid = "qa-ph7-meet-future"
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_meetings.insert_one({"id": mid, "title": "QA Phase7 Future", "kind": "in-person", "date": future, "location": "QA Hall"})
    yield mid
    _MONGO.member_meetings.delete_one({"id": mid})


class TestAlbums:
    def test_albums_list_only_past(self, meeting_today, meeting_future):
        rows = requests.get(f"{API}/members/albums", cookies=C_A).json()
        ids = {m["id"] for m in rows}
        assert meeting_today in ids
        assert meeting_future not in ids

    def test_future_upload_rejected(self, meeting_future):
        files = {"file": ("p.png", PNG, "image/png")}
        r = requests.post(f"{API}/members/albums/{meeting_future}/photos", files=files, cookies=C_A, headers=H_CSRF)
        assert r.status_code == 400

    def test_member_upload_is_pending(self, meeting_today):
        files = {"file": ("p.png", PNG, "image/png")}
        r = requests.post(f"{API}/members/albums/{meeting_today}/photos", files=files, data={"caption": "QA"}, cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "pending"
        pytest.pending_pid = d["id"]

    def test_admin_upload_auto_approved(self, meeting_today):
        files = {"file": ("p.png", PNG, "image/png")}
        r = requests.post(f"{API}/members/albums/{meeting_today}/photos", files=files, cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "approved"
        pytest.approved_pid = d["id"]

    def test_album_detail_visibility(self, meeting_today):
        # A sees own pending + approved
        rows_a = requests.get(f"{API}/members/albums/{meeting_today}", cookies=C_A).json()["photos"]
        ids_a = {p["id"] for p in rows_a}
        assert pytest.pending_pid in ids_a and pytest.approved_pid in ids_a
        # B does NOT see A's pending
        rows_b = requests.get(f"{API}/members/albums/{meeting_today}", cookies=C_B).json()["photos"]
        ids_b = {p["id"] for p in rows_b}
        assert pytest.pending_pid not in ids_b
        assert pytest.approved_pid in ids_b
        # admin sees both
        rows_x = requests.get(f"{API}/members/albums/{meeting_today}", cookies=C_ADMIN).json()["photos"]
        ids_x = {p["id"] for p in rows_x}
        assert pytest.pending_pid in ids_x and pytest.approved_pid in ids_x

    def test_pending_file_404_to_other_member(self):
        r = requests.get(f"{API}/members/gathering-photos/{pytest.pending_pid}/file", cookies=C_B)
        assert r.status_code == 404
        # owner can access
        r2 = requests.get(f"{API}/members/gathering-photos/{pytest.pending_pid}/file", cookies=C_A)
        assert r2.status_code == 200

    def test_media_file_private_for_gathering(self):
        p = _MONGO.member_gathering_photos.find_one({"id": pytest.approved_pid}, {"media_id": 1})
        mid = p["media_id"]
        r = requests.get(f"{API}/media/file/{mid}")
        assert r.status_code == 404  # private category

    def test_media_list_hides_gathering(self):
        all_media = requests.get(f"{API}/media").json()
        p = _MONGO.member_gathering_photos.find_one({"id": pytest.approved_pid}, {"media_id": 1})
        assert not any(m.get("id") == p["media_id"] for m in all_media)

    def test_admin_queue_and_approve(self, meeting_today):
        q = requests.get(f"{API}/admin/members/gathering-photos", cookies=C_ADMIN).json()
        assert any(p["id"] == pytest.pending_pid for p in q)
        r = requests.post(f"{API}/admin/members/gathering-photos/{pytest.pending_pid}/approve", cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        # B now sees it
        rows_b = requests.get(f"{API}/members/albums/{meeting_today}", cookies=C_B).json()["photos"]
        assert any(p["id"] == pytest.pending_pid for p in rows_b)

    def test_member_withdraw_only_own_pending(self, meeting_today):
        # upload a fresh pending by A
        files = {"file": ("p.png", PNG, "image/png")}
        pid = requests.post(f"{API}/members/albums/{meeting_today}/photos", files=files, cookies=C_A, headers=H_CSRF).json()["id"]
        # B cannot delete
        r = requests.delete(f"{API}/members/gathering-photos/{pid}", cookies=C_B, headers=H_CSRF)
        assert r.status_code == 403
        # A can withdraw own pending
        r2 = requests.delete(f"{API}/members/gathering-photos/{pid}", cookies=C_A, headers=H_CSRF)
        assert r2.status_code == 200
        # cannot withdraw own approved via member
        r3 = requests.delete(f"{API}/members/gathering-photos/{pytest.pending_pid}", cookies=C_A, headers=H_CSRF)
        assert r3.status_code == 403

    def test_admin_can_delete_any(self):
        r = requests.delete(f"{API}/members/gathering-photos/{pytest.approved_pid}", cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        r2 = requests.delete(f"{API}/members/gathering-photos/{pytest.pending_pid}", cookies=C_ADMIN, headers=H_CSRF)
        assert r2.status_code == 200


# ============================================================
# SELF CHECK-IN
# ============================================================
@pytest.fixture(scope="class")
def meeting_self_today():
    today = date.today().isoformat()
    mid = "qa-ph7-self-today"
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_meetings.insert_one({"id": mid, "title": "QA Self Checkin", "kind": "in-person", "date": today, "location": "QA Hall"})
    yield mid
    _MONGO.member_meetings.delete_one({"id": mid})


@pytest.fixture(scope="class")
def meeting_self_tomorrow():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    mid = "qa-ph7-self-tomorrow"
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_meetings.insert_one({"id": mid, "title": "QA Self Future", "kind": "in-person", "date": tomorrow, "location": "QA Hall"})
    yield mid
    _MONGO.member_meetings.delete_one({"id": mid})


class TestSelfCheckin:
    def test_door_token_stable(self, meeting_self_today):
        r1 = requests.get(f"{API}/admin/members/checkin/{meeting_self_today}/door", cookies=C_ADMIN).json()["token"]
        r2 = requests.get(f"{API}/admin/members/checkin/{meeting_self_today}/door", cookies=C_ADMIN).json()["token"]
        assert r1 and r1 == r2

    def test_door_reset_returns_new(self, meeting_self_today):
        old = requests.get(f"{API}/admin/members/checkin/{meeting_self_today}/door", cookies=C_ADMIN).json()["token"]
        new = requests.post(f"{API}/admin/members/checkin/{meeting_self_today}/door/reset", cookies=C_ADMIN, headers=H_CSRF).json()["token"]
        assert new and new != old

    def test_bad_token_404(self, meeting_self_today):
        r = requests.get(f"{API}/members/self-checkin/{meeting_self_today}?t=garbage-token", cookies=C_A)
        assert r.status_code == 404

    def test_info_open_today(self, meeting_self_today):
        tok = requests.get(f"{API}/admin/members/checkin/{meeting_self_today}/door", cookies=C_ADMIN).json()["token"]
        r = requests.get(f"{API}/members/self-checkin/{meeting_self_today}?t={tok}", cookies=C_A)
        assert r.status_code == 200
        d = r.json()
        assert d["open"] is True and d["checked_in"] is False

    def test_info_closed_future_date(self, meeting_self_tomorrow):
        tok = requests.get(f"{API}/admin/members/checkin/{meeting_self_tomorrow}/door", cookies=C_ADMIN).json()["token"]
        r = requests.get(f"{API}/members/self-checkin/{meeting_self_tomorrow}?t={tok}", cookies=C_A)
        assert r.status_code == 200
        assert r.json()["open"] is False

    def test_self_checkin_marks_present(self, meeting_self_today, uid_a):
        tok = requests.get(f"{API}/admin/members/checkin/{meeting_self_today}/door", cookies=C_ADMIN).json()["token"]
        r = requests.post(f"{API}/members/self-checkin/{meeting_self_today}", json={"t": tok, "guests": 3},
                          cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True, "guests": 3}
        m = _MONGO.member_meetings.find_one({"id": meeting_self_today})
        assert (m.get("attendance") or {}).get(uid_a) == "present"
        ci = (m.get("checkins") or {}).get(uid_a)
        assert ci and ci["by"] == "self" and ci["guests"] == 3

    def test_bad_guests_400(self, meeting_self_today):
        tok = requests.get(f"{API}/admin/members/checkin/{meeting_self_today}/door", cookies=C_ADMIN).json()["token"]
        r = requests.post(f"{API}/members/self-checkin/{meeting_self_today}", json={"t": tok, "guests": 99},
                          cookies=C_B, headers=H_CSRF)
        assert r.status_code == 400

    def test_future_date_checkin_rejected(self, meeting_self_tomorrow):
        tok = requests.get(f"{API}/admin/members/checkin/{meeting_self_tomorrow}/door", cookies=C_ADMIN).json()["token"]
        r = requests.post(f"{API}/members/self-checkin/{meeting_self_tomorrow}", json={"t": tok, "guests": 0},
                          cookies=C_B, headers=H_CSRF)
        assert r.status_code == 400

    def test_sheet_shows_self_count(self, meeting_self_today):
        r = requests.get(f"{API}/admin/members/checkin/{meeting_self_today}", cookies=C_ADMIN)
        assert r.status_code == 200
        d = r.json()
        assert d["counts"]["guests"] >= 3, f"expected guests >= 3, got {d['counts']}"
        assert d["counts"]["present"] >= 1


# ============================================================
# PRAYER DIGESTS + BIRTHDAYS (via direct function calls, monkeypatched)
# ============================================================
@pytest.fixture(scope="module")
def server_module():
    sys.path.insert(0, "/app/backend")
    import server  # noqa
    # ensure motor is bound to the loop we'll use via _run
    return server


# Shared event loop so motor stays attached to one loop across all _run() calls
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


def _run(coro):
    return _LOOP.run_until_complete(coro)


def _rebind_motor(srv):
    from motor.motor_asyncio import AsyncIOMotorClient
    if getattr(srv, "_rebound_test_loop", None) is not _LOOP:
        srv.client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        srv.db = srv.client[os.environ["DB_NAME"]]
        srv._rebound_test_loop = _LOOP


class TestPrayerDigests:
    def test_author_digest_counts_once(self, server_module, uid_a, uid_b, monkeypatch):
        srv = server_module
        _rebind_motor(srv)
        # cleanup markers
        _MONGO.scheduled_runs.delete_many({"_id": {"$regex": "^prayer-"}})
        # create a prayer by A
        r = requests.post(f"{API}/members/prayers", json={"kind": "request", "body": "QA ph7 digest body", "anonymous": False},
                          cookies=C_A, headers=H_CSRF)
        pid = r.json()["id"]
        # B prays and encourages
        requests.post(f"{API}/members/prayers/{pid}/pray", cookies=C_B, headers=H_CSRF)
        requests.post(f"{API}/members/prayers/{pid}/encourage", json={"body": "QA praying with you"}, cookies=C_B, headers=H_CSRF)
        # A self-prays (should not count)
        requests.post(f"{API}/members/prayers/{pid}/pray", cookies=C_A, headers=H_CSRF)

        sent_log = []
        async def fake_send(to, subject, html, **kw):
            sent_log.append((to, subject))
            return True
        monkeypatch.setattr(srv, "send_email", fake_send)

        n = _run(srv._send_prayer_author_digests())
        assert n == 1, f"expected 1 email, got {n}, sent={sent_log}"
        assert any("qa.sister.a" in to for to, _ in sent_log)
        # second call => no new activity => 0 emails
        sent_log.clear()
        n2 = _run(srv._send_prayer_author_digests())
        assert n2 == 0
        # cleanup
        requests.delete(f"{API}/members/prayers/{pid}", cookies=C_A, headers=H_CSRF)

    def test_weekly_digest_anonymous_masked(self, server_module, monkeypatch):
        srv = server_module
        _rebind_motor(srv)
        # Isolate: remove any pre-existing prayers so only the single anon post below is in the window
        _MONGO.member_prayers.delete_many({"author_id": {"$in": ["qa_mem_a", "qa_mem_b"]}})
        # anon prayer by A
        r = requests.post(f"{API}/members/prayers", json={"kind": "request", "body": "QA weekly anon", "anonymous": True},
                          cookies=C_A, headers=H_CSRF)
        pid = r.json()["id"]

        # B opts out of weekly
        requests.put(f"{API}/members/profile", json={"prayer_weekly": False}, cookies=C_B, headers=H_CSRF)

        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject, html))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        from datetime import date as _d
        n = _run(srv._send_prayer_weekly(_d.today()))
        assert n >= 1
        tos = [to for to, _, _ in sent]
        assert "qa.sister.b@example.com" not in tos, "B opted out but still received weekly digest"
        # anonymous masking: body shows 'a sister', never A's name
        joined = "\n".join(h for _, _, h in sent)
        assert "a sister" in joined
        # A's real name should not appear in anon line (she's qa.sister.a, name 'Ama QA Sister')
        # NOTE: she could still appear if she authored a non-anon post; our single post is anon
        assert "Ama QA Sister" not in joined
        # restore B opt-in
        requests.put(f"{API}/members/profile", json={"prayer_weekly": True}, cookies=C_B, headers=H_CSRF)
        requests.delete(f"{API}/members/prayers/{pid}", cookies=C_A, headers=H_CSRF)

    def test_profile_persists_prayer_weekly(self, uid_a):
        requests.put(f"{API}/members/profile", json={"prayer_weekly": False}, cookies=C_A, headers=H_CSRF)
        u = _MONGO.users.find_one({"user_id": uid_a}, {"member_profile": 1})
        assert u["member_profile"].get("prayer_weekly") is False
        requests.put(f"{API}/members/profile", json={"prayer_weekly": True}, cookies=C_A, headers=H_CSRF)
        u2 = _MONGO.users.find_one({"user_id": uid_a}, {"member_profile": 1})
        assert u2["member_profile"].get("prayer_weekly") is True


class TestBirthdays:
    def test_birthdays_today_endpoint(self, uid_a, uid_b):
        today = date.today()
        _MONGO.users.update_one({"user_id": uid_a}, {"$set": {"member_profile.birthday_month": today.month, "member_profile.birthday_day": today.day},
                                                    "$unset": {"member_bday_sent_year": ""}})
        _MONGO.users.update_one({"user_id": uid_b}, {"$unset": {"member_profile.birthday_month": "", "member_profile.birthday_day": "", "member_bday_sent_year": ""}})
        r = requests.get(f"{API}/members/birthdays/today", cookies=C_B)
        assert r.status_code == 200
        ids = {x["user_id"] for x in r.json()}
        assert uid_a in ids

    def test_portal_birthday_banner_data(self, uid_a):
        r = requests.get(f"{API}/members/birthdays/today", cookies=C_A).json()
        assert any(x["user_id"] == uid_a for x in r)

    def test_send_birthday_emails_idempotent(self, server_module, monkeypatch, uid_a):
        srv = server_module
        _rebind_motor(srv)
        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        today = date.today()
        _MONGO.users.update_one({"user_id": uid_a}, {"$unset": {"member_bday_sent_year": ""}})
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{today.year}"})
        n1 = _run(srv._send_birthday_emails(today))
        assert n1 >= 1
        # thread created
        th = _MONGO.member_threads.find_one({"key": f"birthday:{uid_a}:{today.year}"})
        assert th and "Birthday" in th["title"]
        # idempotent
        sent.clear()
        n2 = _run(srv._send_birthday_emails(today))
        assert n2 == 0
        # cleanup
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{today.year}"})

    def test_staff_birthday_list_without_email(self, server_module, monkeypatch):
        srv = server_module
        _rebind_motor(srv)
        # qa_session.up sets staff_notify_email to "" -> should return False
        _MONGO.settings.update_one({"key": "site"}, {"$set": {"staff_notify_email": ""}}, upsert=True)
        async def fake(**kw):
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        ok = _run(srv._send_staff_birthday_list(date.today()))
        assert ok is False
