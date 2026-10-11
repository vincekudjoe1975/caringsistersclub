"""Iteration 33 backend tests:
- Dated-session check-in roster + attendance (auth/CSRF/per-row/mark-rest)
- Leader personal quote: PUT accepts quote, caps at 240, strips surrounding quotes
- Album slug + home latest album surface
- Public pages regression: every public route returns 200 and non-empty HTML (via API where applicable)
"""
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE}/api"
ADMIN_COOKIE = {"session_token": "qa_tok_123"}
ADMIN_HEADERS = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}

_m = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


# ---------- shared QA data ----------
@pytest.fixture(scope="module")
def qa_data():
    prog = _m.programs.find_one({"slug": "business-elevation-lab"}, {"_id": 0, "id": 1})
    assert prog, "need business-elevation-lab program seeded"
    pid = prog["id"]
    # session
    sid = str(uuid.uuid4())
    _m.program_sessions.insert_one({
        "id": sid, "program_id": pid, "date": "2099-01-10", "start_time": "18:00", "end_time": "19:30",
        "location": "QA Hall", "seats": 0, "notes": "", "created_at": "2026-01-01T00:00:00+00:00",
    })
    # 3 submissions (signups) for session
    sub_ids = []
    for i, nm in enumerate(["QA Person One", "QA Person Two", "QA Person Three"]):
        subid = str(uuid.uuid4())
        _m.submissions.insert_one({
            "id": subid, "type": "program_signup", "program_id": pid, "session_id": sid,
            "data": {"name": nm, "email": f"qa.person{i}@example.com", "phone": ""},
            "created_at": "2026-01-01T00:00:00+00:00", "stage": "new",
        })
        sub_ids.append(subid)
    # leader
    lid = str(uuid.uuid4())
    _m.leaders.insert_one({
        "id": lid, "name": "QA Quote Leader", "role": "QA", "group": "board",
        "intro": "", "bio": "", "photo_url": "", "email": "", "linkedin": "",
        "quote": "", "visible": True, "order": 9999, "created_at": "2026-01-01T00:00:00+00:00",
    })
    # gallery photo (for album)
    mid = str(uuid.uuid4())
    _m.media.insert_one({
        "id": mid, "category": "gallery", "title": "QA photo", "description": "",
        "tag_type": "event", "tag_label": "QA Album Night", "tag_ref": "",
        "hidden": False, "is_deleted": False, "uploaded_at": "2026-01-01T00:00:00+00:00",
        "order": 1, "storage": "fs", "filename": "qa.jpg", "mime": "image/jpeg",
        "size": 10, "width": 100, "height": 100,
    })
    yield {"pid": pid, "sid": sid, "sub_ids": sub_ids, "lid": lid, "mid": mid}
    # cleanup
    _m.program_sessions.delete_one({"id": sid})
    _m.submissions.delete_many({"id": {"$in": sub_ids}})
    _m.leaders.delete_one({"id": lid})
    _m.media.delete_one({"id": mid})
    _m.gallery_albums.delete_many({"key": {"$regex": "QA Album Night", "$options": "i"}})


# ---------- session check-in ----------
class TestSessionCheckin:
    def test_roster_requires_admin(self, qa_data):
        r = requests.get(f"{API}/admin/sessions/{qa_data['sid']}/roster")
        assert r.status_code in (401, 403)

    def test_roster_lists_signups(self, qa_data):
        r = requests.get(f"{API}/admin/sessions/{qa_data['sid']}/roster", cookies=ADMIN_COOKIE)
        assert r.status_code == 200
        d = r.json()
        assert d["program"] == "Business Elevation Lab"
        assert len(d["items"]) == 3
        assert all(i["attendance"] is None for i in d["items"])
        assert {i["name"] for i in d["items"]} == {"QA Person One", "QA Person Two", "QA Person Three"}

    def test_attendance_per_row_toggle(self, qa_data):
        sid = qa_data["sid"]; subid = qa_data["sub_ids"][0]
        # mark attended
        r = requests.post(f"{API}/admin/sessions/{sid}/attendance",
                          json={"updates": {subid: "attended"}}, cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r.status_code == 200 and r.json()["updated"] == 1
        g = requests.get(f"{API}/admin/sessions/{sid}/roster", cookies=ADMIN_COOKIE).json()
        row = next(i for i in g["items"] if i["id"] == subid)
        assert row["attendance"] == "attended"
        # untoggle (null)
        r2 = requests.post(f"{API}/admin/sessions/{sid}/attendance",
                           json={"updates": {subid: None}}, cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r2.status_code == 200
        g2 = requests.get(f"{API}/admin/sessions/{sid}/roster", cookies=ADMIN_COOKIE).json()
        assert next(i for i in g2["items"] if i["id"] == subid)["attendance"] is None

    def test_attendance_mark_rest_noshow(self, qa_data):
        sid = qa_data["sid"]; a, b, c = qa_data["sub_ids"]
        # mark one attended, rest should get no_show (not override attended)
        requests.post(f"{API}/admin/sessions/{sid}/attendance",
                      json={"updates": {a: "attended"}}, cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        r = requests.post(f"{API}/admin/sessions/{sid}/attendance",
                         json={"all": "no_show"}, cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)
        assert r.status_code == 200
        g = requests.get(f"{API}/admin/sessions/{sid}/roster", cookies=ADMIN_COOKIE).json()
        by = {i["id"]: i["attendance"] for i in g["items"]}
        assert by[a] == "attended"
        assert by[b] == "no_show"
        assert by[c] == "no_show"

    def test_attendance_requires_csrf_header(self, qa_data):
        # cookie set but no X-Requested-With -> 403
        r = requests.post(f"{API}/admin/sessions/{qa_data['sid']}/attendance",
                         json={"all": "no_show"}, cookies=ADMIN_COOKIE)
        assert r.status_code == 403

    def test_roster_404_bad_sid(self):
        r = requests.get(f"{API}/admin/sessions/does-not-exist/roster", cookies=ADMIN_COOKIE)
        assert r.status_code == 404


# ---------- Leader quote ----------
class TestLeaderQuote:
    def _put(self, lid, **extra):
        body = {"name": "QA Quote Leader", "role": "QA", "group": "board",
                "intro": "", "bio": "", "photo_url": "", "email": "",
                "linkedin": "", "quote": "", "visible": True, **extra}
        return requests.put(f"{API}/admin/leaders/{lid}", json=body,
                            cookies=ADMIN_COOKIE, headers=ADMIN_HEADERS)

    def test_put_accepts_quote(self, qa_data):
        r = self._put(qa_data["lid"], quote="When one sister rises, we all rise.")
        assert r.status_code == 200
        assert r.json()["quote"] == "When one sister rises, we all rise."

    def test_quote_strips_surrounding_quotes(self, qa_data):
        r = self._put(qa_data["lid"], quote='"Hello"')
        assert r.status_code == 200
        assert r.json()["quote"] == "Hello"
        r = self._put(qa_data["lid"], quote="“Smart”")
        assert r.json()["quote"] == "Smart"

    def test_quote_truncated_to_240(self, qa_data):
        long = "a" * 400
        r = self._put(qa_data["lid"], quote=long)
        assert r.status_code == 200
        assert len(r.json()["quote"]) == 240

    def test_public_leaders_exposes_quote(self, qa_data):
        self._put(qa_data["lid"], quote="public quote")
        r = requests.get(f"{API}/leaders")
        assert r.status_code == 200
        lead = next(x for x in r.json()["items"] if x["id"] == qa_data["lid"])
        assert lead["quote"] == "public quote"


# ---------- Gallery albums for Home + album page ----------
class TestAlbums:
    def test_album_auto_from_event_tag(self, qa_data):
        r = requests.get(f"{API}/gallery/albums")
        assert r.status_code == 200
        items = r.json()["items"]
        a = next((x for x in items if x["title"] == "QA Album Night"), None)
        assert a is not None, f"QA Album Night not surfaced; got {[i['title'] for i in items]}"
        assert a["count"] >= 1
        assert a["slug"]

    def test_album_detail_endpoint(self, qa_data):
        items = requests.get(f"{API}/gallery/albums").json()["items"]
        a = next(x for x in items if x["title"] == "QA Album Night")
        r = requests.get(f"{API}/gallery/albums/{a['slug']}")
        assert r.status_code == 200
        d = r.json()
        assert d["album"]["title"] == "QA Album Night"
        assert len(d["photos"]) == a["count"]

    def test_latest_album_is_most_recent(self, qa_data):
        # inject a second photo-less album by direct meta is overkill;
        # just verify first item is the newest by date desc
        items = requests.get(f"{API}/gallery/albums").json()["items"]
        if len(items) >= 2:
            dates = [i["date"] or "" for i in items]
            assert dates == sorted(dates, reverse=True)


# ---------- Public page regression ----------
PUBLIC_API_HEALTH_ROUTES = [
    "/api/leaders",
    "/api/programs?published=1",
    "/api/events",
    "/api/gallery/albums",
]

PUBLIC_HTML_ROUTES = [
    "/", "/about", "/leadership", "/initiatives", "/initiatives/business-elevation-lab",
    "/sessions", "/events", "/gallery", "/transparency", "/donate", "/volunteer",
    "/contact", "/privacy-policy", "/terms-of-service", "/accessibility",
    "/donor-privacy", "/membership", "/feedback", "/login",
]


class TestPublicRegression:
    @pytest.mark.parametrize("path", PUBLIC_API_HEALTH_ROUTES)
    def test_api_endpoints_ok(self, path):
        r = requests.get(f"{BASE}{path}", timeout=10)
        assert r.status_code == 200, f"{path} -> {r.status_code}"

    @pytest.mark.parametrize("path", PUBLIC_HTML_ROUTES)
    def test_html_route_loads(self, path):
        r = requests.get(f"{BASE}{path}", timeout=15)
        # SPA always returns 200 for the index.html
        assert r.status_code == 200
        assert "<div id=\"root\"" in r.text or "<div id='root'" in r.text


# ---------- Admin & Member Portal sanity ----------
MEMBER_COOKIE_A = {"session_token": "mem_tok_a"}


class TestPortalSanity:
    def test_admin_programs_ok(self):
        r = requests.get(f"{API}/admin/programs", cookies=ADMIN_COOKIE)
        assert r.status_code == 200

    def test_admin_leaders_ok(self):
        r = requests.get(f"{API}/admin/leaders", cookies=ADMIN_COOKIE)
        assert r.status_code == 200

    def test_admin_gallery_albums_ok(self):
        r = requests.get(f"{API}/admin/gallery-albums", cookies=ADMIN_COOKIE)
        assert r.status_code == 200

    def test_member_home_ok(self):
        r = requests.get(f"{API}/members/me", cookies=MEMBER_COOKIE_A)
        assert r.status_code == 200
