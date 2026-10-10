"""Iter-20 backend tests: no-show follow-ups, review highlight, Faithful Sister badge, waitlist-speed report."""
import os
import re
import time
import uuid
import asyncio
import datetime as dt
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MDB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

QA_PID = f"qa20-{uuid.uuid4().hex[:8]}"
COOKIES = {"session_token": "qa_tok_123"}
H_WRITE = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}


def _now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _day(delta):
    return (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=delta)).isoformat()


def _mk_program(**kw):
    pid = kw.pop("id", f"{QA_PID}-{uuid.uuid4().hex[:6]}")
    slug = kw.pop("slug", f"{QA_PID}-{uuid.uuid4().hex[:6]}")
    doc = {
        "id": pid, "slug": slug, "title": kw.get("title", f"QA20 {slug}"),
        "summary": "QA", "description": "QA", "image_url": "",
        "category": "Caring", "published": True, "capacity": 10, "order": 999,
        "created_at": _now_iso(), "schedule": "Sat 10am", "start_date": kw.get("start_date", _day(-3)),
        "end_date": kw.get("end_date", _day(-3)), "cloned_from": kw.get("cloned_from"),
    }
    doc.update(kw)
    MDB.programs.insert_one(dict(doc))
    return doc


def _mk_sub(p, email, name="QA Sister", attendance=None, extra=None):
    sid = f"{QA_PID}-sub-{uuid.uuid4().hex[:8]}"
    doc = {"id": sid, "type": "program_signup", "program_id": p["id"], "waitlist": False,
           "stage": "new", "data": {"name": name, "email": email, "program": p["title"], "program_slug": p["slug"]},
           "created_at": _now_iso()}
    if attendance is not None:
        doc["attendance"] = attendance
    if extra:
        doc.update(extra)
    MDB.submissions.insert_one(dict(doc))
    return doc


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    MDB.programs.delete_many({"id": {"$regex": f"^{QA_PID}"}})
    MDB.submissions.delete_many({"id": {"$regex": f"^{QA_PID}"}})
    MDB.submissions.delete_many({"data.email": {"$regex": r"^qa\.(faith|iter20)"}})
    MDB.noshow_emails.delete_many({"submission_id": {"$regex": f"^{QA_PID}"}})
    MDB.session_feedback.delete_many({"id": {"$regex": f"^{QA_PID}"}})
    MDB.participant_badges.delete_many({"email": {"$regex": r"^qa\.(faith|iter20)"}})


# ---------- No-show follow-up ----------
class TestNoShowFollowup:
    def test_followup_endpoints(self):
        p = _mk_program(start_date=_day(-2), end_date=_day(-1))
        s1 = _mk_sub(p, "qa.iter20.ns1@example.com", "Alice One")
        s2 = _mk_sub(p, "qa.iter20.ns2@example.com", "Beth Two")

        # Mark s1 no_show via attendance endpoint
        r = requests.post(f"{BASE_URL}/api/admin/programs/{p['id']}/attendance",
                          json={"updates": {s1["id"]: "no_show"}}, cookies=COOKIES, headers=H_WRITE)
        assert r.status_code == 200, r.text
        assert r.json().get("updated") == 1

        # Status: 1 no-show, 0 emailed, 1 pending
        g = requests.get(f"{BASE_URL}/api/admin/programs/{p['id']}/noshow-followup", cookies=COOKIES).json()
        assert g == {"no_shows": 1, "emailed": 0, "pending": 1}, g

        # Trigger send (email to @example.com will fail, but noshow_emails doc should be upserted)
        s = requests.post(f"{BASE_URL}/api/admin/programs/{p['id']}/noshow-followup", cookies=COOKIES, headers=H_WRITE)
        assert s.status_code == 200, s.text
        # sent may be 0 (SMTP) but noshow_emails doc is created
        assert MDB.noshow_emails.find_one({"submission_id": s1["id"]}) is not None

        # Pending now 0
        g2 = requests.get(f"{BASE_URL}/api/admin/programs/{p['id']}/noshow-followup", cookies=COOKIES).json()
        assert g2["pending"] == 0 and g2["emailed"] == 1, g2

        # Idempotent: another POST sends 0 (same doc, upserted_id None)
        s2r = requests.post(f"{BASE_URL}/api/admin/programs/{p['id']}/noshow-followup", cookies=COOKIES, headers=H_WRITE)
        assert s2r.status_code == 200 and s2r.json()["sent"] == 0

    def test_daily_loop_only_once(self):
        # Verify POST-based idempotence through the admin endpoint (covers _noshow_for_program upsert guard).
        p = _mk_program(start_date=_day(-3), end_date=_day(-2))
        sub = _mk_sub(p, "qa.iter20.loop@example.com", "Loop Sister", attendance="no_show")
        r1 = requests.post(f"{BASE_URL}/api/admin/programs/{p['id']}/noshow-followup", cookies=COOKIES, headers=H_WRITE)
        r2 = requests.post(f"{BASE_URL}/api/admin/programs/{p['id']}/noshow-followup", cookies=COOKIES, headers=H_WRITE)
        assert r1.status_code == 200 and r2.status_code == 200
        # Second call must not create another email doc
        assert MDB.noshow_emails.count_documents({"submission_id": sub["id"]}) == 1


# ---------- Next session helper ----------
class TestNextSession:
    def test_next_session_resolution(self):
        # Verify via DB query matching _next_session logic. Create root + future clone + orphan.
        p = _mk_program(start_date=_day(-2), end_date=_day(-2))
        future = _mk_program(start_date=_day(14), end_date=_day(14), cloned_from=p["id"], published=True)
        orphan = _mk_program(start_date=_day(-5), end_date=_day(-5))
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        # For p: expected = future (same root/cloned_from family, published, start>today)
        nxt = MDB.programs.find_one(
            {"$or": [{"id": p["id"]}, {"cloned_from": p["id"]}], "published": True, "start_date": {"$gt": today}},
            {"_id": 0}, sort=[("start_date", 1)])
        assert nxt and nxt["id"] == future["id"]
        # For orphan: no future clone -> None
        root_o = orphan.get("cloned_from") or orphan["id"]
        nxt2 = MDB.programs.find_one(
            {"$or": [{"id": root_o}, {"cloned_from": root_o}], "published": True, "start_date": {"$gt": today}},
            {"_id": 0}, sort=[("start_date", 1)])
        assert nxt2 is None
        # End-to-end: POST noshow-followup on p (which has a no-show sub) succeeds
        s = _mk_sub(p, "qa.iter20.nxt@example.com", "Nxt Sister", attendance="no_show")
        r = requests.post(f"{BASE_URL}/api/admin/programs/{p['id']}/noshow-followup", cookies=COOKIES, headers=H_WRITE)
        assert r.status_code == 200
        assert MDB.noshow_emails.find_one({"submission_id": s["id"]}) is not None


# ---------- Review highlight ----------
class TestReviewHighlight:
    def test_highlight_and_hide_toggle(self):
        p = _mk_program(start_date=_day(-30), end_date=_day(-30))
        # Seed 3 session_feedback docs
        older_5 = {"id": f"{QA_PID}-fb-{uuid.uuid4().hex[:6]}", "program_id": p["id"], "name": "Nora Older",
                   "email": "n@x.com", "rating": 5, "comment": "Older five star good",
                   "submitted_at": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()}
        newer_5 = {"id": f"{QA_PID}-fb-{uuid.uuid4().hex[:6]}", "program_id": p["id"], "name": "Nancy Newer",
                   "email": "n2@x.com", "rating": 5, "comment": "Newer five star amazing",
                   "submitted_at": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=5)).isoformat()}
        three = {"id": f"{QA_PID}-fb-{uuid.uuid4().hex[:6]}", "program_id": p["id"], "name": "Tara Three",
                 "email": "n3@x.com", "rating": 3, "comment": "It was okay",
                 "submitted_at": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat()}
        MDB.session_feedback.insert_many([dict(older_5), dict(newer_5), dict(three)])

        g = requests.get(f"{BASE_URL}/api/programs/{p['slug']}").json()
        assert g.get("rating_count") == 3
        assert abs(g["rating_avg"] - round((5 + 5 + 3) / 3, 1)) < 0.01
        h = g.get("review_highlight")
        assert h and h["rating"] == 5 and "Newer" in h["quote"], h
        assert h["name"].startswith("Nancy"), h

        # Hide the newer 5 -> switch to older 5
        r = requests.post(f"{BASE_URL}/api/admin/feedback/{newer_5['id']}/hide-quote", cookies=COOKIES, headers=H_WRITE)
        assert r.status_code == 200 and r.json() == {"quote_hidden": True}
        g2 = requests.get(f"{BASE_URL}/api/programs/{p['slug']}").json()
        assert g2["review_highlight"]["quote"].startswith("Older"), g2["review_highlight"]

        # Toggle again -> false, back to newer
        r2 = requests.post(f"{BASE_URL}/api/admin/feedback/{newer_5['id']}/hide-quote", cookies=COOKIES, headers=H_WRITE)
        assert r2.json() == {"quote_hidden": False}

    def test_feedback_report_includes_quote_hidden(self):
        r = requests.get(f"{BASE_URL}/api/admin/reports/session-feedback", cookies=COOKIES)
        assert r.status_code == 200
        found = False
        for row in r.json().get("items", []):
            for c in row.get("comments") or []:
                if "quote_hidden" in c:
                    found = True; break
            if found:
                break
        assert found, "Expected quote_hidden field in session-feedback comments"


# ---------- Faithful Sister badge ----------
class TestFaithfulBadge:
    def _three_programs_with_subs(self, email, attendances):
        """Return (programs, submission ids)"""
        progs, subs = [], []
        for i, att in enumerate(attendances):
            p = _mk_program(start_date=_day(-20 + i * 3), end_date=_day(-20 + i * 3))
            progs.append(p)
            s = _mk_sub(p, email, "Faith Sister", attendance=att if att != "unmarked" else None)
            subs.append(s)
        return progs, subs

    def test_three_consecutive_attended_awards_badge(self):
        email = "qa.faith.ok@example.com"
        progs, subs = self._three_programs_with_subs(email, ["attended", "attended", "attended"])
        # Trigger streak check via attendance POST that marks them attended (reuse endpoint on third)
        # We already seeded attendance values. Trigger via re-posting attended on last.
        r = requests.post(f"{BASE_URL}/api/admin/programs/{progs[-1]['id']}/attendance",
                          json={"updates": {subs[-1]["id"]: "attended"}}, cookies=COOKIES, headers=H_WRITE)
        assert r.status_code == 200
        time.sleep(3)
        b = MDB.participant_badges.find_one({"email": email.lower(), "kind": "faithful"})
        assert b and b.get("seal") == "3x" and b.get("label") == "Faithful Sister", b
        tok = b["share_token"]

        g = requests.get(f"{BASE_URL}/api/badges/{tok}").json()
        assert g["label"] == "Faithful Sister" and g["seal"] == "3x" and g["kind"] == "participant", g

        # PNG endpoint
        png = requests.get(f"{BASE_URL}/api/share/badge/{tok}/card.png")
        assert png.status_code == 200 and png.headers.get("content-type", "").startswith("image/png")

        # Re-mark attended -> no second badge
        requests.post(f"{BASE_URL}/api/admin/programs/{progs[-1]['id']}/attendance",
                      json={"updates": {subs[-1]["id"]: "attended"}}, cookies=COOKIES, headers=H_WRITE)
        time.sleep(2)
        assert MDB.participant_badges.count_documents({"email": email.lower(), "kind": "faithful"}) == 1

    def test_broken_streak_no_badge(self):
        email = "qa.faith.bad@example.com"
        # attended, no_show, attended, attended -> never 3 consecutive
        progs, subs = self._three_programs_with_subs(email, ["attended", "no_show", "attended"])
        p4 = _mk_program(start_date=_day(-5), end_date=_day(-5))
        s4 = _mk_sub(p4, email, "Faith Bad", attendance="attended")
        r = requests.post(f"{BASE_URL}/api/admin/programs/{p4['id']}/attendance",
                          json={"updates": {s4["id"]: "attended"}}, cookies=COOKIES, headers=H_WRITE)
        assert r.status_code == 200
        time.sleep(3)
        assert MDB.participant_badges.find_one({"email": email.lower(), "kind": "faithful"}) is None


# ---------- Waitlist speed report ----------
class TestWaitlistSpeed:
    def test_waitlist_speed_summary(self):
        p = _mk_program(start_date=_day(5), end_date=_day(5), capacity=1)
        now = dt.datetime.now(dt.timezone.utc)
        sent = (now - dt.timedelta(hours=4)).isoformat()
        claimed_at = (now - dt.timedelta(hours=2)).isoformat()
        future_expiry = (now + dt.timedelta(hours=24)).isoformat()
        past_expiry = (now - dt.timedelta(hours=1)).isoformat()
        # claimed 2h later
        _mk_sub(p, "qa.iter20.ws1@example.com", "W One",
                extra={"waitlist": True, "offer_sent_at": sent, "offer_status": "claimed",
                       "claimed_at": claimed_at, "offer_expires": past_expiry})
        # expired
        _mk_sub(p, "qa.iter20.ws2@example.com", "W Two",
                extra={"waitlist": True, "offer_sent_at": sent, "offer_status": "expired",
                       "offer_expires": past_expiry})
        # open future expiry (pending)
        _mk_sub(p, "qa.iter20.ws3@example.com", "W Three",
                extra={"waitlist": True, "offer_sent_at": sent, "offer_status": "open",
                       "offer_expires": future_expiry})
        # moved_at only (auto_moved)
        _mk_sub(p, "qa.iter20.ws4@example.com", "W Four",
                extra={"waitlist": True, "moved_at": sent})

        r = requests.get(f"{BASE_URL}/api/admin/reports/waitlist-speed", cookies=COOKIES)
        assert r.status_code == 200, r.text
        data = r.json()
        # Find our program
        row = next((x for x in data["items"] if x["program_id"] == p["id"]), None)
        assert row, data
        assert row["offers"] == 3, row
        assert row["claimed"] == 1
        assert row["expired"] == 1
        assert row["pending"] == 1
        assert row["auto_moved"] == 1
        assert row["claim_rate"] == 50
        assert abs(row["median_hours"] - 2.0) < 0.2, row
