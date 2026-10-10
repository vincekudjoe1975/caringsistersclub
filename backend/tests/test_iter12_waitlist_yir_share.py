"""Iteration 12 tests: waitlist spot-alert modes (claim/auto/broadcast),
delete-triggered seat fill, leaderboard badge, YIR share card/share-page/email."""
import os
import re
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
COOKIE = {"session_token": "qa_tok_123"}
H = {"X-Requested-With": "XMLHttpRequest"}

mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

PROG_SLUG = "wellness-workshops"
PROG = mdb.programs.find_one({"slug": PROG_SLUG})
assert PROG, "wellness-workshops program not seeded"
PROG_ID = PROG["id"]
ORIG_CAP = PROG.get("capacity", 0)
ORIG_MODE = PROG.get("waitlist_mode", "claim")


def _program_payload(**over):
    base = {
        "title": PROG["title"], "category": PROG.get("category", ""), "image_url": PROG.get("image_url", ""),
        "summary": PROG.get("summary", ""), "body": PROG.get("body", ""),
        "goals": PROG.get("goals", []), "impact": PROG.get("impact", []),
        "cta_text": PROG.get("cta_text", "Get Involved"), "cta_link": PROG.get("cta_link", "/volunteer"),
        "published": True, "capacity": 0, "waitlist_mode": "claim",
        "gallery": PROG.get("gallery", []), "testimonials": PROG.get("testimonials", []),
        "home_testimonial_ids": PROG.get("home_testimonial_ids", []),
    }
    base.update(over)
    return base


def _put_program(**over):
    r = requests.put(f"{API}/admin/programs/{PROG_ID}", json=_program_payload(**over), cookies=COOKIE, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def _insert_signup(waitlist=False, stage=None, created_at=None):
    em = f"test_wl_{uuid.uuid4().hex[:8]}@example.com"
    doc = {
        "id": str(uuid.uuid4()), "type": "program_signup", "program_id": PROG_ID,
        "waitlist": bool(waitlist),
        "data": {"program": PROG["title"], "program_slug": PROG_SLUG, "name": "QA WL", "email": em, "phone": "", "message": ""},
        "read": False, "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }
    if waitlist:
        doc["data"]["list"] = "Waitlist"
    if stage:
        doc["stage"] = stage
    mdb.submissions.insert_one(doc)
    return doc["id"], em


def _clear_qa_signups():
    mdb.submissions.delete_many({"program_id": PROG_ID, "data.email": {"$regex": "example.com$"}})


def _wait_offer(sid, timeout=10):
    for _ in range(timeout * 2):
        s = mdb.submissions.find_one({"id": sid})
        if s and s.get("offer_status") == "open" and s.get("offer_token"):
            return s
        time.sleep(0.5)
    return mdb.submissions.find_one({"id": sid})


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    # Cleanup QA submissions
    _clear_qa_signups()
    mdb.volunteer_hours.delete_many({"email": {"$regex": "example.com$"}})
    mdb.volunteer_milestones.delete_many({"email": {"$regex": "example.com$"}})
    mdb.volunteer_thanks.delete_many({"email": {"$regex": "example.com$"}})
    mdb.yir_emails.delete_many({})
    # Reset program capacity/mode
    try:
        _put_program(capacity=ORIG_CAP, waitlist_mode="claim")
    except Exception:
        pass
    # Reset yir settings
    mdb.settings.update_one({"key": "site"}, {"$set": {"yir_public": [], "yir_autosend": False, "yir_images.2026": ""}}, upsert=True)


# ========== CLAIM MODE ==========
class TestClaimMode:
    def test_claim_mode_full_flow(self):
        _clear_qa_signups()
        _put_program(capacity=1, waitlist_mode="claim")

        # A takes seat
        idA, emA = _insert_signup()
        # B, C on waitlist (older first)
        now = datetime.now(timezone.utc)
        idB, emB = _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=2)).isoformat())
        idC, emC = _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=1)).isoformat())

        # Mark A not_fit -> frees seat -> B should get offer
        r = requests.put(f"{API}/admin/submissions/{idA}/stage", json={"stage": "not_fit"}, cookies=COOKIE, headers=H)
        assert r.status_code == 200

        sB = _wait_offer(idB)
        assert sB and sB.get("offer_status") == "open", f"B offer_status={sB.get('offer_status') if sB else None}"
        assert sB.get("offer_token")
        # offer_expires ~48h
        exp = datetime.fromisoformat(sB["offer_expires"])
        delta_h = (exp - datetime.now(timezone.utc)).total_seconds() / 3600
        assert 47 < delta_h <= 48.5, f"delta_h={delta_h}"

        # C should NOT have an offer
        sC = mdb.submissions.find_one({"id": idC})
        assert sC.get("offer_status") != "open", f"C offer_status={sC.get('offer_status')}"

        tok = sB["offer_token"]
        # GET /waitlist/offer?token= -> open
        r = requests.get(f"{API}/waitlist/offer", params={"token": tok})
        assert r.status_code == 200 and r.json()["status"] == "open"

        # POST claim -> claimed, waitlist false
        r = requests.post(f"{API}/waitlist/claim", json={"token": tok})
        assert r.status_code == 200 and r.json()["status"] == "claimed"
        sB2 = mdb.submissions.find_one({"id": idB})
        assert sB2["waitlist"] is False and sB2["offer_status"] == "claimed"

        # Claim again -> still returns 'claimed' (idempotent)
        r = requests.post(f"{API}/waitlist/claim", json={"token": tok})
        assert r.status_code == 200 and r.json()["status"] == "claimed"

        # Program full now
        p = requests.get(f"{API}/programs/{PROG_SLUG}").json()
        assert p["seats_left"] == 0 and p["full"] is True

    def test_claim_expiry_promotes_next(self):
        _clear_qa_signups()
        _put_program(capacity=1, waitlist_mode="claim")

        # Seat holder
        idA, _ = _insert_signup()
        # Two waitlisted
        now = datetime.now(timezone.utc)
        idB, _ = _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=5)).isoformat())
        idC, _ = _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=3)).isoformat())

        # Free a seat → B gets open offer
        r = requests.put(f"{API}/admin/submissions/{idA}/stage", json={"stage": "not_fit"}, cookies=COOKIE, headers=H)
        assert r.status_code == 200
        sB = _wait_offer(idB)
        assert sB and sB["offer_status"] == "open"
        tokB = sB["offer_token"]

        # Expire B directly in Mongo
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mdb.submissions.update_one({"id": idB}, {"$set": {"offer_expires": past}})

        # Trigger _fill_seats via another PUT program (keep same capacity/mode)
        _put_program(capacity=1, waitlist_mode="claim")

        # Wait + assert: B expired, C gets open
        sC = None
        for _ in range(20):
            time.sleep(0.5)
            sB2 = mdb.submissions.find_one({"id": idB})
            sC = mdb.submissions.find_one({"id": idC})
            if sB2.get("offer_status") == "expired" and sC.get("offer_status") == "open":
                break
        assert sB2.get("offer_status") == "expired", f"B status={sB2.get('offer_status')}"
        assert sC and sC.get("offer_status") == "open", f"C status={sC.get('offer_status') if sC else None}"

        # GET expired offer -> 'expired'
        r = requests.get(f"{API}/waitlist/offer", params={"token": tokB})
        assert r.status_code == 200 and r.json()["status"] == "expired", r.text
        # POST claim expired -> 410
        r = requests.post(f"{API}/waitlist/claim", json={"token": tokB})
        assert r.status_code == 410, r.text


# ========== AUTO MODE ==========
class TestAutoMode:
    def test_auto_mode_promotes_oldest(self):
        _clear_qa_signups()
        _put_program(capacity=1, waitlist_mode="auto")

        idA, _ = _insert_signup()
        now = datetime.now(timezone.utc)
        idB, _ = _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=5)).isoformat())
        _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=2)).isoformat())

        # Free seat
        r = requests.put(f"{API}/admin/submissions/{idA}/stage", json={"stage": "not_fit"}, cookies=COOKIE, headers=H)
        assert r.status_code == 200

        # Wait for B to be moved in
        sB = None
        for _ in range(20):
            time.sleep(0.5)
            sB = mdb.submissions.find_one({"id": idB})
            if sB and sB.get("waitlist") is False:
                break
        assert sB.get("waitlist") is False
        assert sB["data"].get("list") == "Moved in from waitlist"


# ========== BROADCAST MODE ==========
class TestBroadcastMode:
    def test_broadcast_capacity_raise_offers_all(self):
        _clear_qa_signups()
        _put_program(capacity=1, waitlist_mode="broadcast")

        _insert_signup()  # seat holder
        now = datetime.now(timezone.utc)
        idB, _ = _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=5)).isoformat())
        idC, _ = _insert_signup(waitlist=True, created_at=(now - timedelta(minutes=2)).isoformat())

        # Raise capacity by 1 (free seat appears)
        _put_program(capacity=2, waitlist_mode="broadcast")

        # Wait both to be offered
        tokB = tokC = None
        for _ in range(20):
            time.sleep(0.5)
            sB = mdb.submissions.find_one({"id": idB})
            sC = mdb.submissions.find_one({"id": idC})
            if sB.get("offer_status") == "open" and sC.get("offer_status") == "open":
                tokB, tokC = sB["offer_token"], sC["offer_token"]
                break
        assert tokB and tokC, "Expected both waitlisters to receive open offers in broadcast mode"

        # First claim wins
        r = requests.post(f"{API}/waitlist/claim", json={"token": tokB})
        assert r.status_code == 200 and r.json()["status"] == "claimed"

        # Second claim -> 409 (full)
        r = requests.post(f"{API}/waitlist/claim", json={"token": tokC})
        assert r.status_code == 409, r.text


# ========== DELETE submission triggers seat fill ==========
class TestDeleteTriggersFill:
    def test_delete_seated_signup_fills_from_waitlist(self):
        _clear_qa_signups()
        _put_program(capacity=1, waitlist_mode="claim")

        idA, _ = _insert_signup()
        idB, _ = _insert_signup(waitlist=True)

        r = requests.delete(f"{API}/submissions/{idA}", cookies=COOKIE, headers=H)
        assert r.status_code == 200

        sB = _wait_offer(idB)
        assert sB and sB.get("offer_status") == "open"


# ========== INVALID TOKEN ==========
class TestOfferErrors:
    def test_invalid_token(self):
        r = requests.get(f"{API}/waitlist/offer", params={"token": "nope-" + uuid.uuid4().hex})
        assert r.status_code == 404


# ========== LEADERBOARD BADGE ==========
class TestLeaderboardBadge:
    def test_leaderboard_includes_highest_badge(self):
        em = f"test_lb_{uuid.uuid4().hex[:6]}@example.com"
        year = datetime.now(timezone.utc).strftime("%Y")
        today = datetime.now(timezone.utc).date().isoformat()
        # Seed approved+leaderboard
        mdb.volunteer_hours.insert_one({
            "id": str(uuid.uuid4()), "email": em, "name": "QA Leader Example", "hours": 12,
            "program": "QA", "note": "", "date": today, "leaderboard": True, "status": "approved",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        mdb.volunteer_milestones.insert_one({
            "id": str(uuid.uuid4()), "email": em, "scope": "all", "threshold": 50,
            "awarded_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.get(f"{API}/volunteer-hours/leaderboard")
        assert r.status_code == 200
        items = r.json()["items"]
        # name is short-formed (e.g. "QA E.") so match on badge presence from fresh seed
        hit = [i for i in items if i.get("badge") == 50]
        assert hit, f"50-badge not in leaderboard: {items}"


# ========== YIR SHARE CARD + SHARE PAGE ==========
class TestYirSharePageAndCard:
    def test_card_404_anonymous_unpublished_then_admin_ok(self):
        mdb.settings.update_one({"key": "site"}, {"$pull": {"yir_public": 2026}})
        r = requests.get(f"{API}/share/year-in-review/2026/card.png")
        assert r.status_code == 404

        r = requests.get(f"{API}/share/year-in-review/2026/card.png", cookies=COOKIE, headers=H)
        assert r.status_code == 200
        assert r.headers.get("content-type") == "image/png"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_share_page_404_until_publish_then_meta_tags(self):
        mdb.settings.update_one({"key": "site"}, {"$pull": {"yir_public": 2026}})
        assert requests.get(f"{API}/share/year-in-review/2026").status_code == 404

        # Publish
        r = requests.put(f"{API}/admin/year-in-review/2026", json={"public": True}, cookies=COOKIE, headers=H)
        assert r.status_code == 200
        # Anonymous card now 200
        r = requests.get(f"{API}/share/year-in-review/2026/card.png")
        assert r.status_code == 200 and r.headers.get("content-type") == "image/png"
        # Share page
        r = requests.get(f"{API}/share/year-in-review/2026")
        assert r.status_code == 200
        html = r.text
        assert 'property="og:image"' in html
        assert 'property="og:title"' in html
        assert 'name="twitter:card" content="summary_large_image"' in html
        assert 'http-equiv="refresh"' in html and "/year-in-review/2026" in html

    def test_custom_image_url_and_reset(self):
        # Publish first (idempotent)
        requests.put(f"{API}/admin/year-in-review/2026", json={"public": True}, cookies=COOKIE, headers=H)
        # Invalid image_url -> 400
        r = requests.put(f"{API}/admin/year-in-review/2026",
                         json={"image_url": "https://evil.example/img.png"}, cookies=COOKIE, headers=H)
        assert r.status_code == 400

        # Simulate uploaded media id (valid shape)
        media_id = str(uuid.uuid4())
        valid_url = f"/api/media/file/{media_id}"
        r = requests.put(f"{API}/admin/year-in-review/2026",
                         json={"image_url": valid_url}, cookies=COOKIE, headers=H)
        assert r.status_code == 200, r.text

        # og:image reflects custom url
        r = requests.get(f"{API}/share/year-in-review/2026")
        assert r.status_code == 200
        m = re.search(r'property="og:image" content="([^"]+)"', r.text)
        assert m and valid_url in m.group(1), f"og:image={m.group(1) if m else None}"

        # Reset by sending empty string
        r = requests.put(f"{API}/admin/year-in-review/2026",
                         json={"image_url": ""}, cookies=COOKIE, headers=H)
        assert r.status_code == 200
        site = mdb.settings.find_one({"key": "site"})
        assert (site.get("yir_images") or {}).get("2026") == ""

    def test_unpublish_restores_404(self):
        r = requests.put(f"{API}/admin/year-in-review/2026", json={"public": False}, cookies=COOKIE, headers=H)
        assert r.status_code == 200
        assert requests.get(f"{API}/share/year-in-review/2026").status_code == 404
        assert requests.get(f"{API}/share/year-in-review/2026/card.png").status_code == 404


# ========== YIR EMAIL ==========
class TestYirEmail:
    def test_email_preview_shape(self):
        r = requests.get(f"{API}/admin/year-in-review/2026/email", cookies=COOKIE, headers=H)
        assert r.status_code == 200
        d = r.json()
        for k in ("html", "recipients", "history"):
            assert k in d
        assert isinstance(d["html"], str) and "Year in Review" in d["html"]
        assert isinstance(d["recipients"], int)
        assert isinstance(d["history"], list)

    def test_email_test_bad_address(self):
        r = requests.post(f"{API}/admin/year-in-review/2026/email/test",
                          json={"email": "bad"}, cookies=COOKIE, headers=H)
        assert r.status_code == 400

    def test_send_unpublished_returns_400(self):
        # Ensure unpublished
        mdb.settings.update_one({"key": "site"}, {"$pull": {"yir_public": 2026}})
        r = requests.post(f"{API}/admin/year-in-review/2026/email/send",
                          json={"force": False}, cookies=COOKIE, headers=H)
        assert r.status_code == 400, r.text

    def test_autosend_flag_persists_then_resets(self):
        # Keep unpublished during this test — do NOT trigger a real send
        mdb.settings.update_one({"key": "site"}, {"$pull": {"yir_public": 2026}})

        r = requests.put(f"{API}/admin/year-in-review/2026",
                         json={"autosend": True}, cookies=COOKIE, headers=H)
        assert r.status_code == 200 and r.json()["autosend"] is True

        # Confirm persisted via admin GET
        g = requests.get(f"{API}/admin/year-in-review/2026", cookies=COOKIE, headers=H).json()
        assert g["autosend"] is True
        assert g["public"] is False

        # Reset BEFORE any publish to avoid sending to real donors
        r = requests.put(f"{API}/admin/year-in-review/2026",
                         json={"autosend": False}, cookies=COOKIE, headers=H)
        assert r.status_code == 200 and r.json()["autosend"] is False
