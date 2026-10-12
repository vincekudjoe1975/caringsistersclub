"""Iter 46 — Paddle raise, sponsors, gala thank-you, silent auction."""
import os
import io
import sys
import uuid
import asyncio
import struct
import zlib
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
MONGO = MongoClient(os.environ['MONGO_URL'])
DB = MONGO[os.environ['DB_NAME']]
COOKIES = {"session_token": "qa_tok_123"}
HEADERS = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}


def _png_bytes(w=4, h=4):
    """Return a minimal valid PNG (4x4 red)."""
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(h):
        raw += b"\x00" + (b"\xff\x00\x00") * w
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(scope="module")
def eid():
    """Create a fresh QA Gala event for iter 46 tests."""
    import datetime
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    # Future date so we can tweak later
    eid = str(uuid.uuid4())
    DB.events.insert_one({
        "id": eid, "title": f"QA Iter46 Gala {uuid.uuid4().hex[:6]}",
        "date": yesterday,  # Day was yesterday so thank-you logic can trigger
        "time": "6:00 PM", "location": "Online", "slug": f"qa-iter46-{eid[:8]}",
        "description": "QA iter46", "status": "published", "created_at": "2026-01-01T00:00:00Z",
    })
    yield eid
    # Cleanup
    DB.events.delete_one({"id": eid})
    DB.paddle_pledges.delete_many({"event_id": eid})
    DB.auction_items.delete_many({"event_id": eid})
    DB.auction_bids.delete_many({"event_id": eid})
    DB.auction_bidders.delete_many({"event_id": eid})
    DB.auction_wins.delete_many({"event_id": eid})
    DB.payment_transactions.delete_many({"event_id": eid})
    DB.ticket_orders.delete_many({"event_id": eid})
    DB.push_marks.delete_many({"key": {"$regex": f"gala-thanks:{eid}"}})
    DB.push_marks.delete_many({"key": {"$regex": f"^gala-thanks:{eid}"}})
    # push_marks collection may actually be named differently; try scheduled_marks
    for coll in ("push_marks", "scheduled_marks", "scheduled", "marks"):
        try:
            DB[coll].delete_many({"key": {"$regex": f"gala-thanks:{eid}"}})
        except Exception:
            pass


# ─── Paddle ───
class TestPaddle:
    def test_level_set_pledge_tally(self, eid):
        # Set level 500
        r = requests.put(f"{BASE}/api/admin/events/{eid}/paddle", json={"level": 500},
                         cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200, r.text
        assert r.json()["level"] == 500

        # Invalid level 0
        r = requests.put(f"{BASE}/api/admin/events/{eid}/paddle", json={"level": 0},
                         cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 400

        # Bad email
        r = requests.post(f"{BASE}/api/admin/events/{eid}/paddle/pledge",
                          json={"level": 500, "name": "Bad", "email": "notanemail", "number": ""},
                          cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 400

        # Two pledges
        for name in ("Ann QA", "Bea QA"):
            r = requests.post(f"{BASE}/api/admin/events/{eid}/paddle/pledge",
                              json={"level": 500, "name": name, "email": f"{name.split()[0].lower()}@example.com", "number": "7"},
                              cookies=COOKIES, headers=HEADERS)
            assert r.status_code == 200, r.text
        d = r.json()
        assert d["total"] == 1000
        assert d["tally"] == [{"level": 500.0, "count": 2}]
        assert len(d["pledges"]) == 2

        # Gala screen reflects paddle
        r = requests.get(f"{BASE}/api/gala/{eid}")
        assert r.status_code == 200
        g = r.json()
        assert g["raised"] >= 1000
        assert g["paddle"]["level"] == 500
        assert g["paddle"]["total"] == 1000

        # Undo one
        pid = d["pledges"][0]["id"]
        r = requests.delete(f"{BASE}/api/admin/events/{eid}/paddle/pledge/{pid}",
                            cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["total"] == 500

        # Toggle collected
        pid2 = r.json()["pledges"][0]["id"]
        r = requests.post(f"{BASE}/api/admin/events/{eid}/paddle/pledge/{pid2}/collected",
                          cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200
        assert any(p["id"] == pid2 and p["collected"] for p in r.json()["pledges"])

        # Level=null hides
        r = requests.put(f"{BASE}/api/admin/events/{eid}/paddle", json={"level": None},
                         cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["level"] is None


# ─── Sponsors ───
class TestSponsors:
    def test_upload_delete_sponsor(self, eid):
        png = _png_bytes()
        r = requests.post(f"{BASE}/api/admin/events/{eid}/sponsors",
                          data={"name": "QA Sponsor", "table": 2},
                          files={"file": ("logo.png", png, "image/png")},
                          cookies=COOKIES, headers={"X-Requested-With": "XMLHttpRequest"})
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        assert r.json()["name"] == "QA Sponsor"
        assert r.json()["table"] == 2

        # Non-image
        r2 = requests.post(f"{BASE}/api/admin/events/{eid}/sponsors",
                           data={"name": "QA Bad", "table": 0},
                           files={"file": ("bad.txt", b"hello", "text/plain")},
                           cookies=COOKIES, headers={"X-Requested-With": "XMLHttpRequest"})
        assert r2.status_code == 400, r2.text

        # In gala screen
        g = requests.get(f"{BASE}/api/gala/{eid}").json()
        assert any(s["name"] == "QA Sponsor" for s in g["sponsors"])

        # In seating
        s = requests.get(f"{BASE}/api/admin/events/{eid}/seating",
                        cookies=COOKIES, headers=HEADERS)
        assert s.status_code == 200
        assert any(x["name"] == "QA Sponsor" for x in (s.json().get("sponsors") or []))

        # Delete
        d = requests.delete(f"{BASE}/api/admin/events/{eid}/sponsors/{sid}",
                            cookies=COOKIES, headers=HEADERS)
        assert d.status_code == 200
        g2 = requests.get(f"{BASE}/api/gala/{eid}").json()
        assert not any(s["id"] == sid for s in g2.get("sponsors", []) if "id" in s)


# ─── Thank-you ───
class TestThanks:
    def test_recipients_and_toggle(self, eid):
        # From TestPaddle we already have 1 pledge w/ email
        r = requests.get(f"{BASE}/api/admin/events/{eid}/gala-thanks",
                         cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200
        d = r.json()
        assert d["recipients"] >= 1
        assert "Thank you" in d["html"]
        assert d["enabled"] in (True, False)

        # Toggle false
        r = requests.put(f"{BASE}/api/admin/events/{eid}/gala-thanks",
                         json={"enabled": False}, cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200 and r.json()["enabled"] is False
        d2 = requests.get(f"{BASE}/api/admin/events/{eid}/gala-thanks",
                          cookies=COOKIES, headers=HEADERS).json()
        assert d2["enabled"] is False

        # Flip back on and call _gala_thanks at 10am ET on event date + 1 day
        requests.put(f"{BASE}/api/admin/events/{eid}/gala-thanks",
                     json={"enabled": True}, cookies=COOKIES, headers=HEADERS)

        # Set event date to a known day so thanks loop fires
        import datetime
        target_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        DB.events.update_one({"id": eid}, {"$set": {"date": target_date, "gala_thanks": True}})

        # Call server._gala_thanks in-process via subprocess
        import subprocess
        code = f"""
import asyncio, sys, os, datetime
sys.path.insert(0, '/app/backend')
os.environ['DISABLE_SCHEDULER']='1'
import server
async def main():
    now = datetime.datetime.combine(datetime.date.fromisoformat('{target_date}') + datetime.timedelta(days=1), datetime.time(10,0), tzinfo=server.EVENT_TZ).astimezone(datetime.timezone.utc)
    n1 = await server._gala_thanks(now)
    n2 = await server._gala_thanks(now)  # marker should prevent re-send
    print('N1', n1, 'N2', n2)
    # Toggle off and retry (should be 0 after turning off, mark also present now)
    await server.db.events.update_one({{'id':'{eid}'}}, {{'$set':{{'gala_thanks':False}}}})
    # Clear mark to prove disabled gating alone
    for coll in ('push_marks','scheduled_marks','scheduled','marks'):
        try:
            await server.db[coll].delete_many({{'key': 'gala-thanks:{eid}'}})
        except Exception as e:
            pass
    n3 = await server._gala_thanks(now)
    print('N3', n3)
asyncio.run(main())
"""
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        print("STDOUT:", p.stdout)
        print("STDERR:", p.stderr[-500:])
        assert "N1" in p.stdout
        # Parse
        line = [l for l in p.stdout.splitlines() if l.startswith("N1")][0]
        parts = dict(zip(line.split()[::2], line.split()[1::2]))
        # First call sends >=1 email (at least for the paddle pledge w/ email)
        assert int(parts["N1"]) >= 1
        # Second call must be 0 (marker set)
        assert int(parts["N2"]) == 0
        line3 = [l for l in p.stdout.splitlines() if l.startswith("N3")][0]
        # gala_thanks=False -> 0 even after clearing marker
        assert int(line3.split()[1]) == 0


# ─── Auction ───
class TestAuction:
    def test_full_flow(self, eid):
        # Add item (bidding before open)
        r = requests.post(f"{BASE}/api/admin/events/{eid}/auction/items",
                          json={"title": "QA Lot", "description": "desc", "value": 100,
                                "start_bid": 50, "min_raise": 10},
                          cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200, r.text
        iid = r.json()["id"]

        # Bid before open -> 400
        reg = requests.post(f"{BASE}/api/auction/{eid}/register",
                            json={"name": "A", "email": "a@example.com", "phone": "5551112222"})
        # Register not possible on an unopened auction? auction_register doesn't need open; it just needs event
        assert reg.status_code == 200
        tok_a = reg.json()["token"]
        rb = requests.post(f"{BASE}/api/auction/{eid}/items/{iid}/bid",
                           json={"token": tok_a, "amount": 50})
        assert rb.status_code == 400

        # closes_at in past -> 400
        rc = requests.put(f"{BASE}/api/admin/events/{eid}/auction",
                          json={"closes_at": "2020-01-01T10:00"}, cookies=COOKIES, headers=HEADERS)
        assert rc.status_code == 400

        # Open with future time
        rc = requests.put(f"{BASE}/api/admin/events/{eid}/auction",
                          json={"closes_at": "2099-12-12T20:00"}, cookies=COOKIES, headers=HEADERS)
        assert rc.status_code == 200, rc.text
        assert rc.json()["state"] == "open"

        # Register missing phone
        r1 = requests.post(f"{BASE}/api/auction/{eid}/register",
                           json={"name": "X", "email": "x@example.com", "phone": ""})
        assert r1.status_code == 400

        # Same email again -> same token
        reg2 = requests.post(f"{BASE}/api/auction/{eid}/register",
                             json={"name": "A updated", "email": "a@example.com", "phone": "5551112222"})
        assert reg2.status_code == 200
        assert reg2.json()["token"] == tok_a

        # Bid 40 -> 400 (below start)
        rb = requests.post(f"{BASE}/api/auction/{eid}/items/{iid}/bid",
                           json={"token": tok_a, "amount": 40})
        assert rb.status_code == 400

        # Bid 50 ok
        rb = requests.post(f"{BASE}/api/auction/{eid}/items/{iid}/bid",
                           json={"token": tok_a, "amount": 50})
        assert rb.status_code == 200, rb.text

        # Same bidder again -> "already highest"
        rb = requests.post(f"{BASE}/api/auction/{eid}/items/{iid}/bid",
                           json={"token": tok_a, "amount": 60})
        assert rb.status_code == 400
        assert "highest" in rb.json()["detail"].lower()

        # Register second bidder
        reg_b = requests.post(f"{BASE}/api/auction/{eid}/register",
                              json={"name": "B QA", "email": "b_qa@example.com", "phone": "5553334444"})
        assert reg_b.status_code == 200
        tok_b = reg_b.json()["token"]

        # Bid 55 -> below min (50 + 10 = 60)
        rb = requests.post(f"{BASE}/api/auction/{eid}/items/{iid}/bid",
                           json={"token": tok_b, "amount": 55})
        assert rb.status_code == 400

        # Bid 60 ok
        rb = requests.post(f"{BASE}/api/auction/{eid}/items/{iid}/bid",
                           json={"token": tok_b, "amount": 60})
        assert rb.status_code == 200

        # A view -> outbid
        va = requests.get(f"{BASE}/api/auction/{eid}", params={"token": tok_a}).json()
        it = [x for x in va["items"] if x["id"] == iid][0]
        assert it["outbid"] is True
        assert it["mine"] is False

        # B view -> mine
        vb = requests.get(f"{BASE}/api/auction/{eid}", params={"token": tok_b}).json()
        it = [x for x in vb["items"] if x["id"] == iid][0]
        assert it["mine"] is True

        # Delete item with bids -> 400
        rd = requests.delete(f"{BASE}/api/admin/events/{eid}/auction/items/{iid}",
                             cookies=COOKIES, headers=HEADERS)
        assert rd.status_code == 400

        # Close now
        rcl = requests.post(f"{BASE}/api/admin/events/{eid}/auction/close",
                            cookies=COOKIES, headers=HEADERS)
        assert rcl.status_code == 200
        assert rcl.json()["winners"] == 1

        # Auction_wins row for B
        wins = list(DB.auction_wins.find({"event_id": eid}, {"_id": 0}))
        assert len(wins) == 1
        tok_w = wins[0]["token"]

        # GET /api/auction/pay/{tok} unpaid
        rw = requests.get(f"{BASE}/api/auction/pay/{tok_w}")
        assert rw.status_code == 200 and rw.json()["status"] == "unpaid"

        # POST pay -> stripe url (test mode)
        rp = requests.post(f"{BASE}/api/auction/pay/{tok_w}")
        if rp.status_code == 200:
            assert "url" in rp.json()
            # simulate paid in-process
            import subprocess
            code = f"""
import asyncio, sys
sys.path.insert(0, '/app/backend')
import server
async def main():
    w = await server.db.auction_wins.find_one({{'token':'{tok_w}'}}, {{'_id':0}})
    sid = w.get('session_id')
    print('SID', sid)
    if sid:
        await server._auction_paid(sid)
asyncio.run(main())
"""
            subprocess.run([sys.executable, "-c", code], check=True, timeout=30)
            rw2 = requests.get(f"{BASE}/api/auction/pay/{tok_w}")
            assert rw2.json()["status"] == "paid"
        else:
            print(f"Stripe not configured in preview env: {rp.status_code} {rp.text[:200]}")

        # Bidding after close -> 400
        rb = requests.post(f"{BASE}/api/auction/{eid}/items/{iid}/bid",
                           json={"token": tok_a, "amount": 100})
        assert rb.status_code == 400

        # CSV
        rc = requests.get(f"{BASE}/api/admin/events/{eid}/auction.csv",
                          cookies=COOKIES, headers=HEADERS)
        assert rc.status_code == 200
        assert "text/csv" in rc.headers.get("content-type", "")
        assert b"QA Lot" in rc.content


# ─── Regression ───
class TestRegression:
    def test_gala_screen_goal_raised(self, eid):
        # Set goal
        r = requests.put(f"{BASE}/api/admin/events/{eid}/gala",
                         json={"goal": 2000}, cookies=COOKIES, headers=HEADERS)
        assert r.status_code == 200
        g = requests.get(f"{BASE}/api/gala/{eid}").json()
        assert g["goal"] == 2000
        assert g["raised"] >= 0
        assert "count" in g
