"""Iter 39 - Phone alerts: profile prefs, admin history, event/vote/birthday push flows."""
import os
import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
ADMIN_COOKIE = {"session_token": "qa_tok_123"}
MEM_A_COOKIE = {"session_token": "mem_tok_a"}
HDR = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}
DB = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
FAKE_EP = "https://fcm.googleapis.com/fcm/send/fakeABC_iter39"
FAKE_KEYS = {"p256dh": "BPSjJ8pZ7jmNNc0VxpQxcAJd4H4A4jVmLZEgA9Q7xXxGm2EH2E", "auth": "abcd1234efgh5678"}

# Promote mem_a to active member for push targeting
DB.users.update_one({"user_id": "qa_mem_a"},
                    {"$set": {"member_status": "active", "member_profile": {
                        "push_news": True, "push_prayer": True, "push_events": True,
                        "push_votes": True, "push_bday": True, "bday_notices": True, "bday_card": True}}})


def _cleanup():
    DB.member_announcements.delete_many({"title": {"$regex": "^ITER39"}})
    DB.member_prayers.delete_many({"text": {"$regex": "^ITER39"}})
    DB.member_ballots.delete_many({"title": {"$regex": "^ITER39"}})
    DB.member_meetings.delete_many({"title": {"$regex": "^ITER39"}})
    DB.program_sessions.delete_many({"id": {"$regex": "^iter39_"}})
    DB.programs.delete_many({"id": {"$regex": "^iter39_"}})
    DB.submissions.delete_many({"id": {"$regex": "^iter39_"}})
    DB.push_log.delete_many({"title": {"$regex": "ITER39|iter39|Tomorrow: ITER39"}})
    DB.push_marks.delete_many({"key": {"$regex": "iter39|ITER39"}})
    DB.push_subs.delete_many({"endpoint": {"$regex": "fakeABC_iter39"}})


@pytest.fixture(scope="module", autouse=True)
def _around():
    _cleanup()
    yield
    _cleanup()
    # Restore mem_a baseline (unset member_status/profile just set)
    DB.users.update_one({"user_id": "qa_mem_a"},
                        {"$unset": {"member_status": "", "member_profile": ""}})


# --- profile endpoint ---
def test_put_profile_accepts_push_prefs():
    body = {"city": "", "phone": "", "bio": "", "show_contact": False,
            "birthday_month": None, "birthday_day": None, "prayer_weekly": True,
            "bday_notices": True, "bday_card": True,
            "push_news": False, "push_prayer": True, "push_events": False,
            "push_votes": True, "push_bday": False}
    r = requests.put(f"{BASE}/api/members/profile", json=body, cookies=MEM_A_COOKIE, headers=HDR)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("push_news", "push_prayer", "push_events", "push_votes", "push_bday"):
        assert k in d, f"missing {k}"
    assert d["push_news"] is False
    assert d["push_events"] is False
    assert d["push_bday"] is False
    assert d["push_votes"] is True
    # restore all True so later targeting works
    body.update({"push_news": True, "push_prayer": True, "push_events": True,
                 "push_votes": True, "push_bday": True})
    requests.put(f"{BASE}/api/members/profile", json=body, cookies=MEM_A_COOKIE, headers=HDR)


# --- admin history ---
def test_history_requires_admin():
    r = requests.get(f"{BASE}/api/admin/members/push/history", cookies=MEM_A_COOKIE)
    assert r.status_code == 403


def test_history_lists_newest_first_and_filter():
    DB.push_log.insert_many([
        {"id": "iter39_old", "kind": "announcement", "title": "ITER39 old", "body": "x", "url": "/", "sent_at": "2026-01-01T00:00:00+00:00",
         "members": 1, "delivered": 0, "failed": 0, "expired": 0},
        {"id": "iter39_new", "kind": "vote", "title": "ITER39 new", "body": "x", "url": "/", "sent_at": "2026-01-02T00:00:00+00:00",
         "members": 1, "delivered": 0, "failed": 0, "expired": 0},
    ])
    r = requests.get(f"{BASE}/api/admin/members/push/history", cookies=ADMIN_COOKIE)
    assert r.status_code == 200
    rows = r.json()
    ids = [x["id"] for x in rows]
    assert "iter39_new" in ids and "iter39_old" in ids
    assert ids.index("iter39_new") < ids.index("iter39_old")
    # Required fields
    row = next(x for x in rows if x["id"] == "iter39_new")
    for k in ("id", "kind", "title", "body", "url", "sent_at", "members", "delivered", "failed", "expired"):
        assert k in row

    r = requests.get(f"{BASE}/api/admin/members/push/history?kind=vote", cookies=ADMIN_COOKIE)
    assert r.status_code == 200
    assert all(x["kind"] == "vote" for x in r.json())

    r = requests.get(f"{BASE}/api/admin/members/push/history?kind=bogus", cookies=ADMIN_COOKIE)
    assert r.status_code == 200
    kinds = {x["kind"] for x in r.json()}
    assert len(kinds) >= 2  # unknown returns all

    DB.push_log.delete_many({"id": {"$in": ["iter39_old", "iter39_new"]}})


# --- subscribe fake endpoint ---
def test_subscribe_fake_endpoint():
    r = requests.post(f"{BASE}/api/members/push/subscribe",
                      json={"endpoint": FAKE_EP, "keys": FAKE_KEYS},
                      cookies=MEM_A_COOKIE, headers=HDR)
    assert r.status_code == 200, r.text
    assert DB.push_subs.count_documents({"endpoint": FAKE_EP}) == 1


# --- announcement push_log ---
def test_announcement_creates_push_log_announcement():
    before = DB.push_log.count_documents({"kind": "announcement"})
    r = requests.post(f"{BASE}/api/admin/members/announcements",
                      json={"title": "ITER39 ann", "body": "Hello sisters"},
                      cookies=ADMIN_COOKIE, headers=HDR)
    assert r.status_code in (200, 201), r.text
    aid = r.json().get("id")
    # Wait for background task
    for _ in range(20):
        if DB.push_log.count_documents({"kind": "announcement", "title": {"$regex": "ITER39"}}):
            break
        time.sleep(0.5)
    rows = list(DB.push_log.find({"kind": "announcement", "title": {"$regex": "ITER39"}}))
    assert rows, "no announcement push_log row"
    row = rows[0]
    assert row["members"] >= 1
    # fake endpoint delivery is not possible — must be counted as failed or expired
    assert (row["expired"] + row["failed"]) >= 1, f"expected failed/expired >=1, got {row}"
    assert DB.push_log.count_documents({"kind": "announcement"}) > before
    # cleanup announcement
    if aid:
        requests.delete(f"{BASE}/api/admin/members/announcements/{aid}",
                        cookies=ADMIN_COOKIE, headers=HDR)


# --- prayer push_log ---
def test_prayer_creates_push_log_prayer():
    # Re-subscribe fake for next tests
    requests.post(f"{BASE}/api/members/push/subscribe",
                  json={"endpoint": FAKE_EP, "keys": FAKE_KEYS},
                  cookies=MEM_A_COOKIE, headers=HDR)
    # Post prayer from admin so mem_a is included as target (exclude_uid=author)
    r = requests.post(f"{BASE}/api/members/prayers",
                      json={"body": "ITER39 prayer please pray", "kind": "request", "anonymous": False},
                      cookies=ADMIN_COOKIE, headers=HDR)
    assert r.status_code in (200, 201), r.text
    pid = r.json().get("id")
    for _ in range(20):
        if DB.push_log.count_documents({"kind": "prayer"}):
            break
        time.sleep(0.5)
    assert DB.push_log.count_documents({"kind": "prayer"}) >= 1
    # cleanup prayer
    if pid:
        DB.member_prayers.delete_one({"id": pid})


# --- custom push ---
def test_custom_push_creates_log():
    r = requests.post(f"{BASE}/api/admin/members/push",
                      json={"title": "ITER39 custom", "body": "msg", "url": "/members"},
                      cookies=ADMIN_COOKIE, headers=HDR)
    assert r.status_code == 200, r.text
    rows = list(DB.push_log.find({"kind": "custom", "title": "ITER39 custom"}))
    assert rows, "no custom push_log"


# --- vote alerts ---
def test_vote_open_and_close_push_dedup():
    # Resubscribe fake for push_subs rows (so push_users targets a user)
    requests.post(f"{BASE}/api/members/push/subscribe",
                  json={"endpoint": FAKE_EP, "keys": FAKE_KEYS},
                  cookies=MEM_A_COOKIE, headers=HDR)
    now = datetime.now(timezone.utc)
    opens_at = (now - timedelta(seconds=5)).isoformat()
    closes_at = (now + timedelta(hours=20)).isoformat()
    r = requests.post(f"{BASE}/api/admin/members/ballots",
                      json={"kind": "resolution", "title": "ITER39 ballot",
                            "description": "do the thing", "opens_at": opens_at, "closes_at": closes_at},
                      cookies=ADMIN_COOKIE, headers=HDR)
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    # Wait for background _push_votes
    for _ in range(30):
        has_open = DB.push_marks.find_one({"key": f"vote-open:{bid}"})
        has_close = DB.push_marks.find_one({"key": f"vote-close:{bid}"})
        if has_open and has_close:
            break
        time.sleep(0.5)
    assert DB.push_marks.find_one({"key": f"vote-open:{bid}"}), "no vote-open mark"
    assert DB.push_marks.find_one({"key": f"vote-close:{bid}"}), "no vote-close mark"
    open_logs = list(DB.push_log.find({"kind": "vote", "title": "A member vote is open"}))
    close_logs = list(DB.push_log.find({"kind": "vote", "title": "Voting closes tomorrow"}))
    assert open_logs, "no open vote log"
    assert close_logs, "no close vote log"
    # Call push_votes again via direct trigger (simulate loop) — should not duplicate
    import sys
    sys.path.insert(0, '/app/backend')
    import server  # noqa
    before_open = DB.push_log.count_documents({"kind": "vote", "title": "A member vote is open"})
    before_close = DB.push_log.count_documents({"kind": "vote", "title": "Voting closes tomorrow"})
    asyncio.get_event_loop().run_until_complete(server._push_votes())
    assert DB.push_log.count_documents({"kind": "vote", "title": "A member vote is open"}) == before_open
    assert DB.push_log.count_documents({"kind": "vote", "title": "Voting closes tomorrow"}) == before_close
    # cleanup
    requests.delete(f"{BASE}/api/admin/members/ballots/{bid}", cookies=ADMIN_COOKIE, headers=HDR)


def test_vote_future_opens_at_no_open_alert():
    now = datetime.now(timezone.utc)
    opens_at = (now + timedelta(days=2)).isoformat()
    closes_at = (now + timedelta(days=3)).isoformat()
    r = requests.post(f"{BASE}/api/admin/members/ballots",
                      json={"kind": "resolution", "title": "ITER39 future",
                            "description": "later", "opens_at": opens_at, "closes_at": closes_at},
                      cookies=ADMIN_COOKIE, headers=HDR)
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    time.sleep(2)
    assert DB.push_marks.find_one({"key": f"vote-open:{bid}"}) is None
    requests.delete(f"{BASE}/api/admin/members/ballots/{bid}", cookies=ADMIN_COOKIE, headers=HDR)


# --- events direct call ---
def test_push_events_meeting_tomorrow():
    import sys, uuid
    sys.path.insert(0, '/app/backend')
    import server
    requests.post(f"{BASE}/api/members/push/subscribe",
                  json={"endpoint": FAKE_EP, "keys": FAKE_KEYS},
                  cookies=MEM_A_COOKIE, headers=HDR)
    et_now = datetime.now(server.EVENT_TZ).replace(hour=10, minute=0, second=0, microsecond=0)
    tomorrow = (et_now.date() + timedelta(days=1)).isoformat()
    meeting_id = f"iter39_mtg_{uuid.uuid4().hex[:8]}"
    DB.member_meetings.insert_one({"id": meeting_id, "title": "ITER39 meeting", "date": tomorrow,
                                   "location": "Hall", "rsvps": {"qa_mem_a": {"response": "yes"}}})
    asyncio.get_event_loop().run_until_complete(server._push_events(now=et_now.astimezone(timezone.utc)))
    assert DB.push_marks.find_one({"key": f"event:{meeting_id}:{tomorrow}"}) is not None
    assert DB.push_log.count_documents({"kind": "event", "title": "Tomorrow: ITER39 meeting"}) == 1

    # second call: no duplicate
    asyncio.get_event_loop().run_until_complete(server._push_events(now=et_now.astimezone(timezone.utc)))
    assert DB.push_log.count_documents({"kind": "event", "title": "Tomorrow: ITER39 meeting"}) == 1

    # Opt-out push_events -> target excluded
    DB.push_marks.delete_one({"key": f"event:{meeting_id}:{tomorrow}"})
    DB.push_log.delete_many({"kind": "event", "title": "Tomorrow: ITER39 meeting"})
    DB.users.update_one({"user_id": "qa_mem_a"}, {"$set": {"member_profile.push_events": False}})
    asyncio.get_event_loop().run_until_complete(server._push_events(now=et_now.astimezone(timezone.utc)))
    rows = list(DB.push_log.find({"kind": "event", "title": "Tomorrow: ITER39 meeting"}))
    assert rows and rows[0]["members"] == 0, f"opt-out failed: {rows}"
    # restore
    DB.users.update_one({"user_id": "qa_mem_a"}, {"$set": {"member_profile.push_events": True}})


# --- birthday direct call ---
def test_push_birthdays_and_opt_outs():
    import sys
    sys.path.insert(0, '/app/backend')
    import server
    requests.post(f"{BASE}/api/members/push/subscribe",
                  json={"endpoint": FAKE_EP, "keys": FAKE_KEYS},
                  cookies=MEM_A_COOKIE, headers=HDR)
    et_now = datetime.now(server.EVENT_TZ).replace(hour=9, minute=0, second=0, microsecond=0)
    today = et_now.date()
    # Set mem_a birthday to today
    DB.users.update_one({"user_id": "qa_mem_a"},
                        {"$set": {"member_profile.birthday_month": today.month,
                                  "member_profile.birthday_day": today.day,
                                  "member_profile.bday_notices": True,
                                  "member_profile.bday_card": True}})
    DB.push_marks.delete_one({"key": f"bday:qa_mem_a:{today.year}"})

    asyncio.get_event_loop().run_until_complete(server._push_birthdays(now=et_now.astimezone(timezone.utc)))
    rows = list(DB.push_log.find({"kind": "birthday", "sent_at": {"$gte": "2026-01-01"}}).sort("sent_at", -1).limit(5))
    # There should be at least one birthday log: the self 'Happy birthday' card (others may be 0 members)
    self_log = DB.push_log.find_one({"kind": "birthday", "title": {"$regex": "^Happy birthday"}})
    assert self_log is not None, f"no self bday log: {rows}"

    # Second call: dedupe
    before = DB.push_log.count_documents({"kind": "birthday"})
    asyncio.get_event_loop().run_until_complete(server._push_birthdays(now=et_now.astimezone(timezone.utc)))
    assert DB.push_log.count_documents({"kind": "birthday"}) == before

    # bday_card=False -> self push skipped
    DB.push_marks.delete_one({"key": f"bday:qa_mem_a:{today.year}"})
    DB.push_log.delete_many({"kind": "birthday"})
    DB.users.update_one({"user_id": "qa_mem_a"}, {"$set": {"member_profile.bday_card": False}})
    asyncio.get_event_loop().run_until_complete(server._push_birthdays(now=et_now.astimezone(timezone.utc)))
    assert DB.push_log.find_one({"kind": "birthday", "title": {"$regex": "^Happy birthday"}}) is None

    # cleanup birthday fields
    DB.users.update_one({"user_id": "qa_mem_a"},
                        {"$unset": {"member_profile.birthday_month": "", "member_profile.birthday_day": ""}})
