"""Iter 41 — Scheduled alerts, tap tracking, weekly summary, This Week."""
import os
import sys
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
ET = ZoneInfo("America/New_York")

sys.path.insert(0, '/app/backend')
db_sync = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


def _run(coros):
    """Run coroutines in a fresh loop; rebind motor client so it uses this loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        import server as _srv
        from motor.motor_asyncio import AsyncIOMotorClient as _AMC
        _srv.client = _AMC(os.environ['MONGO_URL'], io_loop=loop)
        _srv.db = _srv.client[os.environ['DB_NAME']]
        results = []
        for c in coros:
            results.append(loop.run_until_complete(c))
        return results
    finally:
        loop.close()

ADMIN = {"session_token": "qa_tok_123"}
MEM_A = {"session_token": "mem_tok_a"}
MEM_B = {"session_token": "mem_tok_b"}
H = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}


def _activate_member(uid):
    db_sync.users.update_one({"user_id": uid}, {"$set": {"member_status": "active"}})


@pytest.fixture(autouse=True)
def ensure_active():
    _activate_member("qa_mem_a")
    _activate_member("qa_mem_b")
    yield


def _iso_future_local(mins=30):
    return (datetime.now(ET) + timedelta(minutes=mins)).strftime("%Y-%m-%dT%H:%M")


def _iso_past_local():
    return (datetime.now(ET) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M")


# ---------- Scheduled alerts CRUD ----------
class TestScheduledAlerts:
    def test_schedule_past_time_400(self):
        r = requests.post(f"{BASE_URL}/api/admin/members/push/scheduled", cookies=ADMIN, headers=H,
                          json={"title": "QA T", "body": "QA B", "url": "/members", "send_at": _iso_past_local()})
        assert r.status_code == 400, r.text

    def test_schedule_missing_title_400(self):
        r = requests.post(f"{BASE_URL}/api/admin/members/push/scheduled", cookies=ADMIN, headers=H,
                          json={"title": "   ", "body": "QA B", "url": "/members", "send_at": _iso_future_local(60)})
        assert r.status_code == 400

    def test_schedule_non_admin_403(self):
        r = requests.post(f"{BASE_URL}/api/admin/members/push/scheduled", cookies=MEM_A, headers=H,
                          json={"title": "QA T", "body": "QA B", "url": "/members", "send_at": _iso_future_local(60)})
        assert r.status_code == 403

    def test_schedule_crud_valid(self):
        local = _iso_future_local(60)
        r = requests.post(f"{BASE_URL}/api/admin/members/push/scheduled", cookies=ADMIN, headers=H,
                          json={"title": "QA Scheduled", "body": "Body", "url": "/members", "send_at": local})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["send_at_local"] == local
        # send_at should be UTC ISO
        at_utc = datetime.fromisoformat(d["send_at"])
        assert at_utc.tzinfo is not None
        sid = d["id"]

        # GET lists only status=scheduled
        g = requests.get(f"{BASE_URL}/api/admin/members/push/scheduled", cookies=ADMIN)
        assert g.status_code == 200
        assert any(x["id"] == sid for x in g.json())

        # PUT edit
        new_local = _iso_future_local(90)
        u = requests.put(f"{BASE_URL}/api/admin/members/push/scheduled/{sid}", cookies=ADMIN, headers=H,
                        json={"title": "QA Edited", "body": "Body2", "url": "/members", "send_at": new_local})
        assert u.status_code == 200
        assert u.json()["title"] == "QA Edited"
        assert u.json()["send_at_local"] == new_local

        # DELETE cancel
        c = requests.delete(f"{BASE_URL}/api/admin/members/push/scheduled/{sid}", cookies=ADMIN, headers=H)
        assert c.status_code == 200

        # Subsequent PUT/DELETE 404
        u2 = requests.put(f"{BASE_URL}/api/admin/members/push/scheduled/{sid}", cookies=ADMIN, headers=H,
                         json={"title": "x", "body": "y", "url": "/members", "send_at": _iso_future_local(120)})
        assert u2.status_code == 404
        c2 = requests.delete(f"{BASE_URL}/api/admin/members/push/scheduled/{sid}", cookies=ADMIN, headers=H)
        assert c2.status_code == 404

        # Cleanup
        db_sync.push_scheduled.delete_one({"id": sid})


# ---------- _send_scheduled in-process ----------
class TestSendScheduled:
    def test_send_scheduled_fires_once(self):
        import server  # noqa
        sid = f"qa_sch_{uuid.uuid4().hex[:8]}"
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        db_sync.push_scheduled.insert_one({
            "id": sid, "title": "QA Scheduled In-Proc", "body": "B", "url": "/members",
            "send_at": past, "send_at_local": "2025-01-01T00:00", "status": "scheduled",
            "created_by": "qa@example.com", "created_at": past,
        })
        try:
            async def _flow():
                await server._send_scheduled()
                before = await server.db.push_log.count_documents({"kind": "custom", "title": "QA Scheduled In-Proc"})
                # second call — nothing new
                await server._send_scheduled()
                after = await server.db.push_log.count_documents({"kind": "custom", "title": "QA Scheduled In-Proc"})
                return before, after
            before, after = _run([_flow()])[0]
            doc = db_sync.push_scheduled.find_one({"id": sid})
            assert doc["status"] == "sent"
            lg = db_sync.push_log.find_one({"kind": "custom", "title": "QA Scheduled In-Proc"})
            assert lg is not None
            assert before == after
            db_sync.push_log.delete_many({"title": "QA Scheduled In-Proc"})
        finally:
            db_sync.push_scheduled.delete_one({"id": sid})


# ---------- Tap tracking ----------
class TestTapped:
    def test_tap_unique_and_history(self):
        log_id = f"qa_log_{uuid.uuid4().hex[:8]}"
        db_sync.push_log.insert_one({
            "id": log_id, "kind": "custom", "title": "QA Tap Alert", "body": "B", "url": "/members",
            "sent_at": datetime.now(timezone.utc).isoformat(), "members": 2, "delivered": 2,
            "failed": 0, "expired": 0, "held": 0,
        })
        try:
            # First tap counts
            r1 = requests.post(f"{BASE_URL}/api/members/push/tapped", cookies=MEM_A, headers=H, json={"log_id": log_id})
            assert r1.status_code == 200
            # Second tap by same user — doesn't double count
            r2 = requests.post(f"{BASE_URL}/api/members/push/tapped", cookies=MEM_A, headers=H, json={"log_id": log_id})
            assert r2.status_code == 200
            # Different user
            r3 = requests.post(f"{BASE_URL}/api/members/push/tapped", cookies=MEM_B, headers=H, json={"log_id": log_id})
            assert r3.status_code == 200
            # Unknown log_id ignored (still 200, no error)
            r4 = requests.post(f"{BASE_URL}/api/members/push/tapped", cookies=MEM_A, headers=H, json={"log_id": "unknown_qa_id"})
            assert r4.status_code == 200

            taps = db_sync.push_taps.count_documents({"log_id": log_id})
            assert taps == 2, f"Expected 2 unique taps, got {taps}"

            # History includes tapped count
            h = requests.get(f"{BASE_URL}/api/admin/members/push/history", cookies=ADMIN)
            assert h.status_code == 200
            row = next((x for x in h.json() if x["id"] == log_id), None)
            assert row is not None
            assert row["tapped"] == 2
        finally:
            db_sync.push_taps.delete_many({"log_id": log_id})
            db_sync.push_taps.delete_many({"log_id": "unknown_qa_id"})
            db_sync.push_log.delete_one({"id": log_id})


# ---------- This Week ----------
class TestThisWeek:
    def test_this_week_sections(self):
        today = datetime.now(ET).date()
        mdate = (today + timedelta(days=3)).isoformat()
        mid = f"qa_meeting_{uuid.uuid4().hex[:8]}"
        aid = f"qa_ann_{uuid.uuid4().hex[:8]}"
        db_sync.member_meetings.insert_one({
            "id": mid, "title": "QA Week Meeting", "date": mdate, "time": "18:00",
            "location": "QA Hall", "kind": "general", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        db_sync.member_announcements.insert_one({
            "id": aid, "title": "QA Week Announcement", "body": "x",
            "created_at": datetime.now(timezone.utc).isoformat(), "author": "qa@example.com",
        })
        try:
            r = requests.get(f"{BASE_URL}/api/members/this-week", cookies=MEM_A)
            assert r.status_code == 200, r.text
            w = r.json()
            for k in ("week_of", "gatherings", "sessions", "votes", "birthdays",
                      "announcements", "spotlights", "minutes"):
                assert k in w, f"Missing section: {k}"
            assert any(g["id"] == mid for g in w["gatherings"])
            assert any(a["id"] == aid for a in w["announcements"])
        finally:
            db_sync.member_meetings.delete_one({"id": mid})
            db_sync.member_announcements.delete_one({"id": aid})


# ---------- Weekly summary admin + _push_weekly ----------
class TestWeeklySummary:
    def test_cfg_toggle_and_preview(self):
        g = requests.get(f"{BASE_URL}/api/admin/members/weekly-summary", cookies=ADMIN)
        assert g.status_code == 200
        d = g.json()
        assert "paused" in d and "preview" in d and "last_sent" in d
        assert isinstance(d["preview"], str) and len(d["preview"]) > 0

        u = requests.put(f"{BASE_URL}/api/admin/members/weekly-summary", cookies=ADMIN, headers=H,
                        json={"paused": True})
        assert u.status_code == 200
        assert u.json()["paused"] is True
        assert requests.get(f"{BASE_URL}/api/admin/members/weekly-summary", cookies=ADMIN).json()["paused"] is True

        u2 = requests.put(f"{BASE_URL}/api/admin/members/weekly-summary", cookies=ADMIN, headers=H,
                         json={"paused": False})
        assert u2.status_code == 200
        assert u2.json()["paused"] is False

    def test_send_now(self):
        before = db_sync.push_log.count_documents({"kind": "weekly"})
        r = requests.post(f"{BASE_URL}/api/admin/members/weekly-summary/send", cookies=ADMIN, headers=H)
        if r.status_code == 429:
            pytest.skip("Rate-limited (admin-weekly 3/10min) by earlier run")
        assert r.status_code == 200, r.text
        assert "sent" in r.json()
        after = db_sync.push_log.count_documents({"kind": "weekly"})
        assert after == before + 1
        lg = db_sync.push_log.find_one({"kind": "weekly"}, sort=[("sent_at", -1)])
        assert lg["url"] == "/members?tab=week"

    def test_push_weekly_scenarios(self):
        import server
        # Clear marks + weekly logs for clean test
        db_sync.push_marks.delete_many({"key": {"$regex": "^weekly:"}})

        # Pick a Sunday 18:30 ET
        today = datetime.now(ET).date()
        offset = (6 - today.weekday()) % 7  # Sunday = 6
        sunday_date = today + timedelta(days=offset or 7)
        sunday_630pm = datetime(sunday_date.year, sunday_date.month, sunday_date.day, 18, 30, tzinfo=ET).astimezone(timezone.utc)
        sunday_before_6 = datetime(sunday_date.year, sunday_date.month, sunday_date.day, 17, 30, tzinfo=ET).astimezone(timezone.utc)
        monday_date = sunday_date + timedelta(days=1)
        monday_630pm = datetime(monday_date.year, monday_date.month, monday_date.day, 18, 30, tzinfo=ET).astimezone(timezone.utc)

        db_sync.settings.update_one({"key": "weekly_summary"}, {"$set": {"paused": False}}, upsert=True)

        async def _flow():
            r1 = await server._push_weekly(now=monday_630pm)
            r2 = await server._push_weekly(now=sunday_before_6)
            cnt_before = await asyncio.to_thread(lambda: db_sync.push_log.count_documents({"kind": "weekly"}))
            await server._push_weekly(now=sunday_630pm)
            cnt_mid = await asyncio.to_thread(lambda: db_sync.push_log.count_documents({"kind": "weekly"}))
            await server._push_weekly(now=sunday_630pm)
            cnt_after = await asyncio.to_thread(lambda: db_sync.push_log.count_documents({"kind": "weekly"}))
            # paused scenario
            await asyncio.to_thread(
                lambda: (
                    db_sync.push_marks.delete_many({"key": {"$regex": "^weekly:"}}),
                    db_sync.settings.update_one({"key": "weekly_summary"}, {"$set": {"paused": True}}, upsert=True),
                )
            )
            r_paused = await server._push_weekly(now=sunday_630pm)
            return r1, r2, cnt_before, cnt_mid, cnt_after, r_paused
        r1, r2, cb, cm, ca, r_paused = _run([_flow()])[0]
        assert r1 == 0 and r2 == 0
        assert cm == cb + 1
        assert ca == cm
        assert r_paused == 0

        db_sync.settings.update_one({"key": "weekly_summary"}, {"$set": {"paused": False}}, upsert=True)
        db_sync.push_marks.delete_many({"key": {"$regex": "^weekly:"}})


# ---------- Profile push_weekly persistence ----------
class TestProfilePushWeekly:
    def test_push_weekly_persists(self):
        payload = {
            "quiet_on": False, "quiet_start": "21:00", "quiet_end": "08:00",
            "push_events": True, "push_votes": True, "push_bday": True, "push_weekly": False,
            "push_news": True, "push_prayer": True, "bday_notices": True, "bday_card": True,
        }
        # Use only known fields — model may ignore extras but push_weekly should persist
        r = requests.put(f"{BASE_URL}/api/members/profile", cookies=MEM_A, headers=H, json=payload)
        assert r.status_code == 200, r.text
        u = db_sync.users.find_one({"user_id": "qa_mem_a"}, {"_id": 0})
        assert (u.get("member_profile") or {}).get("push_weekly") is False
        # Flip back true
        payload["push_weekly"] = True
        r2 = requests.put(f"{BASE_URL}/api/members/profile", cookies=MEM_A, headers=H, json=payload)
        assert r2.status_code == 200
        u2 = db_sync.users.find_one({"user_id": "qa_mem_a"}, {"_id": 0})
        assert (u2.get("member_profile") or {}).get("push_weekly") is True


# ---------- Final cleanup ----------
def teardown_module(module):
    db_sync.push_marks.delete_many({"key": {"$regex": "^weekly:"}})
    db_sync.push_log.delete_many({"title": {"$regex": "^QA"}})
    db_sync.push_log.delete_many({"title": "Your week with the Club"})
    db_sync.push_scheduled.delete_many({"title": {"$regex": "^QA"}})
    db_sync.push_taps.delete_many({"log_id": {"$regex": "^qa_"}})
    db_sync.member_meetings.delete_many({"title": {"$regex": "^QA"}})
    db_sync.member_announcements.delete_many({"title": {"$regex": "^QA"}})
    db_sync.settings.update_one({"key": "weekly_summary"}, {"$set": {"paused": False}}, upsert=True)
