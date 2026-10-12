"""Iter45: Sponsors, guest names, quarterly accountant, live gala giving."""
import os
import sys
import time
import uuid
import subprocess
from datetime import datetime, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO = MongoClient(os.environ["MONGO_URL"])
DB = MONGO[os.environ["DB_NAME"]]

HEADERS = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}
COOKIES = {"session_token": "qa_tok_123"}

# Worker tag for xdist safety
WT = os.environ.get("PYTEST_XDIST_WORKER", "solo")
TAG = f"[iter45-{WT}-{int(time.time())}]"


# -------- fixtures --------
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.cookies.update(COOKIES)
    return s


@pytest.fixture(autouse=True)
def _clear_rl():
    # Keep rate limits open across tests
    for b in ("ticket-checkout", "promo-check", "ticket-names", "gala-screen", "checkout"):
        DB.rate_hits.delete_many({"key": {"$regex": f"^{b}:"}})
    yield


def _mk_event(api, title, date=None, with_tickets=True):
    date = date or (datetime.utcnow() + timedelta(days=30)).date().isoformat()
    r = api.post(f"{BASE}/api/admin/events", json={
        "title": title, "date": date, "time": "6:00pm", "location": "QA Hall",
        "description": "iter45 test", "status": "published"
    })
    assert r.status_code in (200, 201), r.text
    eid = r.json()["id"]
    if with_tickets:
        r = api.put(f"{BASE}/api/admin/events/{eid}/tickets", json={
            "ticket_types": [{"id": "", "name": "General", "price": 75, "qty": 20, "admits": 1}]
        })
        assert r.status_code == 200, r.text
    return eid


# ===================== Sponsors =====================
class TestSponsors:
    def test_sponsor_names_persist_and_drop_overflow(self, api):
        eid = _mk_event(api, f"QA Sponsors {TAG}")
        # Set 3 tables, with sponsor names including an out-of-range table 5
        r = api.put(f"{BASE}/api/admin/events/{eid}/seating",
                    json={"tables": 3, "seats": 8, "names": {"1": "Smith Family", "2": "Jones Co", "5": "Overflow"}})
        assert r.status_code == 200, r.text
        d = r.json()
        names = d["seating"]["names"]
        assert names.get("1") == "Smith Family"
        assert names.get("2") == "Jones Co"
        assert "5" not in names, "Names for tables beyond the count must be dropped"

        # GET persistence
        r2 = api.get(f"{BASE}/api/admin/events/{eid}/seating")
        assert r2.status_code == 200
        assert r2.json()["seating"]["names"].get("1") == "Smith Family"

        # Reduce tables to 1 — table 2 sponsor must be dropped on re-save
        r3 = api.put(f"{BASE}/api/admin/events/{eid}/seating",
                     json={"tables": 1, "seats": 8, "names": {"1": "Smith Family", "2": "Jones Co"}})
        assert r3.status_code == 200
        assert "2" not in r3.json()["seating"]["names"]

        DB.events.delete_one({"id": eid})


# ===================== Guest names =====================
class TestGuestNames:
    def _make_free_order(self, api, eid, promo_code, guest_names):
        r = api.post(f"{BASE}/api/events/{eid}/tickets/checkout", json={
            "name": "Buyer QA", "email": "qa_buyer@example.com",
            "items": [{"type_id": _general_id(eid), "qty": 2}],
            "promo_code": promo_code, "gift": 0, "guest_names": guest_names,
        })
        assert r.status_code == 200, r.text
        url = r.json()["url"]
        # Extract session_id (free_ path returns ?session_id=free_...)
        sid = url.split("session_id=")[-1]
        return sid

    def test_guest_names_fulfilment_and_edit(self, api):
        eid = _mk_event(api, f"QA Guests {TAG}")
        # 100% promo scoped to the event
        code = f"QAFREE100{WT}{int(time.time())%10000}"
        r = api.post(f"{BASE}/api/admin/promo-codes", json={
            "code": code, "kind": "percent", "value": 100, "event_id": eid, "max_uses": 0, "expires": ""
        })
        assert r.status_code in (200, 201), r.text

        sid = self._make_free_order(api, eid, code, ["Ann", "Bea"])

        # Fetch tickets by session -> get token
        r = api.get(f"{BASE}/api/tickets/session/{sid}")
        assert r.status_code == 200, r.text
        tok = r.json()["token"]

        # Order view returns guest_name + can_edit True
        r = api.get(f"{BASE}/api/tickets/order/{tok}")
        assert r.status_code == 200
        o = r.json()
        assert o["can_edit"] is True
        gns = sorted([t["guest_name"] for t in o["tickets"]])
        assert gns == ["Ann", "Bea"], o["tickets"]
        codes = [t["code"] for t in o["tickets"]]

        # Buyer updates names
        r = api.put(f"{BASE}/api/tickets/order/{tok}/names",
                    json={"names": {codes[0]: "Ann Updated", codes[1]: "Bea Updated"}})
        assert r.status_code == 200
        r2 = api.get(f"{BASE}/api/tickets/order/{tok}")
        gns2 = sorted([t["guest_name"] for t in r2.json()["tickets"]])
        assert gns2 == ["Ann Updated", "Bea Updated"]

        # Admin PUT name — valid code
        r = api.put(f"{BASE}/api/admin/events/{eid}/tickets/name",
                    json={"code": codes[0], "name": "Admin Edited"})
        assert r.status_code == 200
        # Wrong code -> 404
        r = api.put(f"{BASE}/api/admin/events/{eid}/tickets/name",
                    json={"code": "nope_bad_code", "name": "X"})
        assert r.status_code == 404

        # Ticket report shows guest_name + buyer
        r = api.get(f"{BASE}/api/admin/events/{eid}/tickets/report")
        assert r.status_code == 200
        guests = r.json()["guests"]
        assert any(g["holder"] == "Admin Edited" and g["buyer"] == "Buyer QA" for g in guests), guests
        assert any(g["holder"] == "Bea Updated" and g["buyer"] == "Buyer QA" for g in guests)

        # Seating GET -> groups[0].seats has {code,guest_name}
        r = api.get(f"{BASE}/api/admin/events/{eid}/seating")
        assert r.status_code == 200
        groups = r.json()["groups"]
        assert groups and all("seats" in g for g in groups)
        assert all(all("code" in s and "guest_name" in s for s in g["seats"]) for g in groups)

        # Now flip event date to the past -> PUT names must 400
        DB.events.update_one({"id": eid}, {"$set": {"date": "2020-01-01"}})
        r = api.put(f"{BASE}/api/tickets/order/{tok}/names", json={"names": {codes[0]: "Late"}})
        assert r.status_code == 400

        # Cleanup
        DB.tickets.delete_many({"event_id": eid})
        DB.ticket_orders.delete_many({"event_id": eid})
        DB.promo_codes.delete_one({"code": code})
        DB.events.delete_one({"id": eid})


def _general_id(eid):
    e = DB.events.find_one({"id": eid}, {"ticket_types": 1})
    return e["ticket_types"][0]["id"]


# ===================== Quarterly =====================
class TestQuarterly:
    def test_quarterly_default_true(self, api):
        r = api.get(f"{BASE}/api/admin/accounting")
        assert r.status_code == 200
        assert r.json().get("quarterly") is True

    def test_summary_quarter_label_and_bad_quarter(self, api):
        y = 2024
        r = api.get(f"{BASE}/api/admin/accounting/{y}/summary.csv", params={"quarter": 2})
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        first = r.text.splitlines()[1]  # second line (header + first data)
        assert f"Quarter {y} Q2" in first, first

        # Bad quarter
        r = api.get(f"{BASE}/api/admin/accounting/{y}/summary.csv", params={"quarter": 5})
        assert r.status_code == 400

    def test_period_values_and_acct_scheduled_june(self):
        code = r"""
import asyncio, sys, os
sys.path.insert(0, "/app/backend")
from datetime import datetime, timezone
os.environ.setdefault("MONGO_URL", os.environ["MONGO_URL"])
import server as s
# _period checks
assert s._period(2024, 0) == ("2024-01-01", "2025-01-01", "2024"), s._period(2024, 0)
assert s._period(2024, 1) == ("2024-01-01", "2024-04-01", "2024 Q1"), s._period(2024, 1)
assert s._period(2024, 2) == ("2024-04-01", "2024-07-01", "2024 Q2"), s._period(2024, 2)
assert s._period(2024, 3) == ("2024-07-01", "2024-10-01", "2024 Q3"), s._period(2024, 3)
assert s._period(2024, 4) == ("2024-10-01", "2025-01-01", "2024 Q4"), s._period(2024, 4)
# _acct_scheduled for a June date -> must return None without emailing
async def go():
    june = datetime(2026, 6, 15, 15, 0, tzinfo=timezone.utc)
    r = await s._acct_scheduled(june)
    assert r is None, r
asyncio.get_event_loop().run_until_complete(go())
print("ok")
"""
        env = os.environ.copy()
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd="/app/backend")
        assert p.returncode == 0 and p.stdout.strip().endswith("ok"), f"stdout={p.stdout}\nstderr={p.stderr}"


# ===================== Gala =====================
class TestGala:
    def test_gala_goal_and_screen_and_sources(self, api):
        eid = _mk_event(api, f"QA Gala {TAG}")

        # Set goal
        r = api.put(f"{BASE}/api/admin/events/{eid}/gala", json={"goal": 5000})
        assert r.status_code == 200, r.text
        assert r.json()["gala_goal"] == 5000

        # Screen initial
        r = api.get(f"{BASE}/api/gala/{eid}")
        assert r.status_code == 200
        d = r.json()
        assert d["goal"] == 5000
        assert d["raised"] == 0
        assert d["count"] == 0

        # Insert a named paid gift + an anonymous one
        now = datetime.utcnow().isoformat()
        DB.payment_transactions.insert_one({
            "session_id": f"qa_gala_named_{WT}", "event_id": eid, "amount": 100,
            "donor_name": "Zora Neale", "anonymous": False,
            "payment_status": "paid", "status": "paid", "updated_at": now, "source": "gala",
        })
        DB.payment_transactions.insert_one({
            "session_id": f"qa_gala_anon_{WT}", "event_id": eid, "amount": 150,
            "donor_name": "Secret Sister", "anonymous": True,
            "payment_status": "paid", "status": "paid", "updated_at": now, "source": "gala",
        })
        r = api.get(f"{BASE}/api/gala/{eid}")
        d = r.json()
        assert d["raised"] >= 200, d
        assert d["count"] == 2
        names = [x["name"] for x in d["recent"]]
        assert "Zora" in names and "Anonymous" in names, names

        # Not-found event
        r = api.get(f"{BASE}/api/gala/does_not_exist_xyz")
        assert r.status_code == 404

        # POST /api/payments/checkout with gala_event_id -> pending txn source gala + event_id
        payload = {
            "amount": 25, "frequency": "one-time",
            "donor_name": "Gala Donor", "donor_email": "gala_donor@example.com",
            "anonymous": False, "origin_url": BASE, "gala_event_id": eid,
        }
        r = api.post(f"{BASE}/api/payments/checkout", json=payload)
        # 200 if Stripe is configured; some envs may 424 — accept either but then skip the DB check.
        if r.status_code != 200:
            pytest.skip(f"Stripe checkout unavailable: {r.status_code} {r.text[:200]}")
        sid = r.json()["session_id"]
        txn = DB.payment_transactions.find_one({"session_id": sid})
        assert txn, "pending txn not stored"
        assert txn.get("event_id") == eid
        assert txn.get("source") == "gala"
        assert txn.get("payment_status") == "pending"
        DB.payment_transactions.delete_one({"session_id": sid})

        # Cleanup gala seeds
        DB.payment_transactions.delete_many({"session_id": {"$regex": "^qa_gala_"}})
        DB.events.delete_one({"id": eid})


# ===================== Regression: iter44 promo + gift =====================
class TestRegression:
    def test_promo_plus_gift_checkout_still_works(self, api):
        eid = _mk_event(api, f"QA Reg {TAG}")
        code = f"QAEARLY{WT}{int(time.time())%10000}"
        r = api.post(f"{BASE}/api/admin/promo-codes", json={
            "code": code, "kind": "percent", "value": 20, "event_id": "", "max_uses": 1, "expires": ""
        })
        assert r.status_code in (200, 201), r.text
        tid = _general_id(eid)
        r = api.post(f"{BASE}/api/events/{eid}/tickets/checkout", json={
            "name": "Reg QA", "email": "reg_qa@example.com",
            "items": [{"type_id": tid, "qty": 2}],
            "promo_code": code, "gift": 50, "guest_names": [],
        })
        # Expect a Stripe URL or 424 if Stripe unavailable
        if r.status_code == 424:
            pytest.skip("Stripe unavailable")
        assert r.status_code == 200, r.text
        assert "http" in r.json()["url"]
        o = DB.ticket_orders.find_one({"event_id": eid, "email": "reg_qa@example.com"})
        assert o and o["subtotal"] == 150 and o["discount"] == 30 and o["total"] == 120 and o["gift"] == 50
        # Cleanup
        DB.ticket_orders.delete_many({"event_id": eid})
        DB.promo_codes.delete_one({"code": code})
        DB.events.delete_one({"id": eid})
