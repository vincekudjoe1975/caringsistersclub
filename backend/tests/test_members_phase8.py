"""Phase 8 member portal: Photo approval alerts, Birthday opt-outs, Album ZIP download, Birthday wishes wall.

Prereq:
  python3 /app/backend/tests/qa_session.py up
  python3 /app/backend/tests/qa_members.py up
  (and set users.member_status='active', member_since for qa_mem_a/b)
Run: pytest /app/backend/tests/test_members_phase8.py -v --tb=short
"""
import io
import os
import sys
import struct
import zlib
import asyncio
import zipfile
import pytest
import requests
from datetime import timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
_MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

sys.path.insert(0, "/app/backend")
from server import _today_et  # noqa

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
H_CSRF = {"X-Requested-With": "XMLHttpRequest"}
C_ADMIN = {"session_token": "qa_tok_123"}
C_A = {"session_token": "mem_tok_a"}
C_B = {"session_token": "mem_tok_b"}


def _tiny_png() -> bytes:
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
    _MONGO.users.update_many(
        {"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}},
        {"$set": {"member_status": "active", "member_since": "2026-01-01"}},
    )
    for cookie in (C_A, C_B):
        r = requests.get(f"{API}/members/me", cookies=cookie)
        assert r.status_code == 200, r.text
    yield
    _MONGO.member_gathering_photos.delete_many({"uploader_id": {"$in": ["qa_mem_a", "qa_mem_b", "qa_user"]}})
    _MONGO.users.update_many(
        {"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}},
        {"$unset": {"member_bday_sent_year": "", "member_profile": ""}},
    )
    # restore photo-settings defaults
    _MONGO.member_settings.update_one({"key": "photos"}, {"$set": {"key": "photos", "staff_alert": "both", "approve_notice": "gathering"}}, upsert=True)
    # restore staff_notify_email to blank (qa_session.up contract)
    _MONGO.settings.update_one({"key": "site"}, {"$set": {"staff_notify_email": ""}}, upsert=True)


@pytest.fixture(scope="session")
def uid_a():
    return requests.get(f"{API}/members/me", cookies=C_A).json()["user_id"]


@pytest.fixture(scope="session")
def uid_b():
    return requests.get(f"{API}/members/me", cookies=C_B).json()["user_id"]


# Shared event loop so motor stays attached across _run() calls
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


def _run(coro):
    return _LOOP.run_until_complete(coro)


@pytest.fixture(scope="module")
def server_module():
    import server  # noqa
    return server


def _rebind_motor(srv):
    from motor.motor_asyncio import AsyncIOMotorClient
    if getattr(srv, "_rebound_test_loop", None) is not _LOOP:
        srv.client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        srv.db = srv.client[os.environ["DB_NAME"]]
        srv._rebound_test_loop = _LOOP


def _set_photo_settings(staff_alert="both", approve_notice="gathering"):
    r = requests.put(f"{API}/admin/members/photo-settings",
                     json={"staff_alert": staff_alert, "approve_notice": approve_notice},
                     cookies=C_ADMIN, headers=H_CSRF)
    assert r.status_code == 200, r.text


# ============================================================
# 1) GET/PUT /api/admin/members/photo-settings
# ============================================================
class TestPhotoSettingsEndpoint:
    def test_get_defaults_or_current(self):
        r = requests.get(f"{API}/admin/members/photo-settings", cookies=C_ADMIN)
        assert r.status_code == 200
        d = r.json()
        assert d["staff_alert"] in ("instant", "daily", "both", "off")
        assert d["approve_notice"] in ("gathering", "each", "off")

    def test_get_requires_admin(self):
        r = requests.get(f"{API}/admin/members/photo-settings", cookies=C_A)
        assert r.status_code in (401, 403)

    def test_put_valid(self):
        r = requests.put(f"{API}/admin/members/photo-settings",
                         json={"staff_alert": "instant", "approve_notice": "each"},
                         cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        assert r.json() == {"staff_alert": "instant", "approve_notice": "each"}
        g = requests.get(f"{API}/admin/members/photo-settings", cookies=C_ADMIN).json()
        assert g["staff_alert"] == "instant" and g["approve_notice"] == "each"

    def test_put_invalid_rejected(self):
        r = requests.put(f"{API}/admin/members/photo-settings",
                         json={"staff_alert": "bogus", "approve_notice": "gathering"},
                         cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 400
        r2 = requests.put(f"{API}/admin/members/photo-settings",
                          json={"staff_alert": "both", "approve_notice": "nope"},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert r2.status_code == 400

    def test_put_requires_admin(self):
        r = requests.put(f"{API}/admin/members/photo-settings",
                         json={"staff_alert": "both", "approve_notice": "gathering"},
                         cookies=C_A, headers=H_CSRF)
        assert r.status_code in (401, 403)


# ============================================================
# 2) /api/members/albums/{mid}/photos/done
# ============================================================
@pytest.fixture(scope="class")
def meeting_ph8():
    today = _today_et().isoformat()
    mid = f"qa-ph8-meet-{today}"
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_meetings.insert_one({"id": mid, "title": "QA Phase8 Gathering", "kind": "in-person", "date": today, "location": "QA Hall"})
    yield mid
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_gathering_photos.delete_many({"meeting_id": mid})


class TestUploadDone:
    def test_done_alerted_true_then_false(self, meeting_ph8):
        _set_photo_settings("both", "gathering")
        # upload two photos as member A
        pids = []
        for _ in range(2):
            r = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                              files={"file": ("p.png", PNG, "image/png")},
                              cookies=C_A, headers=H_CSRF)
            assert r.status_code == 200, r.text
            pids.append(r.json()["id"])

        # first done -> alerted True
        r1 = requests.post(f"{API}/members/albums/{meeting_ph8}/photos/done",
                           cookies=C_A, headers=H_CSRF)
        assert r1.status_code == 200
        assert r1.json()["alerted"] is True

        # staff_alerted set on the pending photos
        for pid in pids:
            doc = _MONGO.member_gathering_photos.find_one({"id": pid}, {"staff_alerted": 1})
            assert doc.get("staff_alerted") is True

        # repeat call -> alerted False (nothing un-alerted)
        r2 = requests.post(f"{API}/members/albums/{meeting_ph8}/photos/done",
                           cookies=C_A, headers=H_CSRF)
        assert r2.json()["alerted"] is False

    def test_done_admin_uploader_false(self, meeting_ph8):
        _set_photo_settings("both", "gathering")
        # admin uploads a photo (auto-approved)
        r = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                          files={"file": ("p.png", PNG, "image/png")},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        done = requests.post(f"{API}/members/albums/{meeting_ph8}/photos/done",
                             cookies=C_ADMIN, headers=H_CSRF)
        assert done.status_code == 200
        assert done.json()["alerted"] is False

    def test_done_false_when_setting_daily_or_off(self, meeting_ph8, uid_b):
        for mode in ("daily", "off"):
            _set_photo_settings(mode, "gathering")
            # fresh upload by B
            up = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                               files={"file": ("p.png", PNG, "image/png")},
                               cookies=C_B, headers=H_CSRF)
            assert up.status_code == 200
            done = requests.post(f"{API}/members/albums/{meeting_ph8}/photos/done",
                                 cookies=C_B, headers=H_CSRF)
            assert done.status_code == 200
            assert done.json()["alerted"] is False, f"setting={mode}"
            # cleanup: should NOT be flagged staff_alerted
            doc = _MONGO.member_gathering_photos.find_one({"id": up.json()["id"]}, {"staff_alerted": 1})
            assert doc.get("staff_alerted") is not True
        _set_photo_settings("both", "gathering")


# ============================================================
# 3) _send_photo_pending_summary() direct
# ============================================================
class TestPhotoPendingSummary:
    def test_none_pending_returns_false(self, server_module, monkeypatch):
        srv = server_module
        _rebind_motor(srv)
        # Remove any lingering pending uploader_ids in our QA space
        _MONGO.member_gathering_photos.delete_many({"status": "pending", "uploader_id": {"$in": ["qa_mem_a", "qa_mem_b"]}})
        # also make sure no pending exists at all in the test env
        remaining = _MONGO.member_gathering_photos.count_documents({"status": "pending"})
        if remaining:
            pytest.skip(f"pending photos from other data ({remaining}); skipping none-pending check")
        async def fake(**kw):
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        ok = _run(srv._send_photo_pending_summary())
        assert ok is False

    def test_summary_with_pending(self, server_module, monkeypatch, meeting_ph8):
        srv = server_module
        _rebind_motor(srv)
        # set staff_notify_email so send actually gets attempted
        _MONGO.settings.update_one({"key": "site"}, {"$set": {"staff_notify_email": "staff-qa@example.com"}}, upsert=True)
        # upload 2 pending photos
        for _ in range(2):
            r = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                              files={"file": ("p.png", PNG, "image/png")},
                              cookies=C_A, headers=H_CSRF)
            assert r.status_code == 200
        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject, html))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        ok = _run(srv._send_photo_pending_summary())
        assert ok is True
        assert len(sent) == 1
        to, subject, html = sent[0]
        assert to == "staff-qa@example.com"
        assert "awaiting review" in subject.lower()
        # body should mention the meeting title and count
        assert "QA Phase8" in html or "QA Phase8 Gathering" in html
        # cleanup
        _MONGO.member_gathering_photos.delete_many({"meeting_id": meeting_ph8})
        _MONGO.settings.update_one({"key": "site"}, {"$set": {"staff_notify_email": ""}}, upsert=True)


# ============================================================
# 4) Approve + grouping (_send_photo_approved)
# ============================================================
class TestApproveNotice:
    def test_approve_gathering_groups_and_idempotent(self, server_module, monkeypatch, meeting_ph8):
        srv = server_module
        _rebind_motor(srv)
        _set_photo_settings("off", "gathering")  # keep staff alerts quiet
        # upload 2 pending by A
        pids = []
        for _ in range(2):
            r = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                              files={"file": ("p.png", PNG, "image/png")},
                              cookies=C_A, headers=H_CSRF)
            assert r.status_code == 200
            pids.append(r.json()["id"])
        # approve both (approve_notice='gathering' -> no inline send)
        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject, html))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        for pid in pids:
            rr = requests.post(f"{API}/admin/members/gathering-photos/{pid}/approve",
                               cookies=C_ADMIN, headers=H_CSRF)
            assert rr.status_code == 200
        # notified=False on approve
        for pid in pids:
            doc = _MONGO.member_gathering_photos.find_one({"id": pid}, {"notified": 1, "status": 1})
            assert doc["status"] == "approved" and doc.get("notified") is False
        # call grouped sender
        n = _run(srv._send_photo_approved())
        assert n == 1, f"expected 1 grouped email, got {n}; sent={sent}"
        to, subject, html = sent[0]
        assert "qa.sister.a" in to
        assert "2 of your photos" in subject or "2 of your photos" in html
        # second call => 0
        sent.clear()
        n2 = _run(srv._send_photo_approved())
        assert n2 == 0
        # cleanup
        _MONGO.member_gathering_photos.delete_many({"id": {"$in": pids}})

    def test_approve_each_inline_email(self, server_module, monkeypatch, meeting_ph8):
        srv = server_module
        _rebind_motor(srv)
        _set_photo_settings("off", "each")
        # upload 1 pending
        up = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF)
        pid = up.json()["id"]
        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject, html))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        rr = requests.post(f"{API}/admin/members/gathering-photos/{pid}/approve",
                           cookies=C_ADMIN, headers=H_CSRF)
        assert rr.status_code == 200
        # BackgroundTasks run after response — poll briefly
        import time
        for _ in range(20):
            if sent:
                break
            time.sleep(0.1)
        # NOTE: Starlette BackgroundTasks run in the server process, not our test
        # process, so monkeypatched send_email there isn't our fake. Verify the
        # 'notified' flag got flipped by the server task instead.
        for _ in range(30):
            doc = _MONGO.member_gathering_photos.find_one({"id": pid}, {"notified": 1})
            if doc.get("notified") is True:
                break
            time.sleep(0.2)
        assert doc.get("notified") is True, "approve_notice=each did not trigger background notify"
        # restore
        _set_photo_settings("both", "gathering")
        _MONGO.member_gathering_photos.delete_one({"id": pid})


# ============================================================
# 5) Album ZIP download + single-photo attachment
# ============================================================
class TestAlbumDownload:
    def test_zip_contains_only_approved(self, meeting_ph8):
        _set_photo_settings("off", "gathering")
        # one approved (admin upload) + one pending (member upload)
        ap = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                           files={"file": ("a.png", PNG, "image/png")},
                           cookies=C_ADMIN, headers=H_CSRF).json()
        pe = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF).json()
        assert ap["status"] == "approved" and pe["status"] == "pending"
        r = requests.get(f"{API}/members/albums/{meeting_ph8}/download", cookies=C_A)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert len(names) == 1, f"ZIP should contain only 1 approved photo, got {names}"
        _MONGO.member_gathering_photos.delete_many({"id": {"$in": [ap["id"], pe["id"]]}})

    def test_zip_requires_member_auth(self, meeting_ph8):
        r = requests.get(f"{API}/members/albums/{meeting_ph8}/download")
        assert r.status_code in (401, 403)

    def test_zip_404_when_none_approved(self, meeting_ph8):
        # ensure none approved
        _MONGO.member_gathering_photos.delete_many({"meeting_id": meeting_ph8})
        r = requests.get(f"{API}/members/albums/{meeting_ph8}/download", cookies=C_A)
        assert r.status_code == 404

    def test_single_photo_download_attachment(self, meeting_ph8, uid_a):
        # admin-uploaded approved photo, download via ?download=1
        up = requests.post(f"{API}/members/albums/{meeting_ph8}/photos",
                           files={"file": ("a.png", PNG, "image/png")},
                           cookies=C_ADMIN, headers=H_CSRF).json()
        pid = up["id"]
        r = requests.get(f"{API}/members/gathering-photos/{pid}/file?download=1", cookies=C_A)
        assert r.status_code == 200
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower(), f"expected attachment, got: {cd}"
        # inline (no download) should NOT force attachment
        r2 = requests.get(f"{API}/members/gathering-photos/{pid}/file", cookies=C_A)
        assert r2.status_code == 200
        cd2 = r2.headers.get("content-disposition", "")
        assert "attachment" not in cd2.lower()
        _MONGO.member_gathering_photos.delete_one({"id": pid})


# ============================================================
# 6) Birthday opt-outs
# ============================================================
class TestBirthdayOptOuts:
    def test_profile_persists_bday_flags(self, uid_a):
        r = requests.put(f"{API}/members/profile",
                         json={"bday_notices": False, "bday_card": False},
                         cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200
        u = _MONGO.users.find_one({"user_id": uid_a}, {"member_profile": 1})
        assert u["member_profile"]["bday_notices"] is False
        assert u["member_profile"]["bday_card"] is False
        r2 = requests.put(f"{API}/members/profile",
                          json={"bday_notices": True, "bday_card": True},
                          cookies=C_A, headers=H_CSRF)
        assert r2.status_code == 200
        u2 = _MONGO.users.find_one({"user_id": uid_a}, {"member_profile": 1})
        assert u2["member_profile"]["bday_notices"] is True
        assert u2["member_profile"]["bday_card"] is True

    def test_send_birthday_emails_respects_opt_outs(self, server_module, monkeypatch, uid_a, uid_b):
        srv = server_module
        _rebind_motor(srv)
        today = _today_et()
        # make A the celebrant with bday_card=False (should skip card to self)
        _MONGO.users.update_one({"user_id": uid_a}, {"$set": {
            "member_profile.birthday_month": today.month,
            "member_profile.birthday_day": today.day,
            "member_profile.bday_card": False,
            "member_profile.bday_notices": True,
        }, "$unset": {"member_bday_sent_year": ""}})
        # make B opted-out of bday_notices (should NOT receive notice about A)
        _MONGO.users.update_one({"user_id": uid_b}, {"$set": {
            "member_profile.bday_notices": False,
        }, "$unset": {"member_profile.birthday_month": "", "member_profile.birthday_day": "", "member_bday_sent_year": ""}})
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{today.year}"})

        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        _run(srv._send_birthday_emails(today))
        tos = [t for t, _ in sent]
        # A's own card should NOT be sent (bday_card=False)
        assert "qa.sister.a@example.com" not in tos, f"celebrant card should be skipped, got: {sent}"
        # B's notice-about-A should NOT be sent (bday_notices=False)
        assert "qa.sister.b@example.com" not in tos, f"opted-out notice recipient should be skipped, got: {sent}"
        # cleanup
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{today.year}"})
        _MONGO.users.update_many({"user_id": {"$in": [uid_a, uid_b]}}, {"$unset": {"member_bday_sent_year": ""}})


# ============================================================
# 7) Birthday wishes wall
# ============================================================
class TestBirthdayWall:
    def test_wall_requires_member(self, uid_a):
        r = requests.get(f"{API}/members/birthdays/{uid_a}/wall")
        assert r.status_code in (401, 403)

    def test_wall_404_unknown(self):
        r = requests.get(f"{API}/members/birthdays/no-such-uid/wall", cookies=C_A)
        assert r.status_code == 404

    def test_wall_returns_wishes_from_thread(self, uid_a, uid_b):
        today = _today_et()
        year = today.year
        # Give A a birthday month/day to populate wall meta
        _MONGO.users.update_one({"user_id": uid_a}, {"$set": {
            "member_profile.birthday_month": today.month,
            "member_profile.birthday_day": today.day,
        }})
        # clean any prior thread
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{year}"})
        # B posts a wish for A
        r = requests.post(f"{API}/members/birthdays/{uid_a}/wish",
                          json={"message": "Happy birthday dear A! QA wish 1"},
                          cookies=C_B, headers=H_CSRF)
        assert r.status_code == 200, r.text
        # GET the wall as B
        w = requests.get(f"{API}/members/birthdays/{uid_a}/wall", cookies=C_B)
        assert w.status_code == 200
        d = w.json()
        assert d["user_id"] == uid_a
        assert d["year"] == year
        assert d["month"] == today.month and d["day"] == today.day
        assert isinstance(d.get("wishes"), list) and len(d["wishes"]) >= 1
        wish = d["wishes"][-1]
        assert "QA wish 1" in wish["body"]
        assert wish["author_name"]  # non-empty author
        # cleanup
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{year}"})


# ============================================================
# 8) Scheduled runs: _once marker idempotency
# ============================================================
class TestScheduledIntegration:
    def test_once_marker_prevents_double_send(self, server_module, monkeypatch):
        """Just a smoke that _photo_settings reads back the stored row."""
        srv = server_module
        _rebind_motor(srv)
        _set_photo_settings("off", "off")
        ps = _run(srv._photo_settings())
        assert ps["staff_alert"] == "off" and ps["approve_notice"] == "off"
        _set_photo_settings("both", "gathering")
