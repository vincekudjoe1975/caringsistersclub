"""
Iter 40 — Install banner, quiet hours, wish alerts, gathering 2h, test push.
Requires qa_session.py up (admin cookie qa_tok_123) and qa_members.py up (mem_tok_a, mem_tok_b).
"""
import asyncio
import os
import sys
import urllib.parse

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
DB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

ADMIN_COOKIE = {"session_token": "qa_tok_123"}
MEM_A = {"session_token": "mem_tok_a"}
MEM_B = {"session_token": "mem_tok_b"}
XH = {"X-Requested-With": "XMLHttpRequest"}


def _activate(uid):
    DB.users.update_one({"user_id": uid}, {"$set": {"member_status": "active"}})


def _pending(uid):
    DB.users.update_one({"user_id": uid}, {"$set": {"member_status": "pending"}})


@pytest.fixture(autouse=True)
def ensure_active():
    _activate("qa_mem_a")
    _activate("qa_mem_b")
    yield


@pytest.fixture(scope="module", autouse=True)
def setup_members():
    _activate("qa_mem_a")
    _activate("qa_mem_b")
    yield
    # Minimal cleanup only; avoid cross-worker races by not touching shared docs
    DB.push_subs.delete_many({"endpoint": {"$regex": "ITER40"}})


# ---------- Profile quiet hours ----------
class TestQuietHoursProfile:
    def _put(self, cookie, start, end, on=True):
        payload = {"city": "", "phone": "", "bio": "", "show_contact": False,
                   "birthday_month": None, "birthday_day": None, "prayer_weekly": True,
                   "bday_notices": True, "bday_card": True, "push_news": True, "push_prayer": True,
                   "push_events": True, "push_votes": True, "push_bday": True,
                   "quiet_on": on, "quiet_start": start, "quiet_end": end}
        return requests.put(f"{API}/members/profile", json=payload, cookies=cookie, headers=XH, timeout=10)

    def test_valid_quiet_hours_saved(self):
        r = self._put(MEM_A, "22:00", "07:00", on=True)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["quiet_on"] is True and d["quiet_start"] == "22:00" and d["quiet_end"] == "07:00"
        # verify via GET /members/me
        me = requests.get(f"{API}/members/me", cookies=MEM_A, timeout=10).json()
        assert me["profile"]["quiet_on"] is True
        assert me["profile"]["quiet_start"] == "22:00"
        assert me["profile"]["quiet_end"] == "07:00"

    def test_invalid_time_400(self):
        r = self._put(MEM_A, "25:00", "07:00")
        assert r.status_code == 400

    def test_equal_times_400(self):
        r = self._put(MEM_A, "21:00", "21:00")
        assert r.status_code == 400


# ---------- Admin push test ----------
class TestAdminPushTest:
    FAKE_EP = f"https://fcm.googleapis.com/fcm/send/ITER40_admin_{os.getpid()}"

    def test_no_devices_400(self):
        DB.push_subs.delete_many({"user_id": "qa_user"})
        r = requests.post(f"{API}/admin/members/push/test",
                          json={"title": "ITER40 test", "body": "hi", "url": "/members"},
                          cookies=ADMIN_COOKIE, headers=XH, timeout=10)
        assert r.status_code == 400
        assert "phone alerts" in r.json()["detail"].lower()

    def test_with_fake_sub_sends_and_logs(self):
        DB.push_subs.insert_one({"user_id": "qa_user", "endpoint": self.FAKE_EP,
                                 "keys": {"p256dh": "x", "auth": "y"}})
        try:
            r = requests.post(f"{API}/admin/members/push/test",
                              json={"title": "ITER40 Test Title", "body": "body", "url": "/members"},
                              cookies=ADMIN_COOKIE, headers=XH, timeout=15)
            assert r.status_code == 200, r.text
            data = r.json()
            assert "sent" in data and "devices" in data
            assert data["devices"] >= 1
            # Log row exists with kind=test and [Test] prefix
            log = DB.push_log.find_one({"title": "[Test] ITER40 Test Title"}, {"_id": 0})
            assert log is not None, "push_log row not written"
            assert log["kind"] == "test"
            assert log["title"].startswith("[Test] ")
        finally:
            DB.push_subs.delete_many({"endpoint": self.FAKE_EP})

    def test_test_targets_only_self(self):
        # Insert a sub for mem_a; admin test should NOT include that user
        other_ep = f"https://fcm.googleapis.com/fcm/send/ITER40_mema_{os.getpid()}"
        DB.push_subs.insert_one({"user_id": "qa_user", "endpoint": self.FAKE_EP,
                                 "keys": {"p256dh": "x", "auth": "y"}})
        DB.push_subs.insert_one({"user_id": "qa_mem_a", "endpoint": other_ep,
                                 "keys": {"p256dh": "x", "auth": "y"}})
        try:
            r = requests.post(f"{API}/admin/members/push/test",
                              json={"title": "ITER40 scope", "body": "b", "url": "/members"},
                              cookies=ADMIN_COOKIE, headers=XH, timeout=15)
            assert r.status_code == 200
            # Only admin's device counted
            assert r.json()["devices"] == 1
        finally:
            DB.push_subs.delete_many({"endpoint": {"$in": [self.FAKE_EP, other_ep]}})

    def test_non_admin_403(self):
        r = requests.post(f"{API}/admin/members/push/test",
                          json={"title": "x", "body": "y", "url": "/members"},
                          cookies=MEM_A, headers=XH, timeout=10)
        assert r.status_code == 403


# ---------- History filters ----------
class TestHistoryFilters:
    def test_filter_test_and_wish(self):
        # Ensure at least a test row & a wish row exist
        DB.push_log.insert_one({"id": "iter40-test-log", "kind": "test", "title": "[Test] ITER40 hist", "body": "b", "url": "/m", "sent_at": "2099-01-01T00:00:00+00:00", "members": 1, "delivered": 0, "failed": 0, "expired": 0, "held": 0})
        DB.push_log.insert_one({"id": "iter40-wish-log", "kind": "wish", "title": "ITER40 wish hist", "body": "b", "url": "/m", "sent_at": "2099-01-01T00:00:00+00:00", "members": 1, "delivered": 0, "failed": 0, "expired": 0, "held": 0})
        try:
            rt = requests.get(f"{API}/admin/members/push/history", params={"kind": "test"}, cookies=ADMIN_COOKIE, timeout=10)
            assert rt.status_code == 200
            kinds_t = {r["kind"] for r in rt.json()}
            assert kinds_t == {"test"} or ("test" in kinds_t and len(kinds_t) == 1)
            assert any(r["id"] == "iter40-test-log" for r in rt.json())

            rw = requests.get(f"{API}/admin/members/push/history", params={"kind": "wish"}, cookies=ADMIN_COOKIE, timeout=10)
            assert rw.status_code == 200
            kinds_w = {r["kind"] for r in rw.json()}
            assert kinds_w == {"wish"}
            assert any(r["id"] == "iter40-wish-log" for r in rw.json())
        finally:
            DB.push_log.delete_many({"id": {"$in": ["iter40-test-log", "iter40-wish-log"]}})


# ---------- Wish alert ----------
class TestWishAlert:
    def test_wish_from_other_triggers_wish_log_to_recipient_only(self):
        # Clear any prior log for this title
        DB.push_log.delete_many({"kind": "wish", "title": "A new birthday wish for you"})
        DB.member_threads.delete_many({"key": {"$regex": "^birthday:qa_mem_a:"}})
        # mem_b posts a wish for mem_a
        r = requests.post(f"{API}/members/birthdays/qa_mem_a/wish",
                          json={"message": "ITER40 wish from B"},
                          cookies=MEM_B, headers=XH, timeout=10)
        assert r.status_code == 200, r.text
        # Background task may take a moment
        import time
        for _ in range(10):
            log = DB.push_log.find_one({"kind": "wish", "title": "A new birthday wish for you"}, sort=[("sent_at", -1)])
            if log:
                break
            time.sleep(0.3)
        assert log is not None, "wish push_log row not created"
        assert log["members"] == 1  # only recipient

    def test_wish_self_no_log(self):
        before = DB.push_log.count_documents({"kind": "wish"})
        # mem_a wishes themselves (shouldn't push to self)
        r = requests.post(f"{API}/members/birthdays/qa_mem_a/wish",
                          json={"message": "ITER40 self wish"},
                          cookies=MEM_A, headers=XH, timeout=10)
        assert r.status_code == 200
        import time
        time.sleep(1.0)
        after = DB.push_log.count_documents({"kind": "wish"})
        # _push_wish early-returns when uid == author -> no log row
        assert after == before, f"expected no new wish log, before={before} after={after}"

    def test_reply_on_birthday_thread_triggers_wish(self):
        # Find the thread id
        import time
        thr = DB.member_threads.find_one({"key": {"$regex": "^birthday:qa_mem_a:"}})
        assert thr is not None
        before = DB.push_log.count_documents({"kind": "wish"})
        r = requests.post(f"{API}/members/threads/{thr['id']}/replies",
                          json={"body": "ITER40 reply wish"},
                          cookies=MEM_B, headers=XH, timeout=10)
        assert r.status_code == 200, r.text
        for _ in range(10):
            if DB.push_log.count_documents({"kind": "wish"}) > before:
                break
            time.sleep(0.3)
        assert DB.push_log.count_documents({"kind": "wish"}) > before


# ---------- In-process quiet hours & release held ----------
class TestQuietHoursInProcess:
    @classmethod
    def setup_class(cls):
        sys.path.insert(0, "/app/backend")
        import importlib
        cls.server = importlib.import_module("server")

    def test_quiet_now_overnight_and_sameday(self):
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        # Overnight 22:00 -> 07:00
        prof = {"quiet_on": True, "quiet_start": "22:00", "quiet_end": "07:00"}
        now_in = datetime(2026, 1, 15, 23, 30, tzinfo=et).astimezone(timezone.utc)
        now_out = datetime(2026, 1, 15, 10, 0, tzinfo=et).astimezone(timezone.utc)
        assert self.server._quiet_now(prof, now_in) is True
        assert self.server._quiet_now(prof, now_out) is False
        # Same day 10:00 -> 12:00
        prof2 = {"quiet_on": True, "quiet_start": "10:00", "quiet_end": "12:00"}
        assert self.server._quiet_now(prof2, datetime(2026, 1, 15, 11, 0, tzinfo=et).astimezone(timezone.utc)) is True
        assert self.server._quiet_now(prof2, datetime(2026, 1, 15, 9, 0, tzinfo=et).astimezone(timezone.utc)) is False
        # Off
        assert self.server._quiet_now({"quiet_on": False, "quiet_start": "00:00", "quiet_end": "23:59"}, now_in) is False

    def test_push_users_holds_during_quiet_and_release(self):
        # Setup: mem_a with quiet on covering NOW, and a fake sub
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        now_et = datetime.now(et)
        # window = now-1h .. now+1h
        start_t = (now_et.replace(hour=(now_et.hour - 1) % 24, minute=0)).strftime("%H:%M")
        end_t = (now_et.replace(hour=(now_et.hour + 1) % 24, minute=0)).strftime("%H:%M")
        if start_t == end_t:
            end_t = (now_et.replace(hour=(now_et.hour + 2) % 24, minute=0)).strftime("%H:%M")
        DB.users.update_one({"user_id": "qa_mem_a"},
                            {"$set": {"member_profile.quiet_on": True,
                                      "member_profile.quiet_start": start_t,
                                      "member_profile.quiet_end": end_t,
                                      "member_profile.push_news": True}})
        fake_ep = f"https://fcm.googleapis.com/fcm/send/ITER40_quiet_{os.getpid()}"
        DB.push_subs.insert_one({"user_id": "qa_mem_a", "endpoint": fake_ep,
                                 "keys": {"p256dh": "x", "auth": "y"}})
        DB.push_held.delete_many({"user_id": "qa_mem_a"})
        DB.push_log.delete_many({"title": "ITER40 quiet"})
        try:
            # Trigger push during quiet hours
            asyncio.get_event_loop().run_until_complete(
                self.server._push_users(["qa_mem_a"], "ITER40 quiet", "body", "/members", "announcement")
            )
            held_rows = list(DB.push_held.find({"user_id": "qa_mem_a"}))
            assert len(held_rows) == 1, f"expected 1 held row, got {len(held_rows)}"
            log = DB.push_log.find_one({"title": "ITER40 quiet"})
            assert log["held"] == 1
            # Release outside quiet
            out_now = datetime.now(timezone.utc).replace(year=2026, month=1, day=15, hour=15, minute=0)
            # Pick a time clearly outside the window
            outside = datetime(2026, 1, 15, (now_et.hour + 6) % 24, 0, tzinfo=et).astimezone(timezone.utc)
            # Ensure outside really is outside window:
            prof = {"quiet_on": True, "quiet_start": start_t, "quiet_end": end_t}
            assert self.server._quiet_now(prof, outside) is False
            asyncio.get_event_loop().run_until_complete(self.server._release_held(outside))
            held_after = DB.push_held.count_documents({"user_id": "qa_mem_a"})
            assert held_after == 0, "held rows should be cleared"
            # push_log held should have been decremented
            log2 = DB.push_log.find_one({"title": "ITER40 quiet"})
            assert log2["held"] == 0, f"held not decremented: {log2}"
        finally:
            DB.push_subs.delete_many({"endpoint": fake_ep})
            DB.users.update_one({"user_id": "qa_mem_a"},
                                {"$unset": {"member_profile.quiet_on": "",
                                            "member_profile.quiet_start": "",
                                            "member_profile.quiet_end": ""}})


# ---------- Gathering 2h ----------
class TestGathering2h:
    @classmethod
    def setup_class(cls):
        sys.path.insert(0, "/app/backend")
        import importlib
        cls.server = importlib.import_module("server")

    def _insert_meeting(self, mid, minutes_ahead, with_rsvp=True, time_override=None):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        now_et = datetime.now(et)
        start = now_et.replace(second=0, microsecond=0)
        start_min_total = now_et.hour * 60 + now_et.minute + minutes_ahead
        hh, mm = (start_min_total // 60) % 24, start_min_total % 60
        time_str = time_override if time_override is not None else f"{hh:02d}:{mm:02d}"
        doc = {"id": mid, "title": f"ITER40 {mid}", "date": now_et.date().isoformat(),
               "time": time_str, "location": "100 Main St, Wilmington DE",
               "rsvps": {"qa_mem_a": {"response": "yes"}} if with_rsvp else {}}
        DB.member_meetings.insert_one(doc)
        return doc

    def test_gathering_soon_sends_and_dedups(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        mid = f"ITER40g1_{os.getpid()}"
        DB.member_meetings.delete_many({"id": mid})
        DB.push_log.delete_many({"title": {"$regex": f"^Starting soon: ITER40 {mid}$"}})
        DB.push_marks.delete_many({"key": {"$regex": f"^event2h:{mid}:"}})
        self._insert_meeting(mid, 90)
        try:
            n1 = asyncio.get_event_loop().run_until_complete(self.server._push_gathering_soon())
            log = DB.push_log.find_one({"title": f"Starting soon: ITER40 {mid}"})
            assert log is not None, "gathering push_log not created"
            assert log["kind"] == "event"
            assert "google.com/maps/dir" in log["url"]
            assert urllib.parse.quote("100 Main St, Wilmington DE", safe="") in log["url"] or "100%20Main" in log["url"] or "100+Main" in log["url"]
            # dedup via mark
            mark = DB.push_marks.find_one({"key": f"event2h:{mid}:{datetime.now(et).date().isoformat()}"})
            assert mark is not None
            n2 = asyncio.get_event_loop().run_until_complete(self.server._push_gathering_soon())
            # No new log for this id
            cnt = DB.push_log.count_documents({"title": f"Starting soon: ITER40 {mid}"})
            assert cnt == 1, f"expected 1 log, got {cnt}"
        finally:
            DB.member_meetings.delete_many({"id": mid})
            DB.push_marks.delete_many({"key": f"event2h:{mid}:{DB.member_meetings.find_one({'id': mid}) and ''}"})

    def test_no_time_or_too_far_skips(self):
        mid_far = f"ITER40far_{os.getpid()}"
        mid_notime = f"ITER40nt_{os.getpid()}"
        DB.member_meetings.delete_many({"id": {"$in": [mid_far, mid_notime]}})
        # 180 min ahead -> skip
        self._insert_meeting(mid_far, 180)
        # No time -> invalid pattern
        self._insert_meeting(mid_notime, 90, time_override="")
        try:
            asyncio.get_event_loop().run_until_complete(self.server._push_gathering_soon())
            assert DB.push_log.find_one({"title": f"Starting soon: ITER40 {mid_far}"}) is None
            assert DB.push_log.find_one({"title": f"Starting soon: ITER40 {mid_notime}"}) is None
        finally:
            DB.member_meetings.delete_many({"id": {"$in": [mid_far, mid_notime]}})


# ---------- App installed ----------
class TestAppInstalled:
    def test_app_installed_then_me_returns_true(self):
        # ensure cleared
        DB.users.update_one({"user_id": "qa_mem_a"}, {"$unset": {"app_installed_at": ""}})
        me1 = requests.get(f"{API}/members/me", cookies=MEM_A, timeout=10).json()
        assert me1["app_installed"] is False
        r = requests.post(f"{API}/members/app-installed", cookies=MEM_A, headers=XH, timeout=10)
        assert r.status_code == 200
        me2 = requests.get(f"{API}/members/me", cookies=MEM_A, timeout=10).json()
        assert me2["app_installed"] is True
        DB.users.update_one({"user_id": "qa_mem_a"}, {"$unset": {"app_installed_at": ""}})
