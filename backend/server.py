from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# ---------- Emergent Google Auth + File/Media Storage ----------
import requests as _requests
from fastapi import Request, Response, HTTPException, UploadFile, File, Form, Depends, Header, Query
from typing import Optional
from datetime import timedelta

# ---- Emergent Object Storage config ----
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "caring-sisters-club"
_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = _requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = _requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = _requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = _requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = _requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
ALLOWED_CATEGORIES = {"gallery", "board", "document", "event"}


class SessionRequest(BaseModel):
    session_id: str


async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.user_sessions.delete_one({"session_token": token})
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(request: Request):
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user



@api_router.post("/auth/session")
async def auth_session(payload: SessionRequest, response: Response):
    try:
        r = _requests.get(
            EMERGENT_SESSION_URL,
            headers={"X-Session-ID": payload.session_id},
            timeout=15,
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Auth service unreachable")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = r.json()
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="No email returned")
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data.get("name"), "picture": data.get("picture")}},
        )
    else:
        # Self-bootstrapping allowlist:
        # - First ever user becomes the owner/admin.
        # - A pre-approved email (allowed_emails) becomes admin.
        # - Everyone else is 'pending' until an admin approves them.
        admin_count = await db.users.count_documents({"role": "admin"})
        preapproved = await db.allowed_emails.find_one({"email": email.lower()})
        role = "admin" if (admin_count == 0 or preapproved) else "pending"
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": data.get("name"),
            "picture": data.get("picture"),
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    session_token = data.get("session_token")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie(
        key="session_token", value=session_token, httponly=True,
        secure=True, samesite="none", max_age=7 * 24 * 60 * 60, path="/",
    )
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user


@api_router.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out"}


def _media_url(item_id: str) -> str:
    return f"/api/media/file/{item_id}"


@api_router.post("/media")
async def upload_media(
    file: UploadFile = File(...),
    category: str = Form(...),
    title: Optional[str] = Form(None),
    subtitle: Optional[str] = Form(None),
    user=Depends(require_admin),
):
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    item_id = str(uuid.uuid4())
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    storage_path = f"{APP_NAME}/{category}/{item_id}.{ext}"
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    try:
        result = put_object(storage_path, data, content_type)
    except Exception as e:
        logging.error(f"Storage upload failed: {e}")
        raise HTTPException(status_code=502, detail="File storage upload failed")
    doc = {
        "id": item_id,
        "category": category,
        "storage_path": result.get("path", storage_path),
        "original_name": file.filename,
        "content_type": content_type,
        "title": title,
        "subtitle": subtitle,
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": user["email"],
    }
    await db.media.insert_one(doc)
    doc.pop("_id", None)
    doc["url"] = _media_url(item_id)
    return doc


@api_router.get("/media")
async def list_media(category: Optional[str] = None):
    query = {"is_deleted": {"$ne": True}}
    if category:
        query["category"] = category
    items = await db.media.find(query, {"_id": 0}).sort("uploaded_at", -1).to_list(500)
    for it in items:
        it["url"] = _media_url(it["id"])
    return items


@api_router.get("/media/file/{item_id}")
async def get_media_file(item_id: str):
    item = await db.media.find_one({"id": item_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    data, content_type = None, None
    try:
        data, content_type = get_object(item["storage_path"])
    except Exception as e:
        logging.error(f"Storage fetch failed: {e}")
        raise HTTPException(status_code=404, detail="File missing")
    return Response(content=data, media_type=item.get("content_type", content_type))


@api_router.delete("/media/{item_id}")
async def delete_media(item_id: str, user=Depends(require_admin)):
    item = await db.media.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await db.media.update_one({"id": item_id}, {"$set": {"is_deleted": True}})
    return {"message": "Deleted"}


# ---------- Stripe Donations (Flow A - claimable sandbox) ----------
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
DONATION_MIN = 1.0
DONATION_MAX = 100000.0


class DonationCheckout(BaseModel):
    amount: float
    frequency: str = "one-time"  # or "monthly"
    donor_name: Optional[str] = None
    donor_email: Optional[str] = None
    anonymous: bool = False
    origin_url: str


def _validate_donation_amount(amount: float) -> float:
    amount = float(amount)
    if amount < DONATION_MIN or amount > DONATION_MAX:
        raise HTTPException(status_code=400, detail="Invalid donation amount")
    return amount


def _build_donation_price_data(amount: float, monthly: bool) -> dict:
    price_data = {
        "currency": "usd",
        "product_data": {"name": "Monthly Donation" if monthly else "One-Time Donation"},
        "unit_amount": int(round(amount * 100)),
    }
    if monthly:
        price_data["recurring"] = {"interval": "month"}
    return price_data


def _create_stripe_donation_session(req: "DonationCheckout", amount: float, monthly: bool):
    try:
        return stripe.checkout.Session.create(
            line_items=[{"price_data": _build_donation_price_data(amount, monthly), "quantity": 1}],
            mode="subscription" if monthly else "payment",
            success_url=f"{req.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{req.origin_url}/donate",
            metadata={
                "amount": str(amount),
                "frequency": req.frequency,
                "donor_name": req.donor_name or "",
                "donor_email": req.donor_email or "",
                "kind": "donation",
            },
        )
    except Exception as e:
        logging.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=502, detail="Could not create checkout session")


@api_router.post("/payments/checkout")
async def create_donation_checkout(req: DonationCheckout):
    amount = _validate_donation_amount(req.amount)
    monthly = req.frequency == "monthly"
    session = _create_stripe_donation_session(req, amount, monthly)
    now = datetime.now(timezone.utc).isoformat()
    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "amount": amount,
        "currency": "usd",
        "frequency": req.frequency,
        "donor_name": req.donor_name or "",
        "donor_email": req.donor_email or "",
        "anonymous": bool(req.anonymous),
        "status": "initiated",
        "payment_status": "pending",
        "created_at": now,
        "updated_at": now,
    })
    return {"checkout_url": session.url, "session_id": session.id}


async def _record_paid_donation(session_id: str, txn: dict, recipient_email: str = None):
    """Insert a donation submission once, and send a receipt email."""
    existing = await db.submissions.find_one({"data.session_id": session_id})
    if existing:
        return
    donor_email = (recipient_email or txn.get("donor_email") or "").strip()
    donor_name = (txn.get("donor_name") or "").strip() or "Friend"
    await db.submissions.insert_one({
        "id": str(uuid.uuid4()),
        "type": "donation",
        "data": {
            "name": txn.get("donor_name") or "Anonymous",
            "email": donor_email,
            "amount": f"${txn.get('amount')}",
            "frequency": txn.get("frequency"),
            "status": "Paid",
            "session_id": session_id,
        },
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    if donor_email:
        html = _receipt_html(donor_name, txn.get("amount"), txn.get("frequency"))
        await send_email(
            to=donor_email,
            subject="Thank you for your gift to The Caring Sisters Club",
            html=html,
        )


@api_router.get("/payments/status/{session_id}")
async def donation_status(session_id: str):
    record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if record.get("payment_status") != "paid":
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {
                        "status": "completed",
                        "payment_status": "paid",
                        "stripe_subscription_id": s.get("subscription"),
                        "stripe_payment_intent_id": s.get("payment_intent"),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
                cust_email = (s.get("customer_details") or {}).get("email")
                await _record_paid_donation(session_id, record, recipient_email=cust_email)
        except Exception as e:
            logging.warning(f"Stripe status check failed: {e}")
    return {
        "session_id": record["session_id"],
        "status": record["status"],
        "payment_status": record["payment_status"],
        "amount": record.get("amount"),
        "frequency": record.get("frequency"),
    }


@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")
    obj, t = event["data"]["object"], event["type"]
    if t == "checkout.session.completed":
        await db.payment_transactions.update_one(
            {"session_id": obj["id"], "payment_status": {"$ne": "paid"}},
            {"$set": {
                "status": "completed",
                "payment_status": obj.get("payment_status", "paid"),
                "stripe_subscription_id": obj.get("subscription"),
                "stripe_payment_intent_id": obj.get("payment_intent"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        txn = await db.payment_transactions.find_one({"session_id": obj["id"]}, {"_id": 0})
        if txn:
            cust_email = (obj.get("customer_details") or {}).get("email")
            await _record_paid_donation(obj["id"], txn, recipient_email=cust_email)
    elif t == "checkout.session.expired":
        await db.payment_transactions.update_one(
            {"session_id": obj["id"]},
            {"$set": {"status": "expired", "payment_status": "expired", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    elif t == "invoice.payment_succeeded":
        # Recurring monthly donation renewal (skip the first invoice of a new subscription)
        if obj.get("billing_reason") == "subscription_cycle":
            await _handle_recurring_renewal(obj)
    return {"status": "ok"}


async def _handle_recurring_renewal(invoice: dict):
    renewal_id = invoice.get("id")
    if not renewal_id:
        return
    if await db.payment_transactions.find_one({"session_id": renewal_id}):
        return  # already processed
    sub_id = invoice.get("subscription")
    orig = await db.payment_transactions.find_one(
        {"stripe_subscription_id": sub_id}, {"_id": 0}
    ) if sub_id else None
    email = invoice.get("customer_email") or (orig.get("donor_email") if orig else "")
    amount = float(invoice.get("amount_paid") or 0) / 100.0
    now = datetime.now(timezone.utc).isoformat()
    txn = {
        "session_id": renewal_id,
        "amount": amount,
        "currency": "usd",
        "frequency": "monthly",
        "donor_name": (orig.get("donor_name") if orig else "") or "",
        "donor_email": email or "",
        "anonymous": bool(orig.get("anonymous")) if orig else False,
        "status": "completed",
        "payment_status": "paid",
        "stripe_subscription_id": sub_id,
        "is_renewal": True,
        "created_at": now,
        "updated_at": now,
    }
    await db.payment_transactions.insert_one(txn)
    if email:
        donor_name = (txn["donor_name"] or "").strip() or "Friend"
        html = _receipt_html(donor_name, amount, "monthly")
        await send_email(
            to=email,
            subject="Your recurring gift to The Caring Sisters Club",
            html=html,
        )


# ---------- Form Submissions (public create, admin manage) ----------
ALLOWED_SUB_TYPES = {"volunteer", "member", "contact", "rsvp", "donation"}


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str


@api_router.post("/submissions")
async def create_submission(payload: SubmissionCreate):
    data = payload.model_dump()
    stype = data.get("type")
    if stype not in ALLOWED_SUB_TYPES:
        raise HTTPException(status_code=400, detail="Invalid submission type")
    doc = {
        "id": str(uuid.uuid4()),
        "type": stype,
        "data": {k: v for k, v in data.items() if k != "type"},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.submissions.insert_one(doc)
    return {"id": doc["id"], "message": "Received"}


@api_router.get("/submissions")
async def list_submissions(type: Optional[str] = None, user=Depends(require_admin)):
    query = {}
    if type:
        query["type"] = type
    items = await db.submissions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


@api_router.get("/submissions/counts")
async def submission_counts(user=Depends(require_admin)):
    out = {}
    for t in ALLOWED_SUB_TYPES:
        total = await db.submissions.count_documents({"type": t})
        unread = await db.submissions.count_documents({"type": t, "read": False})
        out[t] = {"total": total, "unread": unread}
    return out


@api_router.patch("/submissions/{item_id}/read")
async def mark_submission_read(item_id: str, user=Depends(require_admin)):
    await db.submissions.update_one({"id": item_id}, {"$set": {"read": True}})
    return {"message": "ok"}


@api_router.delete("/submissions/{item_id}")
async def delete_submission(item_id: str, user=Depends(require_admin)):
    await db.submissions.delete_one({"id": item_id})
    return {"message": "Deleted"}


# ---------- Email (Emergent-managed Resend) ----------
import re
import httpx
from html import escape as _esc
from html.parser import HTMLParser
from urllib.parse import urlparse
import ipaddress

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "The Caring Sisters Club")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan(); scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str, reply_to: str = None):
    if not EMAIL_KEY:
        logging.warning("EMERGENT_EMAIL_KEY not set; skipping email send")
        return None
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if reply_to or EMAIL_REPLY_TO:
        payload["contact_email"] = reply_to or EMAIL_REPLY_TO
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json=payload,
            )
        resp.raise_for_status()
        return resp.json().get("id")
    except Exception as e:
        logging.error(f"Email send error: {e}")
        return None


def _receipt_html(name: str, amount, frequency: str) -> str:
    freq_txt = "monthly" if frequency == "monthly" else "one-time"
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0">'
        '<tr><td align="center" style="padding:28px 16px;font-family:Georgia,\'Times New Roman\',serif">'
        '<table role="presentation" width="600" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden">'
        '<tr><td style="background:#3B0A2E;padding:28px 32px;color:#F7EFE9">'
        '<div style="font-size:20px;font-weight:bold;letter-spacing:1px">The Caring Sisters Club</div>'
        '<div style="font-size:11px;color:#CBA24B;letter-spacing:3px;text-transform:uppercase;margin-top:4px">Love &middot; Respect &middot; Empowerment</div>'
        '</td></tr>'
        '<tr><td style="padding:32px;font-family:Arial,Helvetica,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 16px">Thank you, {_esc(name)}!</h1>'
        f'<p style="font-size:15px;line-height:1.6;color:#4a3340;margin:0 0 16px">Your generosity fuels professional empowerment, housing support, and community care for women across the Diaspora. We are deeply grateful for your {freq_txt} gift.</p>'
        '<table role="presentation" width="100%" style="background:#faf2f7;border-radius:12px;margin:8px 0 20px">'
        f'<tr><td style="padding:18px 22px;font-size:14px;color:#3B0A2E">Gift amount</td>'
        f'<td align="right" style="padding:18px 22px;font-size:20px;font-weight:bold;color:#B4247E">${_esc(str(amount))}{" / month" if frequency=="monthly" else ""}</td></tr>'
        '</table>'
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:0 0 8px">This email serves as your donation receipt. The Caring Sisters Club, Inc. is a 501(c)(3) tax-exempt organization (EIN 88-1234567, sample). Your contribution is tax-deductible to the extent allowed by law. No goods or services were provided in exchange for this gift.</p>'
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:16px 0 0">With gratitude,<br/>The Caring Sisters Club</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:18px 32px;font-family:Arial,sans-serif">'
        '<p style="font-size:11px;color:#b79aae;margin:0;line-height:1.5">Sent by The Caring Sisters Club. We never ask for your password or card details by email.</p>'
        '</td></tr>'
        '</table></td></tr></table>'
    )


# ---------- Donor Wall (public) ----------
try:
    FUNDRAISING_GOAL = float(os.environ.get("FUNDRAISING_GOAL", "50000"))
except ValueError:
    FUNDRAISING_GOAL = 50000.0


def _display_name(txn: dict) -> str:
    if txn.get("anonymous") or not (txn.get("donor_name") or "").strip():
        return "Anonymous"
    parts = txn["donor_name"].strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


# ---------- Campaign Settings (editable goal + title) ----------
DEFAULT_SETTINGS = {
    "campaign_title": "Together we're making it happen",
    "campaign_subtitle": "Our Community of Givers",
    "goal": FUNDRAISING_GOAL,
}


async def _get_settings():
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0})
    if not doc:
        return dict(DEFAULT_SETTINGS)
    return {
        "campaign_title": doc.get("campaign_title") or DEFAULT_SETTINGS["campaign_title"],
        "campaign_subtitle": doc.get("campaign_subtitle") or DEFAULT_SETTINGS["campaign_subtitle"],
        "goal": float(doc.get("goal") or DEFAULT_SETTINGS["goal"]),
    }


class SettingsUpdate(BaseModel):
    campaign_title: Optional[str] = None
    campaign_subtitle: Optional[str] = None
    goal: Optional[float] = None


@api_router.get("/settings")
async def get_settings():
    return await _get_settings()


@api_router.put("/admin/settings")
async def update_settings(payload: SettingsUpdate, user=Depends(require_admin)):
    update = {}
    if payload.campaign_title is not None:
        update["campaign_title"] = payload.campaign_title.strip()
    if payload.campaign_subtitle is not None:
        update["campaign_subtitle"] = payload.campaign_subtitle.strip()
    if payload.goal is not None:
        if payload.goal <= 0:
            raise HTTPException(status_code=400, detail="Goal must be greater than zero")
        update["goal"] = float(payload.goal)
    if update:
        await db.settings.update_one({"key": "site"}, {"$set": update}, upsert=True)
    return await _get_settings()


@api_router.get("/donations/public")
async def donations_public():
    settings = await _get_settings()
    paid = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(2000)
    total = sum(float(t.get("amount", 0)) for t in paid)
    recent_src = sorted(paid, key=lambda t: t.get("updated_at", ""), reverse=True)[:12]
    recent = [{
        "name": _display_name(t),
        "amount": t.get("amount"),
        "frequency": t.get("frequency"),
        "date": t.get("updated_at"),
    } for t in recent_src]
    return {
        "total_raised": round(total, 2),
        "goal": settings["goal"],
        "campaign_title": settings["campaign_title"],
        "campaign_subtitle": settings["campaign_subtitle"],
        "donor_count": len(paid),
        "recent": recent,
    }


# ---------- Admin: Donations ----------
@api_router.get("/admin/donations")
async def admin_donations(frequency: Optional[str] = None, user=Depends(require_admin)):
    query = {"payment_status": "paid"}
    if frequency in ("monthly", "one-time"):
        query["frequency"] = frequency
    items = await db.payment_transactions.find(query, {"_id": 0}).sort("updated_at", -1).to_list(2000)
    all_paid = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(2000)
    total = sum(float(t.get("amount", 0)) for t in all_paid)
    monthly_ct = sum(1 for t in all_paid if t.get("frequency") == "monthly")
    onetime_ct = sum(1 for t in all_paid if t.get("frequency") != "monthly")
    return {
        "items": items,
        "summary": {
            "total_raised": round(total, 2),
            "count": len(all_paid),
            "monthly_count": monthly_ct,
            "onetime_count": onetime_ct,
        },
    }


# ---------- Admin: Team Access (allowlist management) ----------
class AllowEmail(BaseModel):
    email: str


class RoleUpdate(BaseModel):
    role: str


@api_router.get("/admin/team")
async def admin_team(user=Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0}).sort("created_at", 1).to_list(500)
    allowed = await db.allowed_emails.find({}, {"_id": 0}).to_list(500)
    return {"users": users, "allowed_emails": [a["email"] for a in allowed], "me": user["user_id"]}


@api_router.post("/admin/team/allow")
async def admin_team_allow(payload: AllowEmail, user=Depends(require_admin)):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    await db.allowed_emails.update_one({"email": email}, {"$set": {"email": email}}, upsert=True)
    # Promote an already-pending user with this email
    await db.users.update_one({"email": email}, {"$set": {"role": "admin"}})
    return {"message": "Email approved"}


@api_router.post("/admin/team/{user_id}/role")
async def admin_team_role(user_id: str, payload: RoleUpdate, user=Depends(require_admin)):
    if payload.role not in ("admin", "pending"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if user_id == user["user_id"] and payload.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin access")
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": payload.role}})
    return {"message": "Role updated"}


@api_router.post("/admin/team/revoke-email")
async def admin_team_revoke_email(payload: AllowEmail, user=Depends(require_admin)):
    email = payload.email.strip().lower()
    await db.allowed_emails.delete_one({"email": email})
    return {"message": "Email removed from allowlist"}



@app.on_event("startup")
async def startup_storage():
    try:
        init_storage()
        logging.info("Object storage initialized")
    except Exception as e:
        logging.error(f"Storage init failed: {e}")


@app.on_event("startup")
async def startup_indexes():
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("user_id", unique=True)
        await db.user_sessions.create_index("session_token")
        await db.media.create_index("category")
    except Exception as e:
        logging.warning(f"Index creation warning: {e}")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()