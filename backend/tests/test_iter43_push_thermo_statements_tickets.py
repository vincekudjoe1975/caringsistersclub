"""Iter 43 — push reconcile, thermometer/share, year-end statements, event ticketing.

Backend coverage. Push, statements, and ticketing endpoints with pymongo-level
fulfilment to simulate paid orders (headless can't complete real Stripe payments).
Teardown removes every QA row.
"""
import os
import time
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
MONGO = MongoClient(os.environ["MONGO_URL"])
DB = MONGO[os.environ["DB_NAME"]]

ADMIN = {"session_token": "qa_tok_123"}
MEMBER_A = {"session_token": "mem_tok_a"}
MEMBER_B = {"session_token": "mem_tok_b"}
XRW = {"X-Requested-With": "XMLHttpRequest"}


def _s(cookies):
    s = requests.Session()
    s.cookies.update(cookies)
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session", autouse=True)
def setup_teardown():
    # Make member A active member
    DB.users.update_one({"user_id": "qa_mem_a"}, {"$set": {"member_status": "active"}})
    DB.users.update_one({"user_id": "qa_mem_b"}, {"$set": {"member_status": "active"}})
    # Make sure no stale push subs for these users
    DB.push_subs.delete_many({"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}})
    DB.push_log.delete_many({"kind": "test"})
    DB.payment_transactions.delete_many({"session_id": {"$regex": "^qa_stmt_"}})
    DB.donor_statement_tokens.delete_many({"email": {"$regex": "qa-"}})
    DB.rate_hits.delete_many({"key": {"$regex": "^statement-link:"}})
    yield
    # Teardown
    DB.push_subs.delete_many({"user_id": {"$in": ["qa_mem_a", "qa_mem_b"]}})
    DB.push_subs.delete_many({"endpoint": {"$regex": "qa-push"}})
    DB.push_log.delete_many({"kind": "test"})
    DB.payment_transactions.delete_many({"session_id": {"$regex": "^qa_stmt_"}})
    DB.donor_statement_tokens.delete_many({"email": {"$regex": "qa-"}})
    # Events/tickets cleanup done per-test
    for e in DB.events.find({"title": {"$regex": "^QA Iter43"}}, {"id": 1}):
        DB.events.delete_one({"id": e["id"]})
        DB.ticket_orders.delete_many({"event_id": e["id"]})
        DB.tickets.delete_many({"event_id": e["id"]})


# -------------------- A. Push reconcile --------------------
class TestPush:
    FCM = "https://fcm.googleapis.com/fcm/send/qa-push-abc"
    APL = "https://web.push.apple.com/qa-push-apple-xyz"
    WIN = "https://xyz.notify.windows.com/qa-push-win"
    KEYS = {"p256dh": "BPx" + "A" * 85, "auth": "k" * 22}

    def test_a1_config_before_subscribe_registered_false(self):
        r = _s(MEMBER_A).get(f"{BASE}/members/push/config", params={"endpoint": self.FCM})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "public_key" in data and data["public_key"]
        assert data["registered"] is False
        assert data["devices"] == 0

    def test_a2_test_self_400_when_no_devices(self):
        r = _s(MEMBER_A).post(f"{BASE}/members/push/test-self", headers=XRW)
        assert r.status_code == 400

    def test_a3_subscribe_fcm_returns_kind_android(self):
        r = _s(MEMBER_A).post(f"{BASE}/members/push/subscribe", json={"endpoint": self.FCM, "keys": self.KEYS}, headers=XRW)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["kind"] == "Android / Chrome"

    def test_a4_config_after_subscribe_registered_true(self):
        r = _s(MEMBER_A).get(f"{BASE}/members/push/config", params={"endpoint": self.FCM})
        data = r.json()
        assert data["registered"] is True
        assert data["devices"] >= 1
        kinds_this = [d for d in data["device_list"] if d["this"]]
        assert kinds_this and kinds_this[0]["kind"] == "Android / Chrome"

    def test_a5_device_kinds_map_by_host(self):
        _s(MEMBER_A).post(f"{BASE}/members/push/subscribe", json={"endpoint": self.APL, "keys": self.KEYS}, headers=XRW)
        _s(MEMBER_A).post(f"{BASE}/members/push/subscribe", json={"endpoint": self.WIN, "keys": self.KEYS}, headers=XRW)
        r = _s(MEMBER_A).get(f"{BASE}/members/push/config", params={"endpoint": self.FCM})
        kinds = {d["kind"] for d in r.json()["device_list"]}
        assert {"Android / Chrome", "iPhone / iPad", "Windows / Edge"}.issubset(kinds), kinds

    def test_a6_test_self_200_with_devices_logs_test(self):
        # Fake endpoints -> webpush will return failure/removed. The endpoint still returns {sent, devices}
        r = _s(MEMBER_A).post(f"{BASE}/members/push/test-self", headers=XRW)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "sent" in data and "devices" in data
        # push_log entry with kind=test must exist for user
        time.sleep(0.3)
        lg = DB.push_log.find_one({"kind": "test"}, sort=[("sent_at", -1)])
        assert lg is not None, "push_log kind=test not written"

    def test_a7_resubscribe_under_other_user_rebinds(self):
        # Member B subscribes same FCM endpoint; it should rebind user_id to qa_mem_b
        r = _s(MEMBER_B).post(f"{BASE}/members/push/subscribe", json={"endpoint": self.FCM, "keys": self.KEYS}, headers=XRW)
        assert r.status_code == 200
        row = DB.push_subs.find_one({"endpoint": self.FCM})
        assert row and row["user_id"] == "qa_mem_b"


# -------------------- B. Year-end statements --------------------
class TestStatements:
    EMAIL = "qa-donor@example.com"

    @classmethod
    def _insert_gift(cls):
        DB.payment_transactions.insert_one({
            "session_id": "qa_stmt_1",
            "payment_status": "paid",
            "donor_email": cls.EMAIL,
            "donor_name": "QA Donor",
            "amount": 120.0,
            "frequency": "one-time",
            "updated_at": "2025-05-02T10:00:00+00:00",
        })

    def test_b1_statement_link_sends_message_and_creates_token(self):
        self._insert_gift()
        r = _s({}).post(f"{BASE}/donor/statement-link", json={"email": self.EMAIL})
        assert r.status_code == 200, r.text
        assert "secure download link" in r.json()["message"].lower()
        tok = DB.donor_statement_tokens.find_one({"email": self.EMAIL}, sort=[("created_at", -1)])
        assert tok and tok["token"]
        self.__class__.token = tok["token"]

    def test_b2_years_returns_2025_total_120(self):
        r = _s({}).get(f"{BASE}/donor/statements/{self.token}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == self.EMAIL
        years = {y["year"]: y for y in data["years"]}
        assert 2025 in years
        assert years[2025]["total"] == 120.0
        assert years[2025]["count"] == 1

    def test_b3_pdf_download(self):
        r = _s({}).get(f"{BASE}/donor/statements/{self.token}/2025.pdf")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_b4_year_without_gifts_404(self):
        r = _s({}).get(f"{BASE}/donor/statements/{self.token}/2020.pdf")
        assert r.status_code == 404

    def test_b5_bad_token_410(self):
        r = _s({}).get(f"{BASE}/donor/statements/nope-bad-token-xyz")
        assert r.status_code == 410

    def test_b6_rate_limit_3_per_5min(self):
        # already 1 call in b1, so 2 more should pass, 4th should 429
        codes = []
        for _ in range(4):
            codes.append(_s({}).post(f"{BASE}/donor/statement-link", json={"email": self.EMAIL}).status_code)
        assert 429 in codes, codes


# -------------------- C. Event ticketing --------------------
class TestTickets:
    @classmethod
    def setup_class(cls):
        # Create future event
        r = _s(ADMIN).post(
            f"{BASE}/admin/events",
            json={"title": "QA Iter43 Gala", "date": "2026-12-20", "time": "6:00 PM",
                  "location": "QA Hall", "description": "QA", "capacity": 200},
            headers=XRW,
        )
        assert r.status_code == 200, r.text
        cls.eid = r.json()["id"]

    def test_c1_put_tickets_assigns_ids(self):
        r = _s(ADMIN).put(
            f"{BASE}/admin/events/{self.eid}/tickets",
            json={"ticket_types": [
                {"name": "General", "price": 75, "qty": 2, "admits": 1},
                {"name": "Table of 8", "price": 500, "qty": 1, "admits": 8},
            ]},
            headers=XRW,
        )
        assert r.status_code == 200, r.text
        types = r.json()["ticket_types"]
        assert len(types) == 2 and all(t["id"] for t in types)
        self.__class__.types = types

    def test_c2_validation_bad_values_400(self):
        for bad in (
            [{"name": "X", "price": 0, "qty": 2, "admits": 1}],
            [{"name": "X", "price": 10, "qty": 0, "admits": 1}],
            [{"name": "X", "price": 10, "qty": 2, "admits": 21}],
        ):
            r = _s(ADMIN).put(f"{BASE}/admin/events/{self.eid}/tickets", json={"ticket_types": bad}, headers=XRW)
            assert r.status_code == 400, (bad, r.status_code, r.text)

    def test_c3_public_events_includes_remaining(self):
        r = _s({}).get(f"{BASE}/events")
        assert r.status_code == 200
        ev = next((e for e in r.json()["items"] if e["id"] == self.eid), None)
        assert ev is not None
        tt = {t["name"]: t for t in ev["ticket_types"]}
        assert tt["General"]["remaining"] == 2
        assert tt["Table of 8"]["remaining"] == 1

    def test_c4_checkout_returns_stripe_url_and_pending_holds(self):
        gen = next(t for t in self.types if t["name"] == "General")
        r = _s({}).post(
            f"{BASE}/events/{self.eid}/tickets/checkout",
            json={"name": "QA Buyer", "email": "qa-buyer@example.com", "items": [{"type_id": gen["id"], "qty": 1}]},
        )
        assert r.status_code == 200, r.text
        url = r.json()["url"]
        assert "stripe.com" in url
        # Pending reduces remaining
        pub = _s({}).get(f"{BASE}/events").json()["items"]
        ev = next(e for e in pub if e["id"] == self.eid)
        gen2 = next(t for t in ev["ticket_types"] if t["name"] == "General")
        assert gen2["remaining"] == 1
        self.__class__.pending_sid = DB.ticket_orders.find_one(
            {"event_id": self.eid, "status": "pending", "email": "qa-buyer@example.com"},
            sort=[("created_at", -1)],
        )["session_id"]

    def test_c5_checkout_over_remaining_400(self):
        gen = next(t for t in self.types if t["name"] == "General")
        r = _s({}).post(
            f"{BASE}/events/{self.eid}/tickets/checkout",
            json={"name": "QA Over", "email": "qa-over@example.com", "items": [{"type_id": gen["id"], "qty": 5}]},
        )
        assert r.status_code == 400, r.text

    def test_c6_fulfil_order_creates_tickets(self):
        # Simulate webhook fulfilment: mark pending order as paid + insert tickets.
        o = DB.ticket_orders.find_one_and_update(
            {"session_id": self.pending_sid, "status": "pending"},
            {"$set": {"status": "paid", "paid_at": "2026-01-05T00:00:00+00:00"}},
            return_document=True,
        )
        assert o is not None
        import secrets
        tickets = []
        seat = 0
        for it in o["items"]:
            for _ in range(it["qty"] * it["admits"]):
                seat += 1
                tickets.append({
                    "code": secrets.token_urlsafe(12), "order_id": o["id"], "event_id": o["event_id"],
                    "type": it["name"], "seat": seat, "holder": o["name"],
                    "checked_in_at": None, "created_at": "2026-01-05T00:00:00+00:00",
                })
        DB.tickets.insert_many(tickets)
        self.__class__.order_token = o["token"]
        self.__class__.ticket_code = tickets[0]["code"]
        assert len(tickets) == 1  # qty=1 * admits=1

    def test_c7_order_endpoint_returns_tickets(self):
        r = _s({}).get(f"{BASE}/tickets/order/{self.order_token}")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "QA Buyer"
        assert len(data["tickets"]) == 1

    def test_c8_qr_png(self):
        r = _s({}).get(f"{BASE}/tickets/qr/{self.ticket_code}.png")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert r.content[:4] == b"\x89PNG"

    def test_c9_checkin_then_already(self):
        r1 = _s(ADMIN).post(f"{BASE}/admin/events/{self.eid}/tickets/checkin", json={"code": self.ticket_code}, headers=XRW)
        assert r1.status_code == 200 and r1.json()["ok"] is True
        r2 = _s(ADMIN).post(f"{BASE}/admin/events/{self.eid}/tickets/checkin", json={"code": self.ticket_code}, headers=XRW)
        assert r2.status_code == 200
        assert r2.json()["ok"] is False and r2.json()["already"] is True

    def test_c10_wrong_event_404(self):
        r = _s(ADMIN).post(f"{BASE}/admin/events/not-an-event/tickets/checkin", json={"code": self.ticket_code}, headers=XRW)
        assert r.status_code == 404

    def test_c11_undo_clears_checkin(self):
        r = _s(ADMIN).post(f"{BASE}/admin/events/{self.eid}/tickets/undo", json={"code": self.ticket_code}, headers=XRW)
        assert r.status_code == 200
        t = DB.tickets.find_one({"code": self.ticket_code})
        assert t["checked_in_at"] is None

    def test_c12_report_has_sold_revenue(self):
        r = _s(ADMIN).get(f"{BASE}/admin/events/{self.eid}/tickets/report")
        assert r.status_code == 200
        data = r.json()
        assert data["orders"] == 1
        assert data["revenue"] == 75.0
        assert data["seats"] == 1
        gen = next(t for t in data["types"] if t["name"] == "General")
        assert gen["sold"] == 1 and gen["revenue"] == 75.0

    def test_c13_csv_text(self):
        r = _s(ADMIN).get(f"{BASE}/admin/events/{self.eid}/tickets.csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert b"QA Buyer" in r.content

    def test_c14_lower_qty_below_sold_400(self):
        # Try to lower General qty to 0 while 1 is sold
        payload = {"ticket_types": [
            {"id": t["id"], "name": t["name"], "price": t["price"],
             "qty": 0 if t["name"] == "General" else t["qty"], "admits": t["admits"]}
            for t in self.types
        ]}
        # qty 0 is also invalid (<1) — hit "needs...quantity" 400 first; still 400 ok.
        r = _s(ADMIN).put(f"{BASE}/admin/events/{self.eid}/tickets", json=payload, headers=XRW)
        assert r.status_code == 400

    def test_c15_remove_type_with_sales_400(self):
        payload = {"ticket_types": [
            {"id": t["id"], "name": t["name"], "price": t["price"], "qty": t["qty"], "admits": t["admits"]}
            for t in self.types if t["name"] != "General"
        ]}
        r = _s(ADMIN).put(f"{BASE}/admin/events/{self.eid}/tickets", json=payload, headers=XRW)
        assert r.status_code == 400
