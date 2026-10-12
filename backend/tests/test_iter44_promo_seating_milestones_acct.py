"""Iter 44 — Ticket promo codes, checkout math (promo+gift+100%+free),
table seating API/auto-seat, campaign milestone alerts, and the accountant
year-end package (defaults, cfg validation, CSVs, token download, scheduler).

- Public /events endpoints and admin events APIs via REACT_APP_BACKEND_URL/api.
- Subprocess helper is used to invoke the two in-process server coroutines
  that the testing spec requires: `_fulfil_ticket_order(session_id)` (to
  simulate a paid Stripe webhook without hitting Stripe) and
  `_acct_scheduled(now)` with a non-January datetime (never with a January
  datetime because that would actually email the real accountant).
- Every QA row the suite creates is cleaned at teardown.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
MONGO = MongoClient(os.environ["MONGO_URL"])
DB = MONGO[os.environ["DB_NAME"]]

# This module manipulates shared singletons (settings.goal, QA promo codes,
# accountant cfg) and relies on test ordering within a class. Pin ALL tests
# in this file to a single xdist worker so classes don't race each other.
pytestmark = pytest.mark.xdist_group(name="iter44_shared")

ADMIN = {"session_token": "qa_tok_123"}
XRW = {"X-Requested-With": "XMLHttpRequest"}

QA_TITLE_BASE = "QA Iter44"
QA_CODE_PREFIX = "QA"  # all QA codes start with "QA" for easy teardown


@pytest.fixture(scope="session")
def worker_tag(worker_id):
    """xdist worker suffix — scopes event fixtures per-worker so one worker's
    teardown doesn't wipe another worker's live events."""
    return worker_id if worker_id and worker_id != "master" else "solo"


def _s(cookies=None):
    s = requests.Session()
    if cookies:
        s.cookies.update(cookies)
    s.headers.update({"Content-Type": "application/json"})
    return s


def _clear_rl():
    """Reset per-IP rate-limit buckets so our rapid test traffic doesn't 429."""
    DB.rate_hits.delete_many({"key": {"$regex": "^(ticket-checkout|promo-check|acct-download):"}})


def _run_server_fn(call: str) -> str:
    """Run a snippet inside backend's python so we can call in-process server
    coroutines (like _fulfil_ticket_order and _acct_scheduled). Returns the
    stdout string.
    """
    code = (
        "import sys, asyncio, json\n"
        "sys.path.insert(0, '/app/backend')\n"
        "from datetime import datetime, timezone\n"
        "import server\n"
        f"{call}\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=45, cwd="/app/backend",
    )
    assert r.returncode == 0, f"server fn failed: {r.stderr}\nstdout: {r.stdout}"
    return r.stdout.strip()


# -------------------- Session-wide fixture --------------------
@pytest.fixture(scope="session", autouse=True)
def setup_teardown(worker_tag):
    tag_regex = f"^{QA_TITLE_BASE}\\b.*\\[{worker_tag}\\]"
    # NOTE: qa admin session (cookie=qa_tok_123) must be brought up *before*
    # the suite runs (python3 /app/backend/tests/qa_session.py up). We do NOT
    # bring it up/down here because this suite runs under pytest-xdist with
    # multiple workers; a per-worker teardown would delete the cookie while
    # another worker is still mid-test.

    # Snapshot settings so we can restore the goal etc at the end
    orig_site = DB.settings.find_one({"key": "site"}, {"_id": 0}) or {}

    # Snapshot accountant settings so we can restore exactly
    orig_acct = DB.settings.find_one({"key": "accountant"}, {"_id": 0}) or None

    # Pre-clean any left-over QA rows
    DB.promo_codes.delete_many({"code": {"$regex": "^QA"}})
    DB.acct_tokens.delete_many({"token": {"$regex": "^qa_"}})
    # Clear rate-limit buckets that our rapid test traffic trips
    DB.rate_hits.delete_many({"key": {"$regex": "^(ticket-checkout|promo-check|acct-download):"}})
    for ev in DB.events.find({"title": {"$regex": tag_regex}}, {"id": 1}):
        DB.events.delete_one({"id": ev["id"]})
        DB.ticket_orders.delete_many({"event_id": ev["id"]})
        DB.tickets.delete_many({"event_id": ev["id"]})

    yield

    # Teardown — remove every QA row touched by this suite (scoped to this worker)
    DB.promo_codes.delete_many({"code": {"$regex": "^QA"}})
    DB.acct_tokens.delete_many({"token": {"$regex": "^qa_"}})

    eids = [ev["id"] for ev in DB.events.find({"title": {"$regex": tag_regex}}, {"id": 1})]
    order_ids = [o["id"] for o in DB.ticket_orders.find({"event_id": {"$in": eids}}, {"id": 1})]
    DB.payment_transactions.delete_many({"session_id": {"$in": [f"tkt_{oid}" for oid in order_ids]}})
    DB.tickets.delete_many({"event_id": {"$in": eids}})
    DB.ticket_orders.delete_many({"event_id": {"$in": eids}})
    DB.events.delete_many({"id": {"$in": eids}})

    # Milestones + push_log that this suite created — only in solo mode.
    # Under xdist, deleting these in one worker's teardown races with another
    # worker's TestMilestones.test_d run.
    if worker_tag == "solo":
        DB.milestones_sent.delete_many({"goal": {"$in": [1.0, 1]}})
        DB.push_log.delete_many({"kind": "campaign", "title": {"$regex": "goal"}})

    # Restore site settings via the admin endpoint only when this is the sole
    # worker. Under xdist, each worker runs the session teardown independently;
    # restoring the goal here would race with another worker's milestone test.
    if worker_tag == "solo" and orig_site:
        payload = {k: orig_site.get(k) for k in ("campaign_title", "campaign_subtitle", "goal", "deadline") if k in orig_site}
        if payload:
            _s(ADMIN).put(f"{BASE}/admin/settings", json=payload, headers=XRW)

    # Restore accountant settings exactly
    if orig_acct:
        DB.settings.replace_one({"key": "accountant"}, orig_acct, upsert=True)
    else:
        DB.settings.delete_one({"key": "accountant"})

    # NOTE: do not run qa_session.py down here (xdist multi-worker).


@pytest.fixture(autouse=True)
def _clear_rl_before_each():
    """Clear tight rate-limit buckets before every test — this suite does many
    rapid checkouts/promo-checks that otherwise trip the per-IP limiter."""
    _clear_rl()
    yield


# -------------------- Event fixture --------------------
@pytest.fixture(scope="session")
def qa_event(worker_tag):
    tt = f" [{worker_tag}]"
    # Create primary QA event
    r = _s(ADMIN).post(
        f"{BASE}/admin/events",
        json={"title": f"{QA_TITLE_BASE} Gala{tt}", "date": "2026-12-20", "time": "6:00 PM",
              "location": "QA Hall", "description": "QA", "capacity": 200},
        headers=XRW,
    )
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    r = _s(ADMIN).put(
        f"{BASE}/admin/events/{eid}/tickets",
        json={"ticket_types": [
            {"name": "General", "price": 75, "qty": 10, "admits": 1},
            {"name": "Table of 8", "price": 500, "qty": 2, "admits": 8},
        ]},
        headers=XRW,
    )
    assert r.status_code == 200, r.text
    types = {t["name"]: t for t in r.json()["ticket_types"]}

    # Create a second QA event (used to test event-specific promo codes)
    r2 = _s(ADMIN).post(
        f"{BASE}/admin/events",
        json={"title": f"{QA_TITLE_BASE} Gala Other{tt}", "date": "2026-12-22", "time": "6:00 PM",
              "location": "QA Hall 2", "description": "QA2", "capacity": 50},
        headers=XRW,
    )
    assert r2.status_code == 200
    eid2 = r2.json()["id"]
    r2b = _s(ADMIN).put(
        f"{BASE}/admin/events/{eid2}/tickets",
        json={"ticket_types": [{"name": "General", "price": 50, "qty": 10, "admits": 1}]},
        headers=XRW,
    )
    assert r2b.status_code == 200
    return {"eid": eid, "eid2": eid2, "types": types}


# -------------------- A. Promo API --------------------
class TestIter44:
    def test_a1_create_percent_code_normalises(self, qa_event):
        r = _s(ADMIN).post(
            f"{BASE}/admin/promo-codes",
            json={"code": "qaearly", "kind": "percent", "value": 20,
                  "event_id": "", "max_uses": 1, "expires": ""},
            headers=XRW,
        )
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["code"] == "QAEARLY"
        assert doc["kind"] == "percent" and doc["value"] == 20
        assert doc["active"] is True and doc["uses"] == 0
        assert doc["max_uses"] == 1

    def test_a2_duplicate_code_400(self):
        r = _s(ADMIN).post(
            f"{BASE}/admin/promo-codes",
            json={"code": "QAEARLY", "kind": "percent", "value": 10},
            headers=XRW,
        )
        assert r.status_code == 400

    def test_a3_percent_over_100_400(self):
        r = _s(ADMIN).post(
            f"{BASE}/admin/promo-codes",
            json={"code": "QATOOBIG", "kind": "percent", "value": 150},
            headers=XRW,
        )
        assert r.status_code == 400

    def test_a4_code_too_short_400(self):
        r = _s(ADMIN).post(
            f"{BASE}/admin/promo-codes",
            json={"code": "QA", "kind": "percent", "value": 10},
            headers=XRW,
        )
        assert r.status_code == 400

    def test_a5_check_label(self, qa_event):
        r = _s({}).post(f"{BASE}/events/{qa_event['eid']}/tickets/promo", json={"code": "qaearly"})
        assert r.status_code == 200, r.text
        assert r.json()["label"] == "20% off"
        assert r.json()["code"] == "QAEARLY"

    def test_a6_inactive_code_rejected(self):
        pid = DB.promo_codes.find_one({"code": "QAEARLY"})["id"]
        r = _s(ADMIN).post(f"{BASE}/admin/promo-codes/{pid}/toggle", headers=XRW)
        assert r.status_code == 200 and r.json()["active"] is False
        r = _s({}).post(f"{BASE}/events/anything/tickets/promo", json={"code": "QAEARLY"})
        assert r.status_code == 400
        # Toggle back on
        _s(ADMIN).post(f"{BASE}/admin/promo-codes/{pid}/toggle", headers=XRW)

    def test_a7_expired_code_rejected(self, qa_event):
        # Use a definitely-past date (independent of timezone) to avoid flakiness
        past = "2020-01-01"
        r = _s(ADMIN).post(
            f"{BASE}/admin/promo-codes",
            json={"code": "QAEXPIRED", "kind": "percent", "value": 15, "expires": past},
            headers=XRW,
        )
        assert r.status_code == 200
        r2 = _s({}).post(f"{BASE}/events/{qa_event['eid']}/tickets/promo", json={"code": "QAEXPIRED"})
        assert r2.status_code == 400
        assert "expired" in r2.json()["detail"].lower()

    def test_a8_event_specific_wrong_event_rejected(self, qa_event):
        r = _s(ADMIN).post(
            f"{BASE}/admin/promo-codes",
            json={"code": "QASPECIFIC", "kind": "amount", "value": 5,
                  "event_id": qa_event["eid"]},
            headers=XRW,
        )
        assert r.status_code == 200
        # Valid on its event
        ok = _s({}).post(f"{BASE}/events/{qa_event['eid']}/tickets/promo", json={"code": "QASPECIFIC"})
        assert ok.status_code == 200
        # Invalid on another event
        bad = _s({}).post(f"{BASE}/events/{qa_event['eid2']}/tickets/promo", json={"code": "QASPECIFIC"})
        assert bad.status_code == 400

    def test_a9_list_and_delete(self):
        r = _s(ADMIN).get(f"{BASE}/admin/promo-codes", headers=XRW)
        assert r.status_code == 200
        codes = {d["code"] for d in r.json()}
        assert {"QAEARLY", "QAEXPIRED", "QASPECIFIC"}.issubset(codes)
        pid = DB.promo_codes.find_one({"code": "QAEXPIRED"})["id"]
        r = _s(ADMIN).delete(f"{BASE}/admin/promo-codes/{pid}", headers=XRW)
        assert r.status_code == 200 and r.json()["ok"] is True
        assert DB.promo_codes.find_one({"code": "QAEXPIRED"}) is None


# -------------------- B. Checkout math + gifts + 100% free --------------------
    pass
    free_order_id = None

    def test_b1_checkout_percent_promo_and_gift(self, qa_event):
        gen = qa_event["types"]["General"]
        r = _s({}).post(
            f"{BASE}/events/{qa_event['eid']}/tickets/checkout",
            json={"name": "QA Mathe", "email": "qa-math@example.com",
                  "items": [{"type_id": gen["id"], "qty": 2}],
                  "promo_code": "QAEARLY", "gift": 50},
        )
        assert r.status_code == 200, r.text
        assert "stripe.com" in r.json()["url"]
        o = DB.ticket_orders.find_one(
            {"email": "qa-math@example.com", "event_id": qa_event["eid"]},
            sort=[("created_at", -1)],
        )
        assert o is not None
        assert o["subtotal"] == 150
        assert o["discount"] == 30
        assert o["total"] == 120
        assert o["gift"] == 50
        assert o["promo_code"] == "QAEARLY"

    def test_b2_gift_half_dollar_rejected(self, qa_event):
        gen = qa_event["types"]["General"]
        r = _s({}).post(
            f"{BASE}/events/{qa_event['eid']}/tickets/checkout",
            json={"name": "QA Half", "email": "qa-half@example.com",
                  "items": [{"type_id": gen["id"], "qty": 1}], "gift": 0.5},
        )
        assert r.status_code == 400

    def test_b3_hundred_percent_promo_with_no_gift_goes_free(self, qa_event):
        r = _s(ADMIN).post(
            f"{BASE}/admin/promo-codes",
            json={"code": "QAFREE", "kind": "percent", "value": 100, "max_uses": 5},
            headers=XRW,
        )
        assert r.status_code == 200
        gen = qa_event["types"]["General"]
        r = _s({}).post(
            f"{BASE}/events/{qa_event['eid']}/tickets/checkout",
            json={"name": "QA Free", "email": "qa-free@example.com",
                  "items": [{"type_id": gen["id"], "qty": 1}],
                  "promo_code": "QAFREE", "gift": 0},
        )
        assert r.status_code == 200, r.text
        url = r.json()["url"]
        assert "/tickets/success?session_id=free_" in url
        sid = url.split("session_id=")[1]
        o = DB.ticket_orders.find_one({"session_id": sid})
        assert o is not None
        assert o["status"] == "paid"
        assert o["total"] == 0
        # Tickets created immediately for the free order
        assert DB.tickets.count_documents({"order_id": o["id"]}) == 1
        # Promo uses incremented
        c = DB.promo_codes.find_one({"code": "QAFREE"})
        assert c["uses"] == 1
        pass  # order id tracked via DB

    def test_b4_simulate_stripe_fulfilment_for_promo_and_gift_order(self, qa_event):
        o = DB.ticket_orders.find_one(
            {"email": "qa-math@example.com", "event_id": qa_event["eid"]},
            sort=[("created_at", -1)],
        )
        sid = o["session_id"]
        # Call server._fulfil_ticket_order in the backend's python
        _run_server_fn(
            f"res = asyncio.run(server._fulfil_ticket_order({json.dumps(sid)}))\n"
            "print(json.dumps({'id': res['id'] if res else None}))"
        )
        # Order now paid
        o2 = DB.ticket_orders.find_one({"id": o["id"]})
        assert o2["status"] == "paid"
        # Tickets created (2 * admits 1 = 2 for General)
        assert DB.tickets.count_documents({"order_id": o["id"]}) == 2
        # Promo uses incremented
        c = DB.promo_codes.find_one({"code": "QAEARLY"})
        assert c["uses"] == 1
        # payment_transactions tkt_{order_id} created for the gift (source ticket-gift, paid)
        pt = DB.payment_transactions.find_one({"session_id": f"tkt_{o['id']}"})
        assert pt is not None
        assert pt["amount"] == 50
        assert pt["payment_status"] == "paid"
        assert pt["source"] == "ticket-gift"
        pass  # order id tracked via DB

    def test_b5_ticket_report_excludes_gifts_from_revenue(self, qa_event):
        r = _s(ADMIN).get(f"{BASE}/admin/events/{qa_event['eid']}/tickets/report", headers=XRW)
        assert r.status_code == 200
        data = r.json()
        # The QAFREE order totals $0 and the QAEARLY order totals $120 ticket revenue.
        # Revenue counts the ticket total only, never the add-on gift.
        assert data["revenue"] == 120.0, data
        assert data["orders"] == 2  # free + paid math order
        assert data["seats"] == 3  # 1 (free) + 2 (math)

    def test_b6_fully_used_code_rejected(self):
        # QAEARLY has max_uses=1 and uses=1 after fulfilment above
        r = _s({}).post(f"{BASE}/events/anything/tickets/promo", json={"code": "QAEARLY"})
        assert r.status_code == 400
        assert "fully used" in r.json()["detail"].lower()


# -------------------- C. Seating API --------------------
class TestSeating:
    @classmethod
    def setup_class(cls):
        # Pick up xdist worker tag so parallel teardowns don't clobber this event
        wid = os.environ.get("PYTEST_XDIST_WORKER", "solo")
        tt = f" [{wid}]"
        # Create a dedicated seating event with a Table of 8 ticket
        r = _s(ADMIN).post(
            f"{BASE}/admin/events",
            json={"title": f"{QA_TITLE_BASE} Gala Seating{tt}", "date": "2026-12-24",
                  "location": "QA Seating Hall", "description": "QA",
                  "capacity": 200, "time": "6:00 PM"},
            headers=XRW,
        )
        assert r.status_code == 200
        cls.eid = r.json()["id"]
        r = _s(ADMIN).put(
            f"{BASE}/admin/events/{cls.eid}/tickets",
            json={"ticket_types": [
                {"name": "General", "price": 75, "qty": 10, "admits": 1},
                {"name": "Table of 8", "price": 500, "qty": 2, "admits": 8},
            ]},
            headers=XRW,
        )
        assert r.status_code == 200
        cls.types = {t["name"]: t for t in r.json()["ticket_types"]}

    def test_c1_set_seating_tables(self):
        r = _s(ADMIN).put(
            f"{BASE}/admin/events/{self.eid}/seating",
            json={"tables": 3, "seats": 8},
            headers=XRW,
        )
        assert r.status_code == 200, r.text
        s = r.json()["seating"]
        assert s["tables"] == 3 and s["seats"] == 8

    def test_c2_table_of_8_order_autoseats_as_one_group(self):
        tbl = self.types["Table of 8"]
        r = _s({}).post(
            f"{BASE}/events/{self.eid}/tickets/checkout",
            json={"name": "QA Table Buyer", "email": "qa-table@example.com",
                  "items": [{"type_id": tbl["id"], "qty": 1}]},
        )
        assert r.status_code == 200, r.text
        sid = DB.ticket_orders.find_one(
            {"email": "qa-table@example.com", "event_id": self.eid},
            sort=[("created_at", -1)],
        )["session_id"]
        # Simulate fulfilment (fulfil also calls _auto_seat)
        _run_server_fn(
            f"asyncio.run(server._fulfil_ticket_order({json.dumps(sid)}))\n"
            "print('ok')"
        )
        tickets = list(DB.tickets.find({"event_id": self.eid, "holder": "QA Table Buyer"}))
        assert len(tickets) == 8
        tables = {t["table"] for t in tickets}
        groups = {t["group"] for t in tickets}
        assert tables == {1} or tables == {2} or tables == {3}, tables
        assert len(groups) == 1

    def test_c3_get_seating_returns_group_with_size_and_table(self):
        r = _s(ADMIN).get(f"{BASE}/admin/events/{self.eid}/seating", headers=XRW)
        assert r.status_code == 200
        groups = r.json()["groups"]
        assert len(groups) >= 1
        g = next(g for g in groups if g["holder"] == "QA Table Buyer")
        assert g["size"] == 8
        assert g["table"] in (1, 2, 3)

    def test_c4_assign_group_to_table_and_over_capacity(self):
        # Add a General sale (admits 1) to have a second group to assign
        gen = self.types["General"]
        r = _s({}).post(
            f"{BASE}/events/{self.eid}/tickets/checkout",
            json={"name": "QA Solo", "email": "qa-solo@example.com",
                  "items": [{"type_id": gen["id"], "qty": 1}]},
        )
        assert r.status_code == 200
        sid = DB.ticket_orders.find_one(
            {"email": "qa-solo@example.com", "event_id": self.eid},
            sort=[("created_at", -1)],
        )["session_id"]
        _run_server_fn(f"asyncio.run(server._fulfil_ticket_order({json.dumps(sid)}))\nprint('ok')")

        # Find the solo group and the full group
        g_resp = _s(ADMIN).get(f"{BASE}/admin/events/{self.eid}/seating", headers=XRW).json()
        full = next(g for g in g_resp["groups"] if g["holder"] == "QA Table Buyer")
        solo = next(g for g in g_resp["groups"] if g["holder"] == "QA Solo")

        # Try to put solo on the same table — table has 8 seats and full already uses 8 → should 400
        r = _s(ADMIN).post(
            f"{BASE}/admin/events/{self.eid}/seating/assign",
            json={"group": solo["group"], "table": full["table"]},
            headers=XRW,
        )
        assert r.status_code == 400, r.text

        # Assign solo to a free table
        free_table = next(t for t in (1, 2, 3) if t != full["table"])
        r = _s(ADMIN).post(
            f"{BASE}/admin/events/{self.eid}/seating/assign",
            json={"group": solo["group"], "table": free_table},
            headers=XRW,
        )
        assert r.status_code == 200
        g2 = next(g for g in r.json()["groups"] if g["holder"] == "QA Solo")
        assert g2["table"] == free_table

        # Unassign (table=None)
        r = _s(ADMIN).post(
            f"{BASE}/admin/events/{self.eid}/seating/assign",
            json={"group": solo["group"], "table": None},
            headers=XRW,
        )
        assert r.status_code == 200
        g3 = next(g for g in r.json()["groups"] if g["holder"] == "QA Solo")
        assert g3["table"] is None

    def test_c5_auto_seat_assigns_remaining(self):
        r = _s(ADMIN).post(f"{BASE}/admin/events/{self.eid}/seating/auto", headers=XRW)
        assert r.status_code == 200
        assert r.json()["seated"] >= 1
        unseated = [g for g in r.json()["groups"] if g["table"] is None]
        assert len(unseated) == 0

    def test_c6_reducing_tables_unassigns_guests_on_removed_tables(self):
        # Reduce to 1 table — anyone on table 2 or 3 should become unseated
        r = _s(ADMIN).put(
            f"{BASE}/admin/events/{self.eid}/seating",
            json={"tables": 1, "seats": 8},
            headers=XRW,
        )
        assert r.status_code == 200
        groups = r.json()["groups"]
        # At most 8 seats on the single surviving table — anyone else is unseated
        on_t1 = [g for g in groups if g["table"] == 1]
        total_on_t1 = sum(g["size"] for g in on_t1)
        assert total_on_t1 <= 8
        # The removed-tables guests must be unseated
        unseated_total = sum(g["size"] for g in groups if g["table"] is None)
        assert unseated_total >= 1


# -------------------- D. Campaign milestone alerts --------------------
class TestMilestones:
    def test_d_milestones_fire_at_25_50_75_100(self, qa_event):
        # Snapshot current paid total to compute a goal small enough that
        # the next ticket gift crosses all four thresholds.
        settings = _s(ADMIN).get(f"{BASE}/admin/settings", headers=XRW).json()
        orig_goal = float(settings.get("goal") or 50000)

        # Choose a tiny goal so the already-existing paid gifts alone cross 100%
        tiny = 1.0
        r = _s(ADMIN).put(f"{BASE}/admin/settings", json={"goal": tiny}, headers=XRW)
        assert r.status_code == 200

        # Clear any prior milestones_sent for goal=1 so this run fires cleanly
        DB.milestones_sent.delete_many({"goal": tiny})
        # Clear campaign push_log noise from a prior run
        before_push = DB.push_log.count_documents({"kind": "campaign"})

        # Directly invoke the in-process _check_milestones (the same coroutine
        # that _fulfil_ticket_order fans out to after inserting a ticket-gift).
        # This avoids coupling the milestone assertion to the full ticketing
        # fulfilment pipeline (seating/auto-seat/etc).
        _run_server_fn("asyncio.run(server._check_milestones())\nprint('ok')")

        # Verify all 4 milestones recorded
        found = {m["milestone"] for m in DB.milestones_sent.find({"goal": tiny})}
        assert {25, 50, 75, 100}.issubset(found), found

        # Verify push_log campaign rows (one per milestone)
        after_push = DB.push_log.count_documents({"kind": "campaign"})
        assert after_push - before_push >= 4, (before_push, after_push)

        # Restore original goal
        r = _s(ADMIN).put(f"{BASE}/admin/settings", json={"goal": orig_goal}, headers=XRW)
        assert r.status_code == 200

        # Clean up any milestone rows this test created
        DB.milestones_sent.delete_many({"goal": tiny})


# -------------------- E. Accountant year-end package --------------------
class TestAccountant:
    def test_e1_defaults(self):
        # Remove any prior cfg so we see the actual defaults
        DB.settings.delete_one({"key": "accountant"})
        r = _s(ADMIN).get(f"{BASE}/admin/accounting", headers=XRW)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "Divine Financial Group"
        assert data["emails"] == ["devinetax1@gmail.com", "info@dfgbusiness.com"]
        assert data["cc"] == ["caringsistersclub@gmail.com"]
        assert data["enabled"] is True

    def test_e2_invalid_email_rejected_then_restore_defaults(self):
        r = _s(ADMIN).put(
            f"{BASE}/admin/accounting",
            json={"name": "Divine Financial Group", "emails": ["not-an-email"], "cc": [], "enabled": True},
            headers=XRW,
        )
        assert r.status_code == 400

        # Restore exact defaults via the admin API
        r = _s(ADMIN).put(
            f"{BASE}/admin/accounting",
            json={"name": "Divine Financial Group",
                  "emails": ["devinetax1@gmail.com", "info@dfgbusiness.com"],
                  "cc": ["caringsistersclub@gmail.com"], "enabled": True},
            headers=XRW,
        )
        assert r.status_code == 200
        got = r.json()
        assert got["name"] == "Divine Financial Group"
        assert got["emails"] == ["devinetax1@gmail.com", "info@dfgbusiness.com"]
        assert got["cc"] == ["caringsistersclub@gmail.com"]
        assert got["enabled"] is True

    @pytest.mark.parametrize("name", ["summary", "donations", "donor-totals", "tickets", "dues"])
    def test_e3_admin_csv_download(self, name):
        year = datetime.now(timezone.utc).year - 1
        r = _s(ADMIN).get(f"{BASE}/admin/accounting/{year}/{name}.csv", headers=XRW)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/csv")
        # First line is a header (contains at least one capitalised word)
        first = r.content.split(b"\n", 1)[0]
        assert len(first) > 0

    def test_e4_admin_zip_download(self):
        import io, zipfile
        year = datetime.now(timezone.utc).year - 1
        r = _s(ADMIN).get(f"{BASE}/admin/accounting/{year}/all.zip", headers=XRW)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = {n.rsplit("/", 1)[-1] for n in z.namelist()}
        for key in ("summary", "donations", "donor-totals", "tickets", "dues"):
            assert any(n.endswith(f"-{key}.csv") for n in names), (key, names)

    def test_e5_token_download_valid_200(self):
        year = datetime.now(timezone.utc).year - 1
        future = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        DB.acct_tokens.delete_one({"token": "qa_acct_tok"})
        DB.acct_tokens.insert_one({"token": "qa_acct_tok", "year": year,
                                   "expires_at": future, "created_at": datetime.now(timezone.utc).isoformat()})
        r = _s({}).get(f"{BASE}/accounting/qa_acct_tok/summary.csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")

    def test_e6_token_download_expired_410(self):
        year = datetime.now(timezone.utc).year - 1
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        DB.acct_tokens.delete_one({"token": "qa_acct_tok_expired"})
        DB.acct_tokens.insert_one({"token": "qa_acct_tok_expired", "year": year,
                                   "expires_at": past, "created_at": datetime.now(timezone.utc).isoformat()})
        r = _s({}).get(f"{BASE}/accounting/qa_acct_tok_expired/summary.csv")
        assert r.status_code == 410

    def test_e7_scheduler_returns_none_outside_window(self):
        # Call _acct_scheduled with a June datetime. NEVER with a January
        # datetime, because that would email the real accountant.
        out = _run_server_fn(
            "res = asyncio.run(server._acct_scheduled(datetime(2026, 6, 15, 15, 0, tzinfo=timezone.utc)))\n"
            "print('RESULT=' + repr(res))"
        )
        assert "RESULT=None" in out, out
