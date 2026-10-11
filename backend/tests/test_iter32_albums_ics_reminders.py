"""Iteration 32: Gallery albums, dated session ICS feeds, and dated session reminders."""
import io
import os
import re
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')  # frontend .env drives external URL

ADMIN_COOKIES = {"session_token": "qa_tok_123"}
XHR = {"X-Requested-With": "XMLHttpRequest"}
PROGRAM_SLUG = "business-elevation-lab"


# ----- helpers -----
def _program_id():
    r = requests.get(f"{BASE}/api/programs/{PROGRAM_SLUG}")
    r.raise_for_status()
    return r.json()["id"]


@pytest.fixture(scope="module")
def program_id():
    return _program_id()


@pytest.fixture(scope="module")
def uploaded_photos():
    """Upload 2 QA gallery photos tagged with event 'QA Album Night'."""
    ids = []
    for i in range(2):
        files = {"file": (f"qa_{i}.png", _tiny_png(), "image/png")}
        data = {"category": "gallery", "title": f"QA Photo {i}"}
        r = requests.post(f"{BASE}/api/media", files=files, data=data, cookies=ADMIN_COOKIES, headers=XHR)
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        # tag it
        r2 = requests.put(f"{BASE}/api/admin/gallery/{mid}",
                          json={"title": f"QA Photo {i}", "description": "", "tag_type": "event",
                                "tag_label": "QA Album Night", "tag_ref": "", "hidden": False, "album_key": ""},
                          cookies=ADMIN_COOKIES, headers=XHR)
        assert r2.status_code == 200, r2.text
        ids.append(mid)
    yield ids
    for mid in ids:
        requests.delete(f"{BASE}/api/admin/gallery/{mid}", cookies=ADMIN_COOKIES, headers=XHR)


def _tiny_png():
    # 1x1 transparent png
    import base64
    return io.BytesIO(base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="))


@pytest.fixture(scope="module")
def session_ids(program_id):
    """Create a timed session (18:30-20:00 ET on 2026-12-05) and an all-day session."""
    created = []
    r = requests.post(f"{BASE}/api/admin/programs/{program_id}/sessions",
                      json={"date": "2026-12-05", "start_time": "18:30", "end_time": "20:00",
                            "location": "QA Hall", "seats": 10, "notes": "QA note"},
                      cookies=ADMIN_COOKIES, headers=XHR)
    assert r.status_code == 200, r.text
    timed_id = r.json()["id"]
    created.append(timed_id)
    r2 = requests.post(f"{BASE}/api/admin/programs/{program_id}/sessions",
                       json={"date": "2026-12-20", "start_time": "", "end_time": "",
                             "location": "QA Hall", "seats": 10, "notes": ""},
                       cookies=ADMIN_COOKIES, headers=XHR)
    assert r2.status_code == 200, r2.text
    all_day_id = r2.json()["id"]
    created.append(all_day_id)
    yield {"timed": timed_id, "all_day": all_day_id}
    for sid in created:
        requests.delete(f"{BASE}/api/admin/sessions/{sid}", cookies=ADMIN_COOKIES, headers=XHR)


# ================= ICS =================
class TestICS:
    def test_dated_timed_session_ics_utc(self, session_ids):
        r = requests.get(f"{BASE}/api/sessions/s/{session_ids['timed']}/calendar.ics")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/calendar")
        body = r.text
        # ET -5h in Dec -> UTC
        assert "DTSTART:20261205T233000Z" in body, body
        assert "DTEND:20261206T010000Z" in body, body
        assert "LOCATION:QA Hall" in body
        assert f"UID:psession-{session_ids['timed']}@caringsistersclub" in body

    def test_dated_all_day_session_ics(self, session_ids):
        r = requests.get(f"{BASE}/api/sessions/s/{session_ids['all_day']}/calendar.ics")
        assert r.status_code == 200
        body = r.text
        assert "DTSTART;VALUE=DATE:20261220" in body
        assert "DTEND;VALUE=DATE:20261221" in body

    def test_main_feed_contains_psession_uid(self, session_ids):
        r = requests.get(f"{BASE}/api/sessions.ics")
        assert r.status_code == 200
        assert f"UID:psession-{session_ids['timed']}@caringsistersclub" in r.text

    def test_program_feed(self, session_ids):
        r = requests.get(f"{BASE}/api/sessions/{PROGRAM_SLUG}/calendar.ics")
        assert r.status_code == 200
        body = r.text
        assert f"UID:psession-{session_ids['timed']}@caringsistersclub" in body
        assert f"UID:psession-{session_ids['all_day']}@caringsistersclub" in body

    def test_calendar_entries_include_links(self, session_ids):
        r = requests.get(f"{BASE}/api/sessions/calendar")
        assert r.status_code == 200
        entries = r.json()["entries"]
        timed = next((e for e in entries if e.get("id") == session_ids["timed"]), None)
        assert timed is not None, "timed session not in calendar entries"
        assert timed["ics_url"] == f"/api/sessions/s/{session_ids['timed']}/calendar.ics"
        assert timed["program_feed"] == f"/api/sessions/{PROGRAM_SLUG}/calendar.ics"
        assert timed["gcal_url"].startswith("https://calendar.google.com/calendar/render")
        assert "20261205T233000Z" in timed["gcal_url"]


# ================= Albums =================
class TestAlbums:
    def test_public_albums_auto_from_tag(self, uploaded_photos):
        r = requests.get(f"{BASE}/api/gallery/albums")
        assert r.status_code == 200
        albums = r.json()["items"]
        a = next((x for x in albums if x["title"] == "QA Album Night"), None)
        assert a is not None, f"auto album not found; got {[x['title'] for x in albums]}"
        assert a["count"] == 2
        assert a["tag_type"] == "event"

    def test_public_album_detail(self, uploaded_photos):
        albums = requests.get(f"{BASE}/api/gallery/albums").json()["items"]
        a = next(x for x in albums if x["title"] == "QA Album Night")
        r = requests.get(f"{BASE}/api/gallery/albums/{a['slug']}")
        assert r.status_code == 200
        data = r.json()
        assert data["album"]["title"] == "QA Album Night"
        assert len(data["photos"]) == 2

    def test_update_auto_album_story_and_date(self, uploaded_photos):
        key = "t:event:qa album night"
        r = requests.put(f"{BASE}/api/admin/gallery-albums",
                         json={"key": key, "title": "QA Album Night", "story": "A beautiful QA night.",
                               "date": "2026-11-15", "cover_id": uploaded_photos[1]},
                         cookies=ADMIN_COOKIES, headers=XHR)
        assert r.status_code == 200, r.text
        a = next(x for x in requests.get(f"{BASE}/api/gallery/albums").json()["items"] if x["title"] == "QA Album Night")
        assert a["story"] == "A beautiful QA night."
        assert a["date"] == "2026-11-15"
        assert a["cover_id"] == uploaded_photos[1]

    def test_create_custom_album_and_assign_photo(self, uploaded_photos):
        r = requests.post(f"{BASE}/api/admin/gallery-albums",
                          json={"title": "QA Custom Album", "story": "custom", "date": "2026-10-01", "cover_id": ""},
                          cookies=ADMIN_COOKIES, headers=XHR)
        assert r.status_code == 200, r.text
        album = r.json()
        aid = album["id"]
        akey = album["key"]
        assert akey.startswith("m:")
        try:
            # Invalid album_key should 400
            bad = requests.put(f"{BASE}/api/admin/gallery/{uploaded_photos[0]}",
                               json={"title": "QA Photo 0", "description": "", "tag_type": "event",
                                     "tag_label": "QA Album Night", "tag_ref": "", "hidden": False,
                                     "album_key": "m:nonexistent"},
                               cookies=ADMIN_COOKIES, headers=XHR)
            assert bad.status_code == 400, bad.text

            # Assign one photo to custom album
            ok = requests.put(f"{BASE}/api/admin/gallery/{uploaded_photos[0]}",
                              json={"title": "QA Photo 0", "description": "", "tag_type": "event",
                                    "tag_label": "QA Album Night", "tag_ref": "", "hidden": False,
                                    "album_key": akey},
                              cookies=ADMIN_COOKIES, headers=XHR)
            assert ok.status_code == 200, ok.text

            albums = requests.get(f"{BASE}/api/gallery/albums").json()["items"]
            auto = next(x for x in albums if x["title"] == "QA Album Night")
            custom = next(x for x in albums if x["title"] == "QA Custom Album")
            assert auto["count"] == 1, f"photo not moved out of auto: {auto}"
            assert custom["count"] == 1, f"photo not in custom: {custom}"
        finally:
            # cleanup custom album & unassign
            requests.put(f"{BASE}/api/admin/gallery/{uploaded_photos[0]}",
                         json={"title": "QA Photo 0", "description": "", "tag_type": "event",
                               "tag_label": "QA Album Night", "tag_ref": "", "hidden": False, "album_key": ""},
                         cookies=ADMIN_COOKIES, headers=XHR)
            requests.delete(f"{BASE}/api/admin/gallery-albums/{aid}", cookies=ADMIN_COOKIES, headers=XHR)

    def test_delete_custom_album_unassigns(self, uploaded_photos):
        r = requests.post(f"{BASE}/api/admin/gallery-albums",
                          json={"title": "QA Delete Me", "story": "", "date": "", "cover_id": ""},
                          cookies=ADMIN_COOKIES, headers=XHR)
        album = r.json()
        requests.put(f"{BASE}/api/admin/gallery/{uploaded_photos[1]}",
                     json={"title": "QA Photo 1", "description": "", "tag_type": "event",
                           "tag_label": "QA Album Night", "tag_ref": "", "hidden": False,
                           "album_key": album["key"]},
                     cookies=ADMIN_COOKIES, headers=XHR)
        d = requests.delete(f"{BASE}/api/admin/gallery-albums/{album['id']}", cookies=ADMIN_COOKIES, headers=XHR)
        assert d.status_code == 200
        # Album gone from admin list
        admin_items = requests.get(f"{BASE}/api/admin/gallery-albums", cookies=ADMIN_COOKIES).json()["items"]
        assert not any(x.get("id") == album["id"] for x in admin_items)
        # Photo should be back in auto album
        albums = requests.get(f"{BASE}/api/gallery/albums").json()["items"]
        auto = next(x for x in albums if x["title"] == "QA Album Night")
        assert auto["count"] == 2

    def test_admin_albums_requires_auth(self):
        r = requests.get(f"{BASE}/api/admin/gallery-albums")
        assert r.status_code in (401, 403)


# ================= Reminders =================
class TestReminders:
    """Direct call to _send_dated_session_reminders with send_email monkeypatched."""

    def test_reminder_logic(self):
        """Run _send_dated_session_reminders inside the running backend by invoking it as a subprocess over asyncio."""
        import subprocess, textwrap
        code = textwrap.dedent(f"""
            import asyncio, sys
            sys.path.insert(0, '/app/backend')
            from datetime import datetime, timedelta, timezone
            import server
            sent = []
            async def fake_send_email(**kw):
                sent.append((kw.get('to'), kw.get('subject')))
            server.send_email = fake_send_email

            async def main():
                db = server.db
                # Clear previous reminder log for cleanliness
                await db.session_reminders.delete_many({{"program_id": {{"$exists": True}}}})
                # Create a program session for tomorrow (ET) and a 2h-away session
                p = await db.programs.find_one({{"slug": "{PROGRAM_SLUG}"}}, {{"_id":0}})
                EVENT_TZ = server.EVENT_TZ
                now_utc = datetime.now(timezone.utc)
                et = now_utc.astimezone(EVENT_TZ)
                tomorrow_et = (et.date() + timedelta(days=1)).isoformat()
                today_et = et.date().isoformat()
                # session tomorrow timed
                import uuid
                s1 = {{"id": "qa_rem_tomorrow", "program_id": p["id"], "date": tomorrow_et, "start_time": "10:00", "end_time":"11:00", "location":"QA Hall","notes":"","seats":10,"created_at": server._now_iso()}}
                await db.program_sessions.insert_one(dict(s1))
                # session today starting in ~90 min
                start_dt = (now_utc + timedelta(minutes=90)).astimezone(EVENT_TZ)
                s2 = {{"id": "qa_rem_2h", "program_id": p["id"], "date": start_dt.date().isoformat(), "start_time": start_dt.strftime("%H:%M"), "end_time":"", "location":"QA Hall","notes":"","seats":10,"created_at": server._now_iso()}}
                await db.program_sessions.insert_one(dict(s2))

                # confirmed submission for s1 (tomorrow)
                import secrets
                sub1 = {{"id":"qa_sub_1", "type":"program_signup", "program_id": p["id"], "session_id":"qa_rem_tomorrow", "waitlist": False, "data":{{"email":"qa.person1@example.com","name":"QA One"}}, "released": False, "created_at": server._now_iso()}}
                sub2 = {{"id":"qa_sub_2", "type":"program_signup", "program_id": p["id"], "session_id":"qa_rem_2h", "waitlist": False, "data":{{"email":"qa.person2@example.com","name":"QA Two"}}, "released": False, "created_at": server._now_iso()}}
                sub3 = {{"id":"qa_sub_3", "type":"program_signup", "program_id": p["id"], "session_id":"qa_rem_2h", "waitlist": True, "data":{{"email":"qa.person3@example.com","name":"QA Three"}}, "released": False, "created_at": server._now_iso()}}
                sub4 = {{"id":"qa_sub_4", "type":"program_signup", "program_id": p["id"], "session_id":"qa_rem_tomorrow", "waitlist": False, "data":{{"email":"qa.person4@example.com","name":"QA Four"}}, "released": True, "created_at": server._now_iso()}}
                for s in (sub1, sub2, sub3, sub4):
                    await db.submissions.insert_one(dict(s))

                # Force "now" to 10am ET so day-before fires
                now_10 = datetime.combine(et.date(), datetime.min.time().replace(hour=10)).replace(tzinfo=EVENT_TZ).astimezone(timezone.utc)
                sent1 = await server._send_dated_session_reminders(now_10)
                # Second call should be idempotent (same window), zero new emails
                sent2 = await server._send_dated_session_reminders(now_10)
                print("SENT1", sent1, "SENT2", sent2, "EMAILS", sent)

                # cleanup
                await db.program_sessions.delete_many({{"id": {{"$in": ["qa_rem_tomorrow","qa_rem_2h"]}}}})
                await db.submissions.delete_many({{"id": {{"$in": ["qa_sub_1","qa_sub_2","qa_sub_3","qa_sub_4"]}}}})
                await db.session_reminders.delete_many({{"submission_id": {{"$in":["qa_sub_1","qa_sub_2","qa_sub_3","qa_sub_4"]}}}})

            asyncio.run(main())
        """)
        r = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=60)
        print("STDOUT:", r.stdout)
        print("STDERR:", r.stderr[-800:])
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # Expect SENT1 == 2 (sub1 day-before + sub2 2h), SENT2 == 0 (idempotent)
        m1 = re.search(r"SENT1 (\d+)", out)
        m2 = re.search(r"SENT2 (\d+)", out)
        assert m1 and int(m1.group(1)) == 2, out
        assert m2 and int(m2.group(1)) == 0, out
        # waitlist/released must NOT be in emails
        assert "qa.person3@example.com" not in out
        assert "qa.person4@example.com" not in out
        assert "qa.person1@example.com" in out
        assert "qa.person2@example.com" in out
