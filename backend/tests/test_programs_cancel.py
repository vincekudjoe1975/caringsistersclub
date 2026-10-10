"""Backend tests for Programs & Initiatives, Cancellation Thank-You, Donor Manage Token single-use.
Prereq: qa_session.py up (session_token=qa_tok_123, admin). A cancellation doc with
sub_id='sub_qa_1' must exist (seeded by this test's fixture).
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
DB = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
ADMIN_COOKIES = {"session_token": "qa_tok_123"}


@pytest.fixture
def admin():
    s = requests.Session(); s.cookies.update(ADMIN_COOKIES)
    s.headers.update({"X-Requested-With": "XMLHttpRequest"})
    return s


@pytest.fixture
def pub():
    return requests.Session()


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    DB.programs.delete_many({"title": {"$regex": "^QA"}})
    DB.donor_manage_tokens.delete_many({"token": {"$regex": "^qa_"}})
    DB.settings.update_one({"key": "site"}, {"$unset": {"program_categories": ""}})


# ---------- Programs ----------
class TestPrograms:
    def test_admin_requires_auth(self, pub):
        r = pub.get(f"{BASE}/api/admin/programs")
        assert r.status_code in (401, 403)

    def test_admin_lists_6_seeded(self, admin):
        r = admin.get(f"{BASE}/api/admin/programs")
        assert r.status_code == 200, r.text
        j = r.json()
        assert len(j["items"]) >= 6
        assert all(p.get("slug") for p in j["items"])
        assert "categories" in j

    def test_public_lists_published_only_no_body(self, pub):
        r = pub.get(f"{BASE}/api/programs")
        assert r.status_code == 200
        j = r.json()
        assert len(j["items"]) >= 1
        # Public hides body field
        assert all("body" not in p for p in j["items"])
        # order ascending
        orders = [p.get("order", 0) for p in j["items"]]
        assert orders == sorted(orders)

    def test_create_program(self, admin):
        payload = {
            "title": f"QA Mentorship {uuid.uuid4().hex[:5]}",
            "category": "Professional",
            "image_url": "",
            "summary": "QA summary",
            "body": "QA body long story about this program.",
            "goals": ["Goal A", "Goal B"],
            "impact": [{"value": "100+", "label": "women"}],
            "cta_text": "Join",
            "cta_link": "/volunteer",
            "published": True,
        }
        r = admin.post(f"{BASE}/api/admin/programs", json=payload)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["title"] == payload["title"]
        assert p["slug"].startswith("qa-mentorship")
        # Verify persistence via GET
        pid = p["id"]
        got = admin.get(f"{BASE}/api/admin/programs").json()["items"]
        assert any(x["id"] == pid for x in got)
        return pid

    def test_create_rejects_js_link(self, admin):
        payload = {"title": "QA Bad Link", "category": "", "image_url": "",
                   "summary": "", "body": "", "goals": [], "impact": [],
                   "cta_text": "", "cta_link": "javascript:alert(1)", "published": True}
        r = admin.post(f"{BASE}/api/admin/programs", json=payload)
        assert r.status_code == 400
        assert "link" in r.json()["detail"].lower()

    def test_create_rejects_bad_image(self, admin):
        payload = {"title": "QA Bad Img", "category": "", "image_url": "http://insecure.example.com/a.png",
                   "summary": "", "body": "", "goals": [], "impact": [],
                   "cta_text": "", "cta_link": "/volunteer", "published": True}
        r = admin.post(f"{BASE}/api/admin/programs", json=payload)
        assert r.status_code == 400

    def test_update_toggle_publish_and_detail(self, admin, pub):
        # create
        r = admin.post(f"{BASE}/api/admin/programs", json={
            "title": "QA Toggle", "category": "", "image_url": "",
            "summary": "s", "body": "b", "goals": [], "impact": [],
            "cta_text": "Go", "cta_link": "/donate", "published": True})
        p = r.json(); pid, slug = p["id"], p["slug"]
        # public detail available
        d = pub.get(f"{BASE}/api/programs/{slug}")
        assert d.status_code == 200
        assert d.json()["body"] == "b"
        # unpublish
        p["published"] = False
        r = admin.put(f"{BASE}/api/admin/programs/{pid}", json=p)
        assert r.status_code == 200
        # public detail now 404
        d2 = pub.get(f"{BASE}/api/programs/{slug}")
        assert d2.status_code == 404
        # unknown slug 404
        assert pub.get(f"{BASE}/api/programs/does-not-exist-slug").status_code == 404

    def test_reorder_persists(self, admin):
        items = admin.get(f"{BASE}/api/admin/programs").json()["items"]
        if len(items) < 2:
            pytest.skip("need 2+ programs")
        ids = [p["id"] for p in items]
        reversed_ids = list(reversed(ids))
        r = admin.post(f"{BASE}/api/admin/programs/reorder", json={"ids": reversed_ids})
        assert r.status_code == 200
        # verify
        new_items = admin.get(f"{BASE}/api/admin/programs").json()["items"]
        assert [p["id"] for p in new_items] == reversed_ids
        # restore
        admin.post(f"{BASE}/api/admin/programs/reorder", json={"ids": ids})

    def test_delete_program(self, admin):
        r = admin.post(f"{BASE}/api/admin/programs", json={
            "title": "QA ToDelete", "category": "", "image_url": "",
            "summary": "", "body": "", "goals": [], "impact": [],
            "cta_text": "", "cta_link": "/volunteer", "published": True})
        pid = r.json()["id"]
        d = admin.delete(f"{BASE}/api/admin/programs/{pid}")
        assert d.status_code == 200
        assert d.json()["deleted"] is True
        # 404 on delete again
        assert admin.delete(f"{BASE}/api/admin/programs/{pid}").status_code == 404

    def test_categories_editor(self, admin, pub):
        r = admin.put(f"{BASE}/api/admin/program-categories",
                      json={"categories": ["Professional", "Housing", "Community", "QA Extra"]})
        assert r.status_code == 200
        assert "QA Extra" in r.json()["categories"]
        # Reflected in public listing categories list
        p = pub.get(f"{BASE}/api/programs").json()
        assert "QA Extra" in p["categories"]
        # empty rejected
        bad = admin.put(f"{BASE}/api/admin/program-categories", json={"categories": []})
        assert bad.status_code == 400


# ---------- Cancellation Thank-You ----------
class TestCancellation:
    def _tok(self):
        c = DB.cancellations.find_one({"sub_id": "sub_qa_1"}, {"_id": 0})
        assert c, "QA cancellation (sub_qa_1) must be seeded"
        return c["token"]

    def test_token_info(self, pub):
        tok = self._tok()
        r = pub.get(f"{BASE}/api/cancellations/token/{tok}")
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["email"] == "qa.donor@example.com"
        assert j["amount"] == 25.0
        assert j["thanked"] is False
        # Prefilled note from server
        assert j["subject"]
        assert j["message"]

    def test_invalid_token_404(self, pub):
        r = pub.get(f"{BASE}/api/cancellations/token/no_such_token_xyz_123")
        assert r.status_code == 404

    def test_empty_subject_400(self, pub):
        tok = self._tok()
        r = pub.post(f"{BASE}/api/cancellations/token/{tok}", json={"subject": "", "message": "hi"})
        assert r.status_code == 400

    def test_send_undeliverable_reverts_thanked(self, pub):
        tok = self._tok()
        # thanked must currently be false
        DB.cancellations.update_one({"sub_id": "sub_qa_1"},
                                    {"$set": {"thanked": False}, "$unset": {"thanked_at": ""}})
        r = pub.post(f"{BASE}/api/cancellations/token/{tok}",
                     json={"subject": "QA subj", "message": "QA note"})
        # undeliverable @example.com -> 424 (per main-agent note)
        assert r.status_code in (424, 502), r.text
        c = DB.cancellations.find_one({"sub_id": "sub_qa_1"}, {"_id": 0})
        assert c["thanked"] is False  # reverted


# ---------- Donor Manage Token single-use ----------
class TestManageTokenSingleUse:
    def test_single_use_lifecycle(self, pub):
        txn = DB.payment_transactions.find_one(
            {"frequency": "monthly", "payment_status": "paid",
             "stripe_subscription_id": {"$nin": [None, ""]}})
        if not txn:
            pytest.skip("No real monthly donor")
        tok = "qa_rcpt_tok_" + uuid.uuid4().hex[:10]
        DB.donor_manage_tokens.insert_one({
            "token": tok, "email": txn["donor_email"].lower(),
            "kind": "receipt", "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        })
        try:
            info = pub.get(f"{BASE}/api/donor/manage-token/{tok}").json()
            assert info["valid"] is True
            r = pub.post(f"{BASE}/api/donor/portal", json={"token": tok})
            assert r.status_code == 200, r.text
            assert "billing.stripe.com" in r.json()["url"]
            # second use -> 410
            r2 = pub.post(f"{BASE}/api/donor/portal", json={"token": tok})
            assert r2.status_code == 410
            # GET info now valid:false
            info2 = pub.get(f"{BASE}/api/donor/manage-token/{tok}").json()
            assert info2["valid"] is False
        finally:
            DB.donor_manage_tokens.delete_one({"token": tok})


# ---------- CSV formula injection ----------
class TestCsvInjection:
    def test_donations_export_prefixes_formula(self, admin):
        # inject a transaction whose donor_name starts with '='
        bad_sid = "qa_csv_injection_" + uuid.uuid4().hex[:8]
        DB.payment_transactions.insert_one({
            "session_id": bad_sid, "donor_name": "=1+1", "donor_email": "+csv@example.com",
            "amount": 1.0, "frequency": "one-time", "payment_status": "paid",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            r = admin.get(f"{BASE}/api/admin/donations/export")
            assert r.status_code == 200
            body = r.text
            # Formula cell must be prefixed with ' not raw '='
            assert ",\"'=1+1\"," in body or ",'=1+1," in body or "'=1+1" in body
            assert "'+csv@example.com" in body
        finally:
            DB.payment_transactions.delete_one({"session_id": bad_sid})
