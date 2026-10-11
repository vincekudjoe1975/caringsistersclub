"""Iter 42 — Repeating alerts + weekly email + carpool + sister map + volunteer hours + best times."""
import os
import asyncio
import importlib
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = BASE_URL + "/api"
ADMIN = {"session_token": "qa_tok_123"}
MEM_A = {"session_token": "mem_tok_a"}
MEM_B = {"session_token": "mem_tok_b"}
WRITE_HDRS = {"X-Requested-With": "XMLHttpRequest"}

from pymongo import MongoClient  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# -------- helpers --------
def _s():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _set_member_profile(uid, patch):
    doc = db.users.find_one({"user_id": uid}) or {}
    mp = doc.get("member_profile") or {}
    mp.update(patch)
    db.users.update_one({"user_id": uid}, {"$set": {"member_profile": mp, "member_status": "active"}})


@pytest.fixture(scope="module", autouse=True)
def _setup_members():
    # Mark A and B as active with cities for carpool/map
    _set_member_profile("qa_mem_a", {"city": "Wilmington, DE", "phone": "302-555-0001", "show_on_map": True, "weekly_email": True})
    _set_member_profile("qa_mem_b", {"city": "wilmington,de", "phone": "302-555-0002", "show_on_map": False, "weekly_email": True})
    yield
    # cleanup: remove our scheduled, logs, carpool, taps, meetings, hours created here
    db.push_scheduled.delete_many({"title": {"$regex": "^QA"}})
    db.push_log.delete_many({"title": {"$regex": "^QA"}})
    db.push_log.delete_many({"body": {"$regex": "QA Carpool"}})
    db.push_taps.delete_many({"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}})
    db.member_meetings.delete_many({"title": {"$regex": "^QA"}})
    db.member_carpool.delete_many({"user_id": {"$in": ["qa_mem_a", "qa_mem_b", "qa_mem_c"]}})
    db.volunteer_hours.delete_many({"email": {"$regex": "example.com$"}})
    db.push_marks.delete_many({"key": {"$regex": "^hours-badge:qa_mem"}})
    db.users.delete_one({"user_id": "qa_mem_c"})
    db.user_sessions.delete_one({"session_token": "mem_tok_c"})


# ---------------- 1. Scheduled repeating alerts ----------------
class TestScheduledRepeat:
    def test_weekly_requires_days(self):
        future = (datetime.now(timezone.utc) + timedelta(days=3)).astimezone().strftime("%Y-%m-%dT%H:%M")
        r = requests.post(f"{API}/admin/members/push/scheduled", cookies=ADMIN, headers=WRITE_HDRS,
                          json={"title": "QA bad weekly", "body": "x", "send_at": future, "repeat": "weekly", "days": []})
        assert r.status_code == 400

    def test_invalid_repeat(self):
        future = (datetime.now(timezone.utc) + timedelta(days=3)).astimezone().strftime("%Y-%m-%dT%H:%M")
        r = requests.post(f"{API}/admin/members/push/scheduled", cookies=ADMIN, headers=WRITE_HDRS,
                          json={"title": "QA bad rep", "body": "x", "send_at": future, "repeat": "yearly"})
        assert r.status_code == 400

    def test_end_date_before_start(self):
        future = (datetime.now(timezone.utc) + timedelta(days=10)).astimezone().strftime("%Y-%m-%dT%H:%M")
        bad_end = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        r = requests.post(f"{API}/admin/members/push/scheduled", cookies=ADMIN, headers=WRITE_HDRS,
                          json={"title": "QA bad end", "body": "x", "send_at": future, "repeat": "daily", "end_date": bad_end})
        assert r.status_code == 400

    def test_weekly_schedules_next_matching_mon_thu(self):
        # pick a far-past-time-of-day base so _next_run advances to future
        base_local = "2026-01-05T09:00"  # 2026-01-05 was a Monday
        r = requests.post(f"{API}/admin/members/push/scheduled", cookies=ADMIN, headers=WRITE_HDRS,
                          json={"title": "QA rep weekly", "body": "QA body", "send_at": base_local, "repeat": "weekly", "days": [0, 3]})
        assert r.status_code == 200, r.text
        doc = r.json()
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        send_at = datetime.fromisoformat(doc["send_at"]).astimezone(et)
        assert send_at.weekday() in (0, 3)
        assert send_at.hour == 9 and send_at.minute == 0
        assert send_at > datetime.now(et)

        # pause / resume
        sid = doc["id"]
        rp = requests.post(f"{API}/admin/members/push/scheduled/{sid}/pause", cookies=ADMIN, headers=WRITE_HDRS)
        assert rp.status_code == 200 and rp.json()["status"] == "paused"
        glist = requests.get(f"{API}/admin/members/push/scheduled", cookies=ADMIN).json()
        assert any(x["id"] == sid and x["status"] == "paused" for x in glist)
        rr = requests.post(f"{API}/admin/members/push/scheduled/{sid}/resume", cookies=ADMIN, headers=WRITE_HDRS)
        assert rr.status_code == 200 and rr.json()["status"] == "scheduled"
        # cleanup
        requests.delete(f"{API}/admin/members/push/scheduled/{sid}", cookies=ADMIN, headers=WRITE_HDRS)


# ---------------- 2. _next_run / _send_scheduled unit ----------------
class TestSendScheduledUnit:
    def test_next_run_and_send(self):
        import sys
        sys.path.insert(0, "/app/backend")
        import server
        importlib.reload  # noqa
        from motor.motor_asyncio import AsyncIOMotorClient

        async def _run():
            server.client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            server.db = server.client[os.environ["DB_NAME"]]
            # Daily
            d = server._next_run("2026-01-01T07:00", "daily", [], datetime.now(timezone.utc))
            assert d and d > datetime.now(timezone.utc)
            # Weekly only Tue(1)
            w = server._next_run("2026-01-06T08:00", "weekly", [1], datetime.now(timezone.utc))
            assert w.astimezone(server.EVENT_TZ).weekday() == 1
            # Monthly same day
            m = server._next_run("2026-01-15T10:00", "monthly", [], datetime.now(timezone.utc))
            assert m.astimezone(server.EVENT_TZ).day == 15

            # Insert past repeating doc and _send_scheduled -> advances
            sid = "qa-sched-" + str(int(datetime.now().timestamp()))
            past_utc = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            await server.db.push_scheduled.insert_one({
                "id": sid, "title": "QA rep past", "body": "x", "url": "/members",
                "send_at": past_utc, "send_at_local": "2026-01-06T08:00",
                "status": "scheduled", "repeat": "weekly", "days": [1], "end_date": ""
            })
            await server._send_scheduled()
            d2 = await server.db.push_scheduled.find_one({"id": sid}, {"_id": 0})
            assert d2["status"] == "scheduled"
            assert d2["sent_count"] == 1
            assert datetime.fromisoformat(d2["send_at"]) > datetime.now(timezone.utc)
            await server.db.push_scheduled.delete_one({"id": sid})

            # End-date passed -> status sent
            sid2 = sid + "-end"
            await server.db.push_scheduled.insert_one({
                "id": sid2, "title": "QA rep end", "body": "x", "url": "/members",
                "send_at": past_utc, "send_at_local": "2026-01-06T08:00",
                "status": "scheduled", "repeat": "daily", "days": [],
                "end_date": (datetime.now().date() - timedelta(days=1)).isoformat()
            })
            await server._send_scheduled()
            d3 = await server.db.push_scheduled.find_one({"id": sid2}, {"_id": 0})
            assert d3["status"] == "sent"
            await server.db.push_scheduled.delete_one({"id": sid2})

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()


# ---------------- 3. Weekly email ----------------
class TestWeeklyEmail:
    def test_email_weekly_returns_count(self):
        import sys
        sys.path.insert(0, "/app/backend")
        import server
        from motor.motor_asyncio import AsyncIOMotorClient

        async def _run():
            server.client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            server.db = server.client[os.environ["DB_NAME"]]
            n = await server._email_weekly()
            assert isinstance(n, int) and n >= 0
            return n

        loop = asyncio.new_event_loop()
        try:
            n = loop.run_until_complete(_run())
        finally:
            loop.close()
        # Should be >= 2 (A and B active + weekly_email true)
        assert n >= 2

    def test_send_now_returns_sent_emailed(self):
        r = requests.post(f"{API}/admin/members/weekly-summary/send", cookies=ADMIN, headers=WRITE_HDRS)
        if r.status_code == 429:
            pytest.skip("rate limited admin-weekly")
        assert r.status_code == 200, r.text
        j = r.json()
        assert "sent" in j and "emailed" in j

    def test_profile_weekly_email_persists(self):
        r = requests.put(f"{API}/members/profile", cookies=MEM_A, headers=WRITE_HDRS,
                         json={"weekly_email": False, "city": "Wilmington, DE"})
        assert r.status_code == 200
        u = db.users.find_one({"user_id": "qa_mem_a"})
        assert u["member_profile"].get("weekly_email") is False
        # restore
        requests.put(f"{API}/members/profile", cookies=MEM_A, headers=WRITE_HDRS,
                     json={"weekly_email": True, "city": "Wilmington, DE", "show_on_map": True, "phone": "302-555-0001"})


# ---------------- 4. Carpool ----------------
class TestCarpool:
    @pytest.fixture(scope="class")
    def meeting(self):
        future = (datetime.now().date() + timedelta(days=14)).isoformat()
        payload = {"title": "QA Carpool Meeting", "kind": "in-person", "date": future, "location": "Hall", "description": ""}
        r = requests.post(f"{API}/admin/members/meetings", cookies=ADMIN, headers=WRITE_HDRS, json=payload)
        assert r.status_code in (200, 201), r.text
        mid = r.json()["id"]
        yield mid
        requests.delete(f"{API}/admin/members/meetings/{mid}", cookies=ADMIN, headers=WRITE_HDRS)

    def test_rsvp_both_members(self, meeting):
        for cookie in (MEM_A, MEM_B):
            r = requests.post(f"{API}/members/gatherings/{meeting}/rsvp", cookies=cookie, headers=WRITE_HDRS,
                              json={"response": "yes", "guests": 0, "dietary": ""})
            assert r.status_code == 200, r.text

    def test_carpool_needs_rsvp_yes(self, meeting):
        # mem_c (no rsvp) -> expect 400
        db.users.insert_one({"user_id": "qa_mem_c", "email": "qa.sister.c@example.com", "name": "Cia QA", "role": "pending",
                             "member_status": "active", "member_profile": {"city": "Dover, DE", "phone": "302-555-0003"}})
        db.user_sessions.insert_one({"session_token": "mem_tok_c", "user_id": "qa_mem_c", "expires_at": "2099-01-01T00:00:00+00:00"})
        r = requests.put(f"{API}/members/gatherings/{meeting}/carpool", cookies={"session_token": "mem_tok_c"},
                         headers=WRITE_HDRS, json={"role": "need"})
        assert r.status_code == 400

    def test_bad_seats(self, meeting):
        for n in (0, 9):
            r = requests.put(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_B, headers=WRITE_HDRS,
                             json={"role": "drive", "seats": n})
            assert r.status_code == 400

    def test_auto_match_same_city(self, meeting):
        # A needs
        r = requests.put(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_A, headers=WRITE_HDRS,
                         json={"role": "need"})
        assert r.status_code == 200, r.text
        # B drives 2 seats -> should auto-match A
        r = requests.put(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_B, headers=WRITE_HDRS,
                         json={"role": "drive", "seats": 2})
        assert r.status_code == 200, r.text
        # View as A
        va = requests.get(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_A).json()
        assert va["me"]["role"] == "need"
        assert va["me"].get("driver"), f"expected driver, got {va}"
        assert va["me"]["driver"]["phone"] == "302-555-0002"
        # View as B
        vb = requests.get(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_B).json()
        assert vb["me"]["role"] == "drive"
        assert len(vb["me"]["riders"]) == 1
        assert vb["me"]["seats_left"] == 1
        # push_log carpool entries
        logs = list(db.push_log.find({"kind": "carpool"}).sort("sent_at", -1).limit(5))
        assert logs, "expected push_log entries kind=carpool"

    def test_third_rider_different_city_appears_waiting(self, meeting):
        # mem_c RSVP yes first
        r = requests.post(f"{API}/members/gatherings/{meeting}/rsvp", cookies={"session_token": "mem_tok_c"},
                          headers=WRITE_HDRS, json={"response": "yes"})
        assert r.status_code == 200
        r = requests.put(f"{API}/members/gatherings/{meeting}/carpool", cookies={"session_token": "mem_tok_c"},
                         headers=WRITE_HDRS, json={"role": "need"})
        assert r.status_code == 200
        vb = requests.get(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_B).json()
        waiting_ids = [w["user_id"] for w in vb.get("riders_waiting", [])]
        assert "qa_mem_c" in waiting_ids
        # Offer ride
        off = requests.post(f"{API}/members/gatherings/{meeting}/carpool/offer/qa_mem_c", cookies=MEM_B, headers=WRITE_HDRS)
        assert off.status_code == 200, off.text
        vb2 = requests.get(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_B).json()
        rider_ids = [r["user_id"] for r in vb2["me"]["riders"]]
        assert "qa_mem_c" in rider_ids

    def test_switching_to_none_releases_riders(self, meeting):
        r = requests.put(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_B, headers=WRITE_HDRS,
                         json={"role": "none"})
        assert r.status_code == 200
        va = requests.get(f"{API}/members/gatherings/{meeting}/carpool", cookies=MEM_A).json()
        assert va["me"]["role"] == "need"
        assert not va["me"].get("driver")

    def test_rsvp_no_removes_carpool(self, meeting):
        r = requests.post(f"{API}/members/gatherings/{meeting}/rsvp", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"response": "no"})
        assert r.status_code == 200
        cur = db.member_carpool.find_one({"meeting_id": meeting, "user_id": "qa_mem_a"})
        # Depending on impl, _carpool_release on RSVP change
        # Some impls release only when role changes; check behavior per spec
        # Spec: "A RSVP 'no' -> carpool entry removed"
        assert cur is None, f"expected removed, got {cur}"


# ---------------- 5. Map ----------------
class TestMap:
    def test_map_includes_optin_only(self):
        r = requests.get(f"{API}/members/map", cookies=MEM_A)
        assert r.status_code == 200, r.text
        d = r.json()
        # A opted in, B not. A appears, B not
        sister_ids = {s["user_id"] for c in d["cities"] for s in c["sisters"]}
        assert "qa_mem_a" in sister_ids
        assert "qa_mem_b" not in sister_ids
        for c in d["cities"]:
            assert "lat" in c and "lon" in c and "count" in c

    def test_non_member_403(self):
        # No cookie
        r = requests.get(f"{API}/members/map")
        assert r.status_code in (401, 403)


# ---------------- 6. Hours ----------------
class TestHours:
    def test_add_valid(self):
        today = datetime.now().date().isoformat()
        r = requests.post(f"{API}/members/hours", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"date": today, "hours": 5, "activity": "QA pantry"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "pending"

    def test_future_date_400(self):
        future = (datetime.now().date() + timedelta(days=5)).isoformat()
        r = requests.post(f"{API}/members/hours", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"date": future, "hours": 1, "activity": "QA"})
        assert r.status_code == 400

    def test_zero_hours_400(self):
        today = datetime.now().date().isoformat()
        r = requests.post(f"{API}/members/hours", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"date": today, "hours": 0, "activity": "QA"})
        assert r.status_code == 400

    def test_empty_activity_400(self):
        today = datetime.now().date().isoformat()
        r = requests.post(f"{API}/members/hours", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"date": today, "hours": 1, "activity": "   "})
        assert r.status_code == 400

    def test_get_hours_totals_only_approved(self):
        r = requests.get(f"{API}/members/hours", cookies=MEM_A)
        assert r.status_code == 200
        d = r.json()
        assert d["total"] == 0  # none approved yet
        assert d["pending"] >= 5
        assert [b["hours"] for b in d["badges"]] == [10, 25, 50, 100, 250]
        assert all(not b["earned"] for b in d["badges"])

    def test_delete_pending_ok_approved_not(self):
        today = datetime.now().date().isoformat()
        r = requests.post(f"{API}/members/hours", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"date": today, "hours": 1, "activity": "QA delete me"})
        hid = r.json()["id"]
        d = requests.delete(f"{API}/members/hours/{hid}", cookies=MEM_A, headers=WRITE_HDRS)
        assert d.status_code == 200
        # create and approve, then delete -> 404
        r = requests.post(f"{API}/members/hours", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"date": today, "hours": 2, "activity": "QA appr"})
        hid = r.json()["id"]
        requests.post(f"{API}/admin/volunteer-hours/{hid}/approve", cookies=ADMIN, headers=WRITE_HDRS)
        d = requests.delete(f"{API}/members/hours/{hid}", cookies=MEM_A, headers=WRITE_HDRS)
        assert d.status_code == 404

    def test_admin_leaderboard_and_approve_badge(self):
        r = requests.get(f"{API}/admin/members/hours", cookies=ADMIN)
        assert r.status_code == 200
        j = r.json()
        assert "leaderboard" in j and "pending" in j
        # approve the 5h entry to cross 10h threshold
        pending = [p for p in j["pending"] if p["email"] == "qa.sister.a@example.com" and p["hours"] >= 5]
        assert pending, "expected QA pending 5h entry"
        hid = pending[0]["id"]
        r = requests.post(f"{API}/admin/volunteer-hours/{hid}/approve", cookies=ADMIN, headers=WRITE_HDRS)
        assert r.status_code == 200
        # Give background task time
        import time
        time.sleep(2)
        # total should now be >=5+2=7, add another 5h and approve to cross 10
        today = datetime.now().date().isoformat()
        r = requests.post(f"{API}/members/hours", cookies=MEM_A, headers=WRITE_HDRS,
                          json={"date": today, "hours": 5, "activity": "QA extra"})
        hid2 = r.json()["id"]
        requests.post(f"{API}/admin/volunteer-hours/{hid2}/approve", cookies=ADMIN, headers=WRITE_HDRS)
        time.sleep(2)
        # push_log kind=hours
        logs = list(db.push_log.find({"kind": "hours", "body": {"$regex": "qa.sister.a|Ama"}}))
        # Just verify at least one hours log exists for mem_a
        logs_a = list(db.push_log.find({"kind": "hours"}).sort("sent_at", -1).limit(10))
        # The push targets user id, body contains name. Just assert hours badge was marked
        marks = list(db.push_marks.find({"key": {"$regex": "^hours-badge:qa_mem_a:10"}}))
        assert marks, "expected hours-badge:qa_mem_a:10 push_mark after crossing 10h"

    def test_csv(self):
        r = requests.get(f"{API}/admin/members/hours.csv", cookies=ADMIN)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert "Name,Email,Date,Hours" in r.text


# ---------------- 7. Best times ----------------
class TestBestTimes:
    def test_best_times_grid(self):
        # insert some push_taps
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        now_et = datetime.now(timezone.utc).astimezone(et)
        # pick wednesday 14:00 ET
        target_wkd, target_hr = 2, 14
        # Pick a date within last 90 days
        base = now_et.replace(hour=target_hr, minute=0, second=0, microsecond=0)
        delta = (base.weekday() - target_wkd) % 7
        base = base - timedelta(days=delta)
        if base > now_et:
            base = base - timedelta(days=7)
        iso = base.astimezone(timezone.utc).isoformat()
        for i in range(3):
            db.push_taps.insert_one({"log_id": f"qa-log-{i}", "user_id": "qa_mem_a", "at": iso})

        r = requests.get(f"{API}/admin/members/push/best-times", cookies=ADMIN)
        assert r.status_code == 200
        j = r.json()
        assert len(j["grid"]) == 7 and len(j["grid"][0]) == 24
        assert j["grid"][target_wkd][target_hr] >= 3
        assert j["total"] >= 3
        # cleanup
        db.push_taps.delete_many({"log_id": {"$regex": "^qa-log-"}})
