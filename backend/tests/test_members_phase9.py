"""Phase 9 member portal: Wish reminders, Photo captions, Album slideshow, Gathering recaps.

Prereq:
  python3 /app/backend/tests/qa_session.py up
  python3 /app/backend/tests/qa_members.py up
  (and set users.member_status='active', member_since for qa_mem_a/b)
Run: pytest /app/backend/tests/test_members_phase9.py -v --tb=short
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
    _MONGO.member_meetings.delete_many({"id": {"$regex": "^qa-ph9"}})
    _MONGO.member_threads.delete_many({"key": {"$regex": "^birthday:qa_mem"}})
    _MONGO.scheduled_runs.delete_many({"key": {"$regex": "^wishrem:"}})
    _MONGO.users.update_many(
        {"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}},
        {"$unset": {"member_profile": "", "member_bday_sent_year": ""}},
    )


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


# ------- shared gathering fixture (past, in-person) -------
@pytest.fixture(scope="class")
def meeting_ph9():
    today = _today_et()
    past = (today - timedelta(days=5)).isoformat()
    mid = f"qa-ph9-meet-{today.isoformat()}"
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_meetings.insert_one({"id": mid, "title": "QA Phase9 Gathering",
                                       "kind": "in-person", "date": past, "location": "QA Hall"})
    yield mid
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_gathering_photos.delete_many({"meeting_id": mid})


# ============================================================
# 1) PUT /members/gathering-photos/{pid}/caption
# ============================================================
class TestCaptionEdit:
    def test_upload_with_caption(self, meeting_ph9):
        r = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                          files={"file": ("p.png", PNG, "image/png")},
                          data={"caption": "Dancing sisters"},
                          cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200, r.text
        assert r.json()["caption"] == "Dancing sisters"
        assert r.json()["status"] == "pending"
        _MONGO.member_gathering_photos.delete_one({"id": r.json()["id"]})

    def test_uploader_edit_while_pending(self, meeting_ph9):
        up = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF).json()
        pid = up["id"]
        r = requests.put(f"{API}/members/gathering-photos/{pid}/caption",
                         json={"caption": "After worship"},
                         cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200
        assert r.json()["caption"] == "After worship"
        doc = _MONGO.member_gathering_photos.find_one({"id": pid}, {"caption": 1})
        assert doc["caption"] == "After worship"
        _MONGO.member_gathering_photos.delete_one({"id": pid})

    def test_other_member_cannot_edit_pending(self, meeting_ph9):
        up = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF).json()
        pid = up["id"]
        r = requests.put(f"{API}/members/gathering-photos/{pid}/caption",
                         json={"caption": "nope"},
                         cookies=C_B, headers=H_CSRF)
        assert r.status_code == 403
        _MONGO.member_gathering_photos.delete_one({"id": pid})

    def test_uploader_cannot_edit_after_approval(self, meeting_ph9):
        up = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF).json()
        pid = up["id"]
        ap = requests.post(f"{API}/admin/members/gathering-photos/{pid}/approve",
                           cookies=C_ADMIN, headers=H_CSRF)
        assert ap.status_code == 200
        r = requests.put(f"{API}/members/gathering-photos/{pid}/caption",
                         json={"caption": "too late"},
                         cookies=C_A, headers=H_CSRF)
        assert r.status_code == 403
        _MONGO.member_gathering_photos.delete_one({"id": pid})

    def test_admin_can_edit_any_time(self, meeting_ph9):
        up = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF).json()
        pid = up["id"]
        requests.post(f"{API}/admin/members/gathering-photos/{pid}/approve",
                      cookies=C_ADMIN, headers=H_CSRF)
        r = requests.put(f"{API}/members/gathering-photos/{pid}/caption",
                         json={"caption": "Staff edit"},
                         cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        assert r.json()["caption"] == "Staff edit"
        _MONGO.member_gathering_photos.delete_one({"id": pid})

    def test_caption_truncated_to_200(self, meeting_ph9):
        up = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF).json()
        pid = up["id"]
        long_cap = "x" * 300
        r = requests.put(f"{API}/members/gathering-photos/{pid}/caption",
                         json={"caption": long_cap},
                         cookies=C_A, headers=H_CSRF)
        assert r.status_code == 200
        assert len(r.json()["caption"]) == 200
        _MONGO.member_gathering_photos.delete_one({"id": pid})


# ============================================================
# 2) ZIP includes captions.txt + caption-based filenames
# ============================================================
class TestZipCaptions:
    def test_zip_has_captions_file_and_named_entries(self, meeting_ph9):
        # 2 approved photos with captions, 1 approved without
        pids = []
        for cap in ["Praising together", "Fellowship meal", ""]:
            up = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                               files={"file": ("p.png", PNG, "image/png")},
                               data={"caption": cap},
                               cookies=C_ADMIN, headers=H_CSRF).json()
            pids.append(up["id"])
        r = requests.get(f"{API}/members/albums/{meeting_ph9}/download", cookies=C_A)
        assert r.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert "captions.txt" in names, f"captions.txt missing. names={names}"
        caps_txt = zf.read("captions.txt").decode()
        assert "Praising together" in caps_txt
        assert "Fellowship meal" in caps_txt
        # filename based on caption slug for the two captioned ones
        joined = " ".join(names).lower()
        assert "praising" in joined or "praising-together" in joined, f"caption slug missing: {names}"
        _MONGO.member_gathering_photos.delete_many({"id": {"$in": pids}})


# ============================================================
# 3) GET /members/albums-slideshow
# ============================================================
class TestSlideshowEndpoint:
    def test_slideshow_returns_approved_with_titles(self, meeting_ph9):
        up = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           data={"caption": "slide"},
                           cookies=C_ADMIN, headers=H_CSRF).json()
        pid = up["id"]
        pe = requests.post(f"{API}/members/albums/{meeting_ph9}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_A, headers=H_CSRF).json()
        pending_id = pe["id"]
        r = requests.get(f"{API}/members/albums-slideshow", cookies=C_A)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        ids = {p["id"] for p in rows}
        assert pid in ids
        assert pending_id not in ids, "pending photos should not appear in slideshow"
        hit = next(p for p in rows if p["id"] == pid)
        assert hit["caption"] == "slide"
        assert hit["gathering_title"] == "QA Phase9 Gathering"
        _MONGO.member_gathering_photos.delete_many({"id": {"$in": [pid, pending_id]}})

    def test_slideshow_requires_member(self):
        r = requests.get(f"{API}/members/albums-slideshow")
        assert r.status_code in (401, 403)


# ============================================================
# 4) Wish reminders (direct function call)
# ============================================================
class TestWishReminders:
    def _setup_birthday(self, uid, year_offset=0):
        today = _today_et() + timedelta(days=year_offset)
        _MONGO.users.update_one({"user_id": uid}, {"$set": {
            "member_profile.birthday_month": today.month,
            "member_profile.birthday_day": today.day,
            "member_profile.bday_notices": True,
            "member_profile.bday_card": True,
        }})

    def test_eve_reminder_recipients_and_idempotent(self, server_module, monkeypatch, uid_a, uid_b):
        srv = server_module
        _rebind_motor(srv)
        today = _today_et()
        # celebrant = A tomorrow
        _MONGO.users.update_one({"user_id": uid_a}, {"$set": {
            "member_profile.birthday_month": (today + timedelta(days=1)).month,
            "member_profile.birthday_day": (today + timedelta(days=1)).day,
            "member_profile.bday_notices": True,
            "member_profile.bday_card": True,
        }})
        # B active with bday_notices True
        _MONGO.users.update_one({"user_id": uid_b}, {"$set": {
            "member_profile.bday_notices": True,
        }, "$unset": {"member_profile.birthday_month": "", "member_profile.birthday_day": ""}})
        # Clear idempotency marker + thread
        tomorrow = today + timedelta(days=1)
        _MONGO.scheduled_runs.delete_many({"key": f"wishrem:eve:{uid_a}:{tomorrow.isoformat()}"})
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{tomorrow.year}"})

        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject))
            return True
        monkeypatch.setattr(srv, "send_email", fake)

        n = _run(srv._send_wish_reminders(tomorrow, "eve"))
        tos = [t for t, _ in sent]
        # B should be included; A (celebrant) should NOT
        assert "qa.sister.b@example.com" in tos, f"B missing. sent={sent}"
        assert "qa.sister.a@example.com" not in tos, "celebrant should be excluded"
        assert n >= 1

        # second call => 0 (idempotent via scheduled_runs marker)
        sent.clear()
        n2 = _run(srv._send_wish_reminders(tomorrow, "eve"))
        assert n2 == 0
        assert sent == []

    def test_day_reminder_excludes_posters_and_opted_out(self, server_module, monkeypatch, uid_a, uid_b):
        srv = server_module
        _rebind_motor(srv)
        today = _today_et()
        # celebrant A today
        _MONGO.users.update_one({"user_id": uid_a}, {"$set": {
            "member_profile.birthday_month": today.month,
            "member_profile.birthday_day": today.day,
            "member_profile.bday_notices": True,
        }})
        # B already posted a wish (via HTTP) so should be excluded
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{today.year}"})
        _MONGO.scheduled_runs.delete_many({"key": f"wishrem:day:{uid_a}:{today.isoformat()}"})
        wish = requests.post(f"{API}/members/birthdays/{uid_a}/wish",
                             json={"message": "Happy birthday A!"},
                             cookies=C_B, headers=H_CSRF)
        assert wish.status_code == 200, wish.text

        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        _run(srv._send_wish_reminders(today, "day"))
        tos = [t for t, _ in sent]
        assert "qa.sister.b@example.com" not in tos, "B already wished - should be excluded"
        assert "qa.sister.a@example.com" not in tos, "celebrant excluded"

        # Now opt-out B from bday_notices; clear idempotency and try again (new day call)
        _MONGO.scheduled_runs.delete_many({"key": f"wishrem:day:{uid_a}:{today.isoformat()}"})
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{today.year}"})
        _MONGO.users.update_one({"user_id": uid_b}, {"$set": {"member_profile.bday_notices": False}})
        sent.clear()
        _run(srv._send_wish_reminders(today, "day"))
        tos2 = [t for t, _ in sent]
        assert "qa.sister.b@example.com" not in tos2, "opted-out B should be excluded"
        # restore
        _MONGO.users.update_one({"user_id": uid_b}, {"$set": {"member_profile.bday_notices": True}})
        _MONGO.member_threads.delete_many({"key": f"birthday:{uid_a}:{today.year}"})


# ============================================================
# 5) Recaps: list, preview, tokenized photo, send, auto
# ============================================================
@pytest.fixture(scope="class")
def recap_meeting():
    today = _today_et()
    past = (today - timedelta(days=5)).isoformat()
    mid = f"qa-ph9-recap-{today.isoformat()}"
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_meetings.insert_one({"id": mid, "title": "QA Recap Gathering",
                                       "kind": "in-person", "date": past, "location": "QA Hall"})
    # seed one approved photo
    up = requests.post(f"{API}/members/albums/{mid}/photos",
                       files={"file": ("p.png", PNG, "image/png")},
                       data={"caption": "Group photo"},
                       cookies=C_ADMIN, headers=H_CSRF).json()
    yield mid, up["id"]
    _MONGO.member_meetings.delete_one({"id": mid})
    _MONGO.member_gathering_photos.delete_many({"meeting_id": mid})


class TestRecaps:
    def test_list_includes_past_in_person_with_photos(self, recap_meeting):
        mid, pid = recap_meeting
        r = requests.get(f"{API}/admin/members/recaps", cookies=C_ADMIN)
        assert r.status_code == 200
        rows = r.json()
        hit = next((m for m in rows if m["id"] == mid), None)
        assert hit is not None, f"recap row missing for {mid}"
        assert hit["title"] == "QA Recap Gathering"
        assert any(p["id"] == pid for p in hit["photos"])
        assert "recap_sent_at" not in hit or hit.get("recap_sent_at") in (None, "", False)

    def test_list_requires_admin(self, recap_meeting):
        r = requests.get(f"{API}/admin/members/recaps", cookies=C_A)
        assert r.status_code in (401, 403)

    def test_preview_html_and_tokenized_image(self, recap_meeting):
        mid, pid = recap_meeting
        r = requests.post(f"{API}/admin/members/recaps/{mid}/preview",
                          json={"photo_ids": [pid], "note": "Thank you QA"},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 200
        html = r.json()["html"]
        assert f"/api/recap-photo/{pid}?t=" in html
        assert "QA Recap Gathering" in html
        assert "Thank you QA" in html
        # Pull token out of html
        import re
        m = re.search(rf"/api/recap-photo/{pid}\?t=([A-Za-z0-9_-]+)", html)
        assert m
        token = m.group(1)
        # Correct token => 200 image
        img = requests.get(f"{API}/recap-photo/{pid}", params={"t": token})
        assert img.status_code == 200
        assert img.headers["content-type"].startswith("image/")
        # Wrong token => 404
        bad = requests.get(f"{API}/recap-photo/{pid}", params={"t": "xxx"})
        assert bad.status_code == 404

    def test_preview_rejects_more_than_six_photos(self, recap_meeting):
        mid, _ = recap_meeting
        r = requests.post(f"{API}/admin/members/recaps/{mid}/preview",
                          json={"photo_ids": [f"p{i}" for i in range(7)], "note": ""},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 400

    def test_send_recap_via_function_and_idempotency(self, server_module, monkeypatch, recap_meeting):
        """Call _send_recap directly (monkeypatch send_email) to verify count + idempotency."""
        srv = server_module
        _rebind_motor(srv)
        mid, pid = recap_meeting
        # clear any prior recap_sent_at
        _MONGO.member_meetings.update_one({"id": mid},
            {"$unset": {"recap_sent_at": "", "recap_by": "", "recap_count": "", "recap_photo_ids": ""}})
        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject, html))
            return True
        monkeypatch.setattr(srv, "send_email", fake)
        n = _run(srv._send_recap(mid, [pid], "Thanks sisters", "qa"))
        assert n == 2, f"expected 2 active members, got {n}: {sent}"
        subjects = [s for _, s, _ in sent]
        assert all("QA Recap Gathering" in s for s in subjects)
        # Each HTML has the tokenized URL
        for _, _, html in sent:
            assert f"/api/recap-photo/{pid}?t=" in html

        # Second call => -1 (already sent); no new emails
        sent.clear()
        n2 = _run(srv._send_recap(mid, [pid], "", "qa"))
        assert n2 == -1
        assert sent == []

        # And the HTTP endpoint should 400 duplicate
        r = requests.post(f"{API}/admin/members/recaps/{mid}/send",
                          json={"photo_ids": [pid], "note": ""},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 400
        # Reset
        _MONGO.member_meetings.update_one({"id": mid},
            {"$unset": {"recap_sent_at": "", "recap_by": "", "recap_count": "", "recap_photo_ids": ""}})

    def test_send_requires_admin(self, recap_meeting):
        mid, pid = recap_meeting
        r = requests.post(f"{API}/admin/members/recaps/{mid}/send",
                          json={"photo_ids": [pid], "note": ""},
                          cookies=C_A, headers=H_CSRF)
        assert r.status_code in (401, 403)

    def test_send_404_for_unknown_meeting(self):
        r = requests.post(f"{API}/admin/members/recaps/no-such/send",
                          json={"photo_ids": [], "note": ""},
                          cookies=C_ADMIN, headers=H_CSRF)
        assert r.status_code == 404


# ============================================================
# 6) _auto_recaps: idempotency + window
# ============================================================
class TestAutoRecaps:
    def test_auto_recaps_window_and_idempotent(self, server_module, monkeypatch):
        srv = server_module
        _rebind_motor(srv)
        today = _today_et()
        # In window (5 days ago) with approved photo + no recap_sent_at
        mid_in = f"qa-ph9-auto-in-{today.isoformat()}"
        past_in = (today - timedelta(days=5)).isoformat()
        _MONGO.member_meetings.delete_one({"id": mid_in})
        _MONGO.member_meetings.insert_one({"id": mid_in, "title": "QA Auto In",
                                           "kind": "in-person", "date": past_in})
        up = requests.post(f"{API}/members/albums/{mid_in}/photos",
                           files={"file": ("p.png", PNG, "image/png")},
                           cookies=C_ADMIN, headers=H_CSRF).json()

        # Out of window (1 day ago)
        mid_out = f"qa-ph9-auto-out-{today.isoformat()}"
        past_out = (today - timedelta(days=1)).isoformat()
        _MONGO.member_meetings.delete_one({"id": mid_out})
        _MONGO.member_meetings.insert_one({"id": mid_out, "title": "QA Auto Out",
                                           "kind": "in-person", "date": past_out})
        up2 = requests.post(f"{API}/members/albums/{mid_out}/photos",
                            files={"file": ("p.png", PNG, "image/png")},
                            cookies=C_ADMIN, headers=H_CSRF).json()

        sent = []
        async def fake(to, subject, html, **kw):
            sent.append((to, subject))
            return True
        monkeypatch.setattr(srv, "send_email", fake)

        n = _run(srv._auto_recaps(today))
        assert n >= 1, f"expected at least 1 auto recap; got {n}, sent={sent}"
        # The in-window one should now be marked
        doc = _MONGO.member_meetings.find_one({"id": mid_in}, {"recap_sent_at": 1, "recap_by": 1})
        assert doc.get("recap_sent_at")
        assert doc.get("recap_by") == "auto"
        # out-of-window not marked
        doc2 = _MONGO.member_meetings.find_one({"id": mid_out}, {"recap_sent_at": 1})
        assert not doc2.get("recap_sent_at"), "out-of-window gathering should not be auto-recapped"

        # second call -> 0 (idempotent)
        sent.clear()
        n2 = _run(srv._auto_recaps(today))
        # Account for any other seed gatherings also matching: ours should NOT re-send
        doc3 = _MONGO.member_meetings.find_one({"id": mid_in}, {"recap_sent_at": 1})
        assert doc3.get("recap_sent_at") == doc.get("recap_sent_at"), "recap_sent_at should not change on re-run"

        # cleanup
        _MONGO.member_meetings.delete_many({"id": {"$in": [mid_in, mid_out]}})
        _MONGO.member_gathering_photos.delete_many({"id": {"$in": [up["id"], up2["id"]]}})
