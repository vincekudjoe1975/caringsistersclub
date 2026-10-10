from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
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
from fastapi import Request, Response, HTTPException, UploadFile, File, Form, Depends, Header, Query, BackgroundTasks
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
ADMIN_OWNER_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_OWNER_EMAILS", "").split(",") if e.strip()}
ALLOWED_CATEGORIES = {"gallery", "board", "document", "event", "report", "program", "share"}


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
        update = {"name": data.get("name"), "picture": data.get("picture")}
        if email.lower() in ADMIN_OWNER_EMAILS and existing.get("role") != "admin":
            update["role"] = "admin"
        await db.users.update_one({"user_id": user_id}, {"$set": update})
    else:
        # Owner emails (ADMIN_OWNER_EMAILS) or admin-approved emails become admin; everyone else is pending.
        preapproved = email.lower() in ADMIN_OWNER_EMAILS or await db.allowed_emails.find_one({"email": email.lower()})
        role = "admin" if preapproved else "pending"
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
async def auth_me(request: Request, user=Depends(get_current_user)):
    if user.get("role") == "admin":
        try:
            await _detect_site_url(request)
        except Exception as e:
            logging.error(f"Site URL detection failed: {e}")
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


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_IMAGE_EXT = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
_DOC_EXT = {"pdf": "application/pdf"}


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
    return await _store_upload(file, category, title, subtitle, user["email"])


@api_router.post("/stories/photo")
async def upload_story_photo(request: Request, file: UploadFile = File(...)):
    _rate_limit(request, "story-photo", max_hits=3, window_s=600)
    doc = await _store_upload(file, "story", "Story photo", None, "public")
    return {"url": doc["url"]}


async def _store_upload(file: UploadFile, category: str, title, subtitle, uploader: str) -> dict:
    item_id = str(uuid.uuid4())
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    is_doc = category in ("document", "report")
    allowed = _DOC_EXT if is_doc else _IMAGE_EXT
    if ext not in allowed:
        kinds = "PDF" if is_doc else "PNG, JPG, WEBP or GIF image"
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Please upload a {kinds}.")
    # Derive content type from the validated extension (never trust client-supplied type).
    content_type = allowed[ext]
    # Read with a hard size cap so an oversized upload can't exhaust memory.
    data = b""
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data += chunk
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    storage_path = f"{APP_NAME}/{category}/{item_id}.{ext}"
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
        "uploaded_by": uploader,
    }
    await db.media.insert_one(doc)
    doc.pop("_id", None)
    doc["url"] = _media_url(item_id)
    return doc


@api_router.get("/media")
async def list_media(category: Optional[str] = None):
    query = {"is_deleted": {"$ne": True}, "category": {"$ne": "story"}}
    if category and category != "story":
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
    safe_type = item.get("content_type") or content_type or "application/octet-stream"
    return Response(
        content=data,
        media_type=safe_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
            "Cache-Control": "public, max-age=86400",
        },
    )


@api_router.get("/brand/logo")
async def get_brand_logo():
    path = ROOT_DIR / "brand_logo.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    return Response(
        content=path.read_bytes(),
        media_type="image/png",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=604800"},
    )


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
    appeal_id: Optional[str] = None


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
                "appeal_id": req.appeal_id or "",
            },
        )
    except Exception as e:
        logging.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=424, detail="Could not create checkout session")


import time as _time
from collections import deque, defaultdict

_RATE_BUCKETS: dict = defaultdict(deque)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit(request: Request, bucket: str, max_hits: int, window_s: int):
    """Gentle in-memory per-IP sliding-window limiter for public endpoints."""
    ip = _client_ip(request)
    key = f"{bucket}:{ip}"
    now = _time.monotonic()
    dq = _RATE_BUCKETS[key]
    while dq and dq[0] <= now - window_s:
        dq.popleft()
    if len(dq) >= max_hits:
        retry = int(window_s - (now - dq[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down and try again in a moment.",
            headers={"Retry-After": str(retry)},
        )
    dq.append(now)
    if not dq:
        _RATE_BUCKETS.pop(key, None)


@api_router.post("/payments/checkout")
async def create_donation_checkout(req: DonationCheckout, request: Request):
    _rate_limit(request, "checkout", max_hits=6, window_s=300)
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
        "appeal_id": (req.appeal_id or "")[:64] or None,
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
        _s = await _get_settings()
        manage = await _manage_url(donor_email) if txn.get("frequency") == "monthly" else None
        html = _receipt_html(donor_name, txn.get("amount"), txn.get("frequency"), ein=_s.get("org_ein", ""), manage_url=manage)
        await send_email(
            to=donor_email,
            subject="Thank you for your gift to The Caring Sisters Club",
            html=html,
        )
    await _maybe_send_thankyou(txn, recipient_email=donor_email)
    await _check_milestones()


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
    elif t in ("customer.subscription.updated", "customer.subscription.deleted"):
        if t.endswith("deleted") or obj.get("cancel_at_period_end") or obj.get("cancel_at"):
            await _handle_cancellation(obj)
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
        _s = await _get_settings()
        html = _receipt_html(donor_name, amount, "monthly", ein=_s.get("org_ein", ""), manage_url=await _manage_url(email))
        await send_email(
            to=email,
            subject="Your recurring gift to The Caring Sisters Club",
            html=html,
        )
    await _maybe_send_thankyou(txn, recipient_email=email)
    await _check_milestones()


# ---------- Form Submissions (public create, admin manage) ----------
ALLOWED_SUB_TYPES = {"volunteer", "member", "contact", "rsvp", "donation", "program_signup"}


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PUBLIC_SUB_TYPES = {"volunteer", "member", "contact"}
SUB_LABELS = {"program_signup": "Program sign-up", "story": "Member story", "volunteer": "Volunteer application", "member": "Membership application", "contact": "Contact message", "rsvp": "Event RSVP"}


def _validate_person(data: dict):
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Please enter your name.")
    if not _EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    for k, v in data.items():
        if isinstance(v, str) and len(v) > 5000:
            raise HTTPException(status_code=400, detail=f"The {k} field is too long.")
    return name, email


def _staff_notice_html(stype: str, data: dict) -> str:
    rows = "".join(
        f'<tr><td style="padding:6px 12px;font-size:13px;color:#6b5560;vertical-align:top;white-space:nowrap">{_esc(str(k).replace("_", " ").title())}</td>'
        f'<td style="padding:6px 12px;font-size:13px;color:#241019">{_esc(str(v)).replace(chr(10), "<br/>")}</td></tr>'
        for k, v in data.items() if v not in (None, "")
    )
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:24px 12px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("New Website Submission") +
        f'<tr><td style="padding:26px 24px;font-family:Arial,sans-serif"><h2 style="font-family:Georgia,serif;color:#3B0A2E;font-size:20px;margin:0 0 14px">{_esc(SUB_LABELS.get(stype, stype))}</h2>'
        f'<table role="presentation" width="100%" style="background:#faf2f7;border-radius:10px">{rows}</table>'
        '<p style="font-size:12px;color:#6b5560;margin:16px 0 0">Review and manage it in Admin &rarr; Form Submissions.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _notify_staff(stype: str, data: dict):
    try:
        to = (await _get_settings()).get("staff_notify_email")
        if not to:
            return
        who = data.get("name") or "someone"
        await send_email(to=to, subject=f"New {SUB_LABELS.get(stype, stype).lower()} from {who}"[:150],
                         html=_staff_notice_html(stype, data), reply_to=data.get("email"))
    except Exception as e:
        logging.error(f"Staff notification failed: {e}")


@api_router.post("/submissions")
async def create_submission(payload: SubmissionCreate, request: Request, background: BackgroundTasks):
    _rate_limit(request, "submission", max_hits=5, window_s=60)
    data = payload.model_dump()
    stype = data.get("type")
    if stype not in PUBLIC_SUB_TYPES:
        raise HTTPException(status_code=400, detail="Invalid submission type")
    _validate_person(data)
    if stype == "contact" and not str(data.get("message") or "").strip():
        raise HTTPException(status_code=400, detail="Please enter a message.")
    doc = {
        "id": str(uuid.uuid4()),
        "type": stype,
        "data": {k: v for k, v in data.items() if k != "type"},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.submissions.insert_one(doc)
    background.add_task(_notify_staff, stype, doc["data"])
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
    out["program_signup"]["overdue"] = await db.submissions.count_documents(_overdue_q())
    return out


def _overdue_q() -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    return {"type": "program_signup", "created_at": {"$lte": cutoff}, "stage": {"$in": [None, "new"]}}


@api_router.patch("/submissions/{item_id}/read")
async def mark_submission_read(item_id: str, user=Depends(require_admin)):
    await db.submissions.update_one({"id": item_id}, {"$set": {"read": True}})
    return {"message": "ok"}


@api_router.delete("/submissions/{item_id}")
async def delete_submission(item_id: str, background: BackgroundTasks, user=Depends(require_admin)):
    sub = await db.submissions.find_one_and_delete({"id": item_id})
    if sub and sub.get("type") == "program_signup":
        pid = await _signup_program_id(sub)
        if pid:
            background.add_task(_fill_seats, pid)
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


_SITE_URL_FALLBACK = os.environ.get("PUBLIC_APP_URL", "https://caring-sisters-clone.preview.emergentagent.com").rstrip("/")
PUBLIC_APP_URL = _SITE_URL_FALLBACK


def _clean_site_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query:
        raise ValueError("Website address must look like https://yourdomain.org")
    return f"https://{parsed.netloc.lower()}"


async def _refresh_site_url():
    """Email links use the admin-set site_url only (detected host is just a suggestion in Admin)."""
    global PUBLIC_APP_URL
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0}) or {}
    PUBLIC_APP_URL = (doc.get("site_url") or _SITE_URL_FALLBACK).rstrip("/")


async def _detect_site_url(request: Request):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip().lower()
    if not host or host.startswith(("localhost", "127.", "0.0.0.0")) or ":" in host:
        return
    url = f"https://{host}"
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0, "detected_site_url": 1}) or {}
    if doc.get("detected_site_url") != url:
        await db.settings.update_one({"key": "site"}, {"$set": {"detected_site_url": url}}, upsert=True)


def _brand_header(eyebrow: str) -> str:
    return (
        '<tr><td style="background:#3B0A2E;padding:24px 32px;color:#F7EFE9;text-align:center">'
        f'<img src="{PUBLIC_APP_URL}/api/brand/logo" alt="The Caring Sisters Club" width="64" height="64" '
        'style="display:block;margin:0 auto 10px;border-radius:50%;background:#fff" />'
        '<div style="font-family:Georgia,serif;font-size:19px;font-weight:bold;letter-spacing:1px">The Caring Sisters Club</div>'
        f'<div style="font-size:11px;color:#CBA24B;letter-spacing:3px;text-transform:uppercase;margin-top:4px">{_esc(eyebrow)}</div>'
        '</td></tr>'
    )


def _receipt_html(name: str, amount, frequency: str, ein: str = "", manage_url: str = None) -> str:
    manage_html = (
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:0 0 8px">Need to update your card or change your plans? '
        f'<a href="{manage_url}" style="color:#B4247E;font-weight:bold">Manage your gift</a> securely. For your protection this link works once; '
        f'you can request a new one anytime at <a href="{PUBLIC_APP_URL}/manage-gift" style="color:#B4247E">our Manage My Gift page</a>.</p>'
        if manage_url else ""
    )
    freq_txt = "monthly" if frequency == "monthly" else "one-time"
    ein_txt = f" (EIN {_esc(ein)})" if ein else ""
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0">'
        '<tr><td align="center" style="padding:28px 16px;font-family:Georgia,\'Times New Roman\',serif">'
        '<table role="presentation" width="600" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden">'
        + _brand_header("Love \u00b7 Respect \u00b7 Empowerment") +
        '<tr><td style="padding:32px;font-family:Arial,Helvetica,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 16px">Thank you, {_esc(name)}!</h1>'
        f'<p style="font-size:15px;line-height:1.6;color:#4a3340;margin:0 0 16px">Your generosity fuels professional empowerment, housing support, and community care for women across the Diaspora. We are deeply grateful for your {freq_txt} gift.</p>'
        '<table role="presentation" width="100%" style="background:#faf2f7;border-radius:12px;margin:8px 0 20px">'
        f'<tr><td style="padding:18px 22px;font-size:14px;color:#3B0A2E">Gift amount</td>'
        f'<td align="right" style="padding:18px 22px;font-size:20px;font-weight:bold;color:#B4247E">${_esc(str(amount))}{" / month" if frequency=="monthly" else ""}</td></tr>'
        '</table>'
        f'<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:0 0 8px">This email serves as your donation receipt. The Caring Sisters Club, Inc. is a 501(c)(3) tax-exempt organization{ein_txt}. Your contribution is tax-deductible to the extent allowed by law. No goods or services were provided in exchange for this gift.</p>'
        + manage_html +
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


def _thankyou_email_html(name: str, amount, frequency: str, sender_name: str, note: str) -> str:
    freq_txt = " monthly" if frequency == "monthly" else ""
    note_html = (
        f'<p style="font-size:15px;line-height:1.7;color:#4a3340;margin:0 0 18px">{_esc(note)}</p>'
        if note else ""
    )
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0">'
        '<tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden">'
        '<tr><td style="background:#3B0A2E;padding:28px 32px;color:#F7EFE9;font-family:Georgia,serif">'
        '<div style="font-size:20px;font-weight:bold;letter-spacing:1px">The Caring Sisters Club</div>'
        '<div style="font-size:11px;color:#CBA24B;letter-spacing:3px;text-transform:uppercase;margin-top:4px">A Personal Thank You</div>'
        '</td></tr>'
        '<tr><td style="padding:32px;font-family:Arial,Helvetica,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#B4247E;font-size:24px;margin:0 0 16px">Dear {_esc(name)},</h1>'
        f'<p style="font-size:15px;line-height:1.7;color:#4a3340;margin:0 0 18px">Your extraordinary{freq_txt} gift of <strong>${_esc(str(amount))}</strong> truly moved us. I am writing to you personally to say thank you from the bottom of my heart.</p>'
        f'{note_html}'
        '<p style="font-size:14px;line-height:1.6;color:#6b5560;margin:18px 0 0">With deep gratitude,</p>'
        f'<p style="font-family:Georgia,serif;font-size:16px;color:#3B0A2E;margin:4px 0 0;font-weight:bold">{_esc(sender_name)}</p>'
        '<p style="font-size:13px;color:#6b5560;margin:2px 0 0">The Caring Sisters Club</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:18px 32px;font-family:Arial,sans-serif">'
        '<p style="font-size:11px;color:#b79aae;margin:0;line-height:1.5">A formal tax receipt has been sent separately. We never ask for your password or card details by email.</p>'
        '</td></tr>'
        '</table></td></tr></table>'
    )


async def _maybe_send_thankyou(txn: dict, recipient_email: str = None):
    """Send a personal board-member thank-you for gifts at or above the configured threshold."""
    try:
        settings = await _get_settings()
        if not settings.get("thankyou_enabled"):
            return
        threshold = float(settings.get("thankyou_threshold") or 0)
        amount = float(txn.get("amount") or 0)
        if threshold <= 0 or amount < threshold:
            return
        email = (recipient_email or txn.get("donor_email") or "").strip()
        if not email:
            return
        session_id = txn.get("session_id")
        if session_id and await db.thankyou_sent.find_one({"session_id": session_id}):
            return
        donor_name = (txn.get("donor_name") or "").strip() or "Friend"
        html = _thankyou_email_html(
            donor_name, txn.get("amount"), txn.get("frequency"),
            settings.get("thankyou_sender_name"), settings.get("thankyou_note"),
        )
        await send_email(
            to=email,
            subject=f"A personal thank you from {settings.get('thankyou_sender_name')}",
            html=html,
        )
        await db.thankyou_sent.insert_one({
            "session_id": session_id,
            "email": email,
            "amount": amount,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logging.error(f"Thank-you automation failed: {e}")


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
    "deadline": None,
    "thankyou_enabled": True,
    "thankyou_threshold": 250.0,
    "thankyou_sender_name": "Fem Mansaray, Founder & President",
    "thankyou_note": "On behalf of our entire board and the women we serve, I wanted to personally thank you. Gifts like yours are transformational, and we are honored to have you in our sisterhood.",
    "org_ein": "",
    "lapsed_autoemail_enabled": True,
    "lapsed_cooldown_days": 30,
    "site_url": "",
    "detected_site_url": "",
    "staff_notify_email": "caringsistersclub@gmail.com",
    "story_requests_enabled": True,
}


async def _get_settings():
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0})
    if not doc:
        return dict(DEFAULT_SETTINGS)
    return {
        "campaign_title": doc.get("campaign_title") or DEFAULT_SETTINGS["campaign_title"],
        "campaign_subtitle": doc.get("campaign_subtitle") or DEFAULT_SETTINGS["campaign_subtitle"],
        "goal": float(doc.get("goal") or DEFAULT_SETTINGS["goal"]),
        "deadline": doc.get("deadline"),
        "thankyou_enabled": doc.get("thankyou_enabled", DEFAULT_SETTINGS["thankyou_enabled"]),
        "thankyou_threshold": float(doc.get("thankyou_threshold") or DEFAULT_SETTINGS["thankyou_threshold"]),
        "thankyou_sender_name": doc.get("thankyou_sender_name") or DEFAULT_SETTINGS["thankyou_sender_name"],
        "thankyou_note": doc.get("thankyou_note") or DEFAULT_SETTINGS["thankyou_note"],
        "org_ein": doc.get("org_ein", DEFAULT_SETTINGS["org_ein"]),
        "lapsed_autoemail_enabled": doc.get("lapsed_autoemail_enabled", DEFAULT_SETTINGS["lapsed_autoemail_enabled"]),
        "lapsed_cooldown_days": int(doc.get("lapsed_cooldown_days") or DEFAULT_SETTINGS["lapsed_cooldown_days"]),
        "site_url": doc.get("site_url") or "",
        "detected_site_url": doc.get("detected_site_url") or "",
        "staff_notify_email": doc.get("staff_notify_email", DEFAULT_SETTINGS["staff_notify_email"]),
        "story_requests_enabled": doc.get("story_requests_enabled", True),
    }


class SettingsUpdate(BaseModel):
    campaign_title: Optional[str] = None
    campaign_subtitle: Optional[str] = None
    goal: Optional[float] = None
    deadline: Optional[str] = None  # ISO date (YYYY-MM-DD) or "" to clear
    thankyou_enabled: Optional[bool] = None
    thankyou_threshold: Optional[float] = None
    thankyou_sender_name: Optional[str] = None
    thankyou_note: Optional[str] = None
    org_ein: Optional[str] = None
    lapsed_autoemail_enabled: Optional[bool] = None
    lapsed_cooldown_days: Optional[int] = None
    site_url: Optional[str] = None
    staff_notify_email: Optional[str] = None
    story_requests_enabled: Optional[bool] = None


@api_router.get("/settings")
async def get_settings():
    # Public endpoint: expose only public campaign fields (SEC-003 — no internal
    # thank-you config such as sender/note/threshold).
    s = await _get_settings()
    return {
        "campaign_title": s["campaign_title"],
        "campaign_subtitle": s["campaign_subtitle"],
        "goal": s["goal"],
        "deadline": s["deadline"],
    }


@api_router.get("/admin/settings")
async def admin_get_settings(user=Depends(require_admin)):
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
    if payload.deadline is not None:
        update["deadline"] = payload.deadline.strip() or None
    if payload.thankyou_enabled is not None:
        update["thankyou_enabled"] = bool(payload.thankyou_enabled)
    if payload.thankyou_threshold is not None:
        if payload.thankyou_threshold < 0:
            raise HTTPException(status_code=400, detail="Threshold cannot be negative")
        update["thankyou_threshold"] = float(payload.thankyou_threshold)
    if payload.thankyou_sender_name is not None:
        update["thankyou_sender_name"] = payload.thankyou_sender_name.strip()
    if payload.thankyou_note is not None:
        update["thankyou_note"] = payload.thankyou_note.strip()
    if payload.org_ein is not None:
        update["org_ein"] = payload.org_ein.strip()
    if payload.lapsed_autoemail_enabled is not None:
        update["lapsed_autoemail_enabled"] = bool(payload.lapsed_autoemail_enabled)
    if payload.lapsed_cooldown_days is not None:
        update["lapsed_cooldown_days"] = max(1, int(payload.lapsed_cooldown_days))
    if payload.site_url is not None:
        try:
            update["site_url"] = _clean_site_url(payload.site_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if payload.story_requests_enabled is not None:
        update["story_requests_enabled"] = bool(payload.story_requests_enabled)
    if payload.staff_notify_email is not None:
        em = payload.staff_notify_email.strip()
        if em and not _EMAIL_RE.match(em):
            raise HTTPException(status_code=400, detail="Staff notification email is not valid")
        update["staff_notify_email"] = em
    if update:
        await db.settings.update_one({"key": "site"}, {"$set": update}, upsert=True)
        await _refresh_site_url()
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
        "deadline": settings["deadline"],
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
    pending_items = await db.payment_transactions.find(
        {"payment_status": {"$nin": ["paid", "expired"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    total = sum(float(t.get("amount", 0)) for t in all_paid)
    monthly_ct = sum(1 for t in all_paid if t.get("frequency") == "monthly")
    onetime_ct = sum(1 for t in all_paid if t.get("frequency") != "monthly")

    # Active recurring donors: unique subscriptions with a paid monthly gift.
    # Monthly recurring revenue (MRR) = sum of one gift per active subscription.
    active_subs = {}
    for t in all_paid:
        if t.get("frequency") == "monthly" and t.get("stripe_subscription_id"):
            active_subs[t["stripe_subscription_id"]] = float(t.get("amount", 0))
    # Fallback: monthly gifts without a subscription id (e.g. seeded/test)
    monthly_no_sub = [t for t in all_paid if t.get("frequency") == "monthly" and not t.get("stripe_subscription_id")]
    mrr = sum(active_subs.values()) + sum(float(t.get("amount", 0)) for t in monthly_no_sub)
    active_recurring = len(active_subs) + len(monthly_no_sub)

    return {
        "items": items,
        "pending_items": pending_items,
        "summary": {
            "total_raised": round(total, 2),
            "count": len(all_paid),
            "monthly_count": monthly_ct,
            "onetime_count": onetime_ct,
            "active_recurring": active_recurring,
            "monthly_revenue": round(mrr, 2),
        },
    }


# ---------- Admin: CSV export, year-end statements, progress emails ----------
import csv
import io
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse


def _txn_display_name(t: dict) -> str:
    if t.get("anonymous"):
        return "Anonymous"
    return (t.get("donor_name") or "").strip() or "Anonymous"


@api_router.get("/admin/donations/export")
async def export_donations_csv(year: Optional[int] = None, user=Depends(require_admin)):
    query = {"payment_status": "paid"}
    rows = await db.payment_transactions.find(query, {"_id": 0}).sort("updated_at", 1).to_list(5000)
    if year:
        rows = [r for r in rows if (r.get("updated_at") or "").startswith(str(year))]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Donor Name", "Email", "Amount (USD)", "Type", "Renewal", "Transaction ID"])
    for r in rows:
        date = (r.get("updated_at") or "")[:10]
        writer.writerow([
            date,
            _csv_safe(_txn_display_name(r)),
            _csv_safe(r.get("donor_email") or ""),
            f"{float(r.get('amount', 0)):.2f}",
            "Monthly" if r.get("frequency") == "monthly" else "One-Time",
            "Yes" if r.get("is_renewal") else "No",
            r.get("session_id") or "",
        ])
    buf.seek(0)
    fname = f"caring-sisters-donations{'-' + str(year) if year else ''}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


def _year_statement_html(name: str, year: int, total: float, gifts: list, ein: str = "") -> str:
    rows = "".join(
        f'<tr><td style="padding:8px 12px;font-size:13px;color:#4a3340;border-top:1px solid #eadfe6">{_esc((g.get("updated_at") or "")[:10])}</td>'
        f'<td style="padding:8px 12px;font-size:13px;color:#4a3340;border-top:1px solid #eadfe6">{"Monthly" if g.get("frequency")=="monthly" else "One-Time"}</td>'
        f'<td align="right" style="padding:8px 12px;font-size:13px;color:#3B0A2E;font-weight:bold;border-top:1px solid #eadfe6">${float(g.get("amount",0)):,.2f}</td></tr>'
        for g in gifts
    )
    ein_txt = f" (EIN {_esc(ein)})" if ein else ""
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header(f"{year} Annual Giving Statement") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:22px;margin:0 0 12px">Thank you, {_esc(name)}</h1>'
        f'<p style="font-size:14px;line-height:1.6;color:#4a3340;margin:0 0 18px">Here is a summary of your tax-deductible contributions to The Caring Sisters Club during {year}. Please retain this statement for your records.</p>'
        '<table role="presentation" width="100%" style="border-collapse:collapse;margin-bottom:16px">'
        '<tr style="background:#faf2f7"><td style="padding:8px 12px;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#B4247E">Date</td>'
        '<td style="padding:8px 12px;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#B4247E">Type</td>'
        '<td align="right" style="padding:8px 12px;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#B4247E">Amount</td></tr>'
        f'{rows}</table>'
        '<table role="presentation" width="100%" style="background:#3B0A2E;border-radius:12px">'
        f'<tr><td style="padding:16px 22px;font-size:14px;color:#F7EFE9">Total {year} contributions</td>'
        f'<td align="right" style="padding:16px 22px;font-size:20px;font-weight:bold;color:#CBA24B">${total:,.2f}</td></tr></table>'
        f'<p style="font-size:12px;line-height:1.6;color:#6b5560;margin:18px 0 0">The Caring Sisters Club, Inc. is a 501(c)(3) tax-exempt organization{ein_txt}. No goods or services were provided in exchange for these contributions. Please consult your tax advisor.</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">With gratitude, The Caring Sisters Club. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _run_year_statements(yr: int) -> dict:
    settings = await _get_settings()
    ein = settings.get("org_ein", "")
    rows = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(5000)
    rows = [r for r in rows if (r.get("updated_at") or "").startswith(str(yr)) and (r.get("donor_email") or "").strip()]
    by_email = {}
    for r in rows:
        by_email.setdefault(r["donor_email"].strip().lower(), []).append(r)
    sent = 0
    for email, gifts in by_email.items():
        total = sum(float(g.get("amount", 0)) for g in gifts)
        name = next((g.get("donor_name") for g in gifts if (g.get("donor_name") or "").strip()), None) or "Friend"
        gifts_sorted = sorted(gifts, key=lambda g: g.get("updated_at") or "")
        html = _year_statement_html(name, yr, total, gifts_sorted, ein=ein)
        result = await send_email(to=email, subject=f"Your {yr} giving statement — The Caring Sisters Club", html=html)
        if result is not None:
            sent += 1
    return {"year": yr, "recipients": len(by_email), "sent": sent}


@api_router.post("/admin/donations/send-statements")
async def send_year_statements(year: Optional[int] = None, user=Depends(require_admin)):
    yr = year or datetime.now(timezone.utc).year
    return await _run_year_statements(yr)


class ProgressEmail(BaseModel):
    message: Optional[str] = None


def _progress_email_html(pct: int, raised: float, goal: float, title: str, note: str) -> str:
    bar_w = max(3, min(100, pct))
    note_html = f'<p style="font-size:14px;line-height:1.6;color:#4a3340;margin:0 0 18px">{_esc(note)}</p>' if note else ''
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        '<tr><td style="background:#3B0A2E;padding:26px 32px;color:#F7EFE9;font-family:Georgia,serif">'
        '<div style="font-size:19px;font-weight:bold">The Caring Sisters Club</div>'
        '<div style="font-size:11px;color:#CBA24B;letter-spacing:3px;text-transform:uppercase;margin-top:4px">Campaign Update</div></td></tr>'
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#B4247E;font-size:26px;margin:0 0 10px">We\'re {pct}% there!</h1>'
        f'<p style="font-size:14px;line-height:1.6;color:#4a3340;margin:0 0 8px">Thanks to supporters like you, <strong>{_esc(title)}</strong> has raised <strong>${raised:,.0f}</strong> of our <strong>${goal:,.0f}</strong> goal.</p>'
        f'{note_html}'
        f'<div style="height:16px;border-radius:999px;background:#eadfe6;overflow:hidden;margin:6px 0 20px"><div style="height:16px;width:{bar_w}%;background:#B4247E;border-radius:999px"></div></div>'
        '<a href="' + PUBLIC_APP_URL + '/donate" style="display:inline-block;background:#B4247E;color:#fff;text-decoration:none;font-weight:bold;font-size:14px;padding:12px 26px;border-radius:999px">Give Again</a>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You\'re receiving this because you supported The Caring Sisters Club. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


@api_router.post("/admin/campaign/send-progress")
async def send_progress_email(payload: ProgressEmail, user=Depends(require_admin)):
    settings = await _get_settings()
    goal = float(settings.get("goal") or 0)
    paid = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(5000)
    total = sum(float(t.get("amount", 0)) for t in paid)
    pct = int((total / goal) * 100) if goal > 0 else 0
    emails = sorted({(t.get("donor_email") or "").strip().lower() for t in paid if (t.get("donor_email") or "").strip()})
    html = _progress_email_html(pct, total, goal, settings.get("campaign_title"), payload.message or "")
    sent = 0
    for email in emails:
        result = await send_email(to=email, subject=f"We're {pct}% to our goal — thank you!", html=html)
        if result is not None:
            sent += 1
    return {"percent": pct, "recipients": len(emails), "sent": sent}


# ---------- Admin: Donor Profiles ----------
LAPSED_GRACE_DAYS = 35  # a monthly donor whose last monthly gift predates this is "lapsed"


def _is_lapsed(last_monthly_iso: str) -> bool:
    if not last_monthly_iso:
        return False
    try:
        last = datetime.fromisoformat(last_monthly_iso.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last).days > LAPSED_GRACE_DAYS
    except (ValueError, TypeError):
        return False


@api_router.get("/admin/donors")
async def admin_donors(user=Depends(require_admin)):
    paid = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(5000)
    profiles = {}
    for t in paid:
        email = (t.get("donor_email") or "").strip().lower()
        key = email or f"anon:{t.get('session_id')}"
        p = profiles.setdefault(key, {
            "email": email,
            "name": "",
            "lifetime": 0.0,
            "gifts": 0,
            "last_gift": "",
            "last_monthly_gift": "",
            "has_monthly": False,
            "anonymous_only": True,
        })
        p["lifetime"] += float(t.get("amount", 0))
        p["gifts"] += 1
        upd = t.get("updated_at") or ""
        if t.get("frequency") == "monthly":
            p["has_monthly"] = True
            if upd > p["last_monthly_gift"]:
                p["last_monthly_gift"] = upd
        if not t.get("anonymous") and (t.get("donor_name") or "").strip():
            p["name"] = t["donor_name"].strip()
            p["anonymous_only"] = False
        if upd > p["last_gift"]:
            p["last_gift"] = upd
    # Attach private notes/tags (keyed by email)
    notes_docs = await db.donor_notes.find({}, {"_id": 0}).to_list(5000)
    notes_map = {n["email"]: n for n in notes_docs}
    out = []
    for p in profiles.values():
        p["lifetime"] = round(p["lifetime"], 2)
        if not p["name"]:
            p["name"] = "Anonymous" if p["anonymous_only"] else (p["email"] or "Anonymous")
        p["lapsed"] = bool(p["has_monthly"] and _is_lapsed(p["last_monthly_gift"]))
        nd = notes_map.get(p["email"]) if p["email"] else None
        p["tags"] = (nd.get("tags") if nd else []) or []
        p["has_note"] = bool(nd and (nd.get("note") or "").strip())
        out.append(p)
    out.sort(key=lambda x: x["lifetime"], reverse=True)
    lapsed_count = sum(1 for p in out if p.get("lapsed"))
    return {"donors": out, "count": len(out), "lapsed_count": lapsed_count}


class DonorNotes(BaseModel):
    note: Optional[str] = None
    tags: Optional[List[str]] = None


@api_router.get("/admin/donors/{email}")
async def admin_donor_detail(email: str, user=Depends(require_admin)):
    em = email.strip().lower()
    gifts = await db.payment_transactions.find(
        {"payment_status": "paid", "donor_email": {"$regex": f"^{re.escape(em)}$", "$options": "i"}},
        {"_id": 0},
    ).sort("updated_at", -1).to_list(2000)
    lifetime = round(sum(float(g.get("amount", 0)) for g in gifts), 2)
    name = next((g.get("donor_name") for g in gifts if (g.get("donor_name") or "").strip() and not g.get("anonymous")), None) or em
    last_monthly = next((g.get("updated_at") for g in gifts if g.get("frequency") == "monthly"), "")
    has_monthly = any(g.get("frequency") == "monthly" for g in gifts)
    nd = await db.donor_notes.find_one({"email": em}, {"_id": 0}) or {}
    react = await db.reactivation_sent.find_one({"email": em}, {"_id": 0}, sort=[("sent_at", -1)])
    return {
        "email": em,
        "name": name,
        "lifetime": lifetime,
        "gift_count": len(gifts),
        "gifts": gifts,
        "note": nd.get("note", ""),
        "tags": nd.get("tags", []),
        "lapsed": bool(has_monthly and _is_lapsed(last_monthly)),
        "has_monthly": has_monthly,
        "reactivation_last_sent": react.get("sent_at") if react else None,
    }


@api_router.put("/admin/donors/{email}/notes")
async def update_donor_notes(email: str, payload: DonorNotes, user=Depends(require_admin)):
    em = email.strip().lower()
    if not em or "@" not in em:
        raise HTTPException(status_code=400, detail="Valid donor email required")
    update = {"email": em, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get("user_id")}
    if payload.note is not None:
        update["note"] = payload.note.strip()
    if payload.tags is not None:
        clean = []
        for t in payload.tags:
            t = (t or "").strip()
            if t and t not in clean:
                clean.append(t)
        update["tags"] = clean[:20]
    await db.donor_notes.update_one({"email": em}, {"$set": update}, upsert=True)
    doc = await db.donor_notes.find_one({"email": em}, {"_id": 0})
    return {"email": em, "note": doc.get("note", ""), "tags": doc.get("tags", [])}


# ---------- Reactivation ("we miss you") + test receipt ----------
def _reactivation_email_html(name: str) -> str:
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        '<tr><td style="background:#3B0A2E;padding:26px 32px;color:#F7EFE9;font-family:Georgia,serif">'
        '<div style="font-size:19px;font-weight:bold">The Caring Sisters Club</div>'
        '<div style="font-size:11px;color:#CBA24B;letter-spacing:3px;text-transform:uppercase;margin-top:4px">We Miss You</div></td></tr>'
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#B4247E;font-size:24px;margin:0 0 14px">We miss you, {_esc(name)}</h1>'
        '<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 16px">It has been a little while since your last gift, and we wanted to reach out — not to ask, but to say thank you. Your past generosity helped empower women of the Diaspora through friendship, professional growth, and community care.</p>'
        '<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 20px">If you would like to rejoin our community of givers, we would be honored to welcome you back. Every gift, of any size, makes a real difference.</p>'
        '<a href="' + PUBLIC_APP_URL + '/donate" style="display:inline-block;background:#B4247E;color:#fff;text-decoration:none;font-weight:bold;font-size:14px;padding:12px 26px;border-radius:999px">Rejoin Our Mission</a>'
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:22px 0 0">With warmth and gratitude,<br/>The Caring Sisters Club</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you previously supported The Caring Sisters Club. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


@api_router.post("/admin/donors/{email}/reactivation")
async def send_reactivation_email(email: str, user=Depends(require_admin)):
    em = email.strip().lower()
    # Recipient must be an existing donor on record (G4: not arbitrary caller input).
    gift = await db.payment_transactions.find_one(
        {"payment_status": "paid", "donor_email": {"$regex": f"^{re.escape(em)}$", "$options": "i"}},
        {"_id": 0},
    )
    if not gift:
        raise HTTPException(status_code=404, detail="No donor with that email on record")
    name = (gift.get("donor_name") or "").strip() or "Friend"
    result = await send_email(
        to=em,
        subject="We miss you at The Caring Sisters Club",
        html=_reactivation_email_html(name),
    )
    await db.reactivation_sent.insert_one({
        "email": em,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": user.get("user_id"),
        "delivered": result is not None,
    })
    if result is None:
        return {"sent": False, "email": em, "detail": "The email provider could not deliver to this address."}
    return {"sent": True, "email": em}


@api_router.post("/admin/email/test-receipt")
async def send_test_receipt(user=Depends(require_admin)):
    # Sends the real branded receipt template to the logged-in admin's OWN email.
    to = (user.get("email") or "").strip()
    if not to:
        raise HTTPException(status_code=400, detail="Your admin account has no email on file")
    _s = await _get_settings()
    result = await send_email(
        to=to,
        subject="Test receipt — The Caring Sisters Club",
        html=_receipt_html(user.get("name") or "Friend", 100, "one-time", ein=_s.get("org_ein", "")),
    )
    if result is None:
        return {"sent": False, "to": to, "detail": "The email provider could not deliver to your address."}
    return {"sent": True, "to": to}


MAJOR_DONOR_MIN = 500.0


def _appeal_email_html(name: str, subject: str, message_html: str, appeal_id: str = None) -> str:
    gift_url = f"{PUBLIC_APP_URL}/api/t/appeal/{appeal_id}" if appeal_id else f"{PUBLIC_APP_URL}/donate"
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("A Note For You") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:22px;margin:0 0 14px">{_esc(subject)}</h1>'
        f'<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">Dear {_esc(name)},</p>'
        f'<div style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 22px">{message_html}</div>'
        '<a href="' + gift_url + '" style="display:inline-block;background:#B4247E;color:#fff;text-decoration:none;font-weight:bold;font-size:14px;padding:12px 26px;border-radius:999px">Make a Gift</a>'
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:22px 0 0">With gratitude,<br/>The Caring Sisters Club</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you supported The Caring Sisters Club. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


class SegmentEmail(BaseModel):
    segment: str  # all | monthly | lapsed | major
    subject: str
    message: str


async def _donor_segment_recipients(seg: str) -> list:
    paid = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(5000)
    profiles = {}
    for t in paid:
        email = (t.get("donor_email") or "").strip().lower()
        if not email:
            continue
        p = profiles.setdefault(email, {"email": email, "name": "", "lifetime": 0.0, "has_monthly": False, "last_monthly": ""})
        p["lifetime"] += float(t.get("amount", 0))
        if t.get("frequency") == "monthly":
            p["has_monthly"] = True
            upd = t.get("updated_at") or ""
            if upd > p["last_monthly"]:
                p["last_monthly"] = upd
        if not t.get("anonymous") and (t.get("donor_name") or "").strip():
            p["name"] = t["donor_name"].strip()

    def in_segment(p):
        if seg == "monthly":
            return p["has_monthly"]
        if seg == "lapsed":
            return p["has_monthly"] and _is_lapsed(p["last_monthly"])
        if seg == "major":
            return p["lifetime"] >= MAJOR_DONOR_MIN
        return True

    return [p for p in profiles.values() if in_segment(p)]


@api_router.get("/admin/donors/segment-count/{segment}")
async def donor_segment_count(segment: str, user=Depends(require_admin)):
    recipients = await _donor_segment_recipients(segment.strip().lower())
    return {"segment": segment, "count": len(recipients)}


async def _dispatch_segment_appeal(seg: str, subject: str, message: str, sent_by: str, sent_by_name: str) -> dict:
    recipients = await _donor_segment_recipients(seg)
    if not recipients:
        return {"recipients": 0, "sent": 0, "empty": True}
    message_html = _esc(message).replace("\n", "<br/>")
    appeal_id = str(uuid.uuid4())
    sent = 0
    for p in recipients:
        result = await send_email(to=p["email"], subject=subject, html=_appeal_email_html(p["name"] or "Friend", subject, message_html, appeal_id))
        if result is not None:
            sent += 1
    await db.segment_emails.insert_one({
        "id": appeal_id, "clicks": 0,
        "segment": seg, "subject": subject, "recipients": len(recipients),
        "sent": sent, "sent_by": sent_by, "sent_by_name": sent_by_name,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"recipients": len(recipients), "sent": sent, "appeal_id": appeal_id}


@api_router.get("/t/appeal/{appeal_id}")
async def track_appeal_click(appeal_id: str, request: Request):
    target = f"{PUBLIC_APP_URL}/donate"
    try:
        _rate_limit(request, f"appeal-click:{appeal_id}", max_hits=3, window_s=600)
        res = await db.segment_emails.update_one({"id": appeal_id}, {"$inc": {"clicks": 1}})
        if res.matched_count:
            target = f"{target}?appeal={appeal_id}"
    except HTTPException:
        target = f"{target}?appeal={appeal_id}"
    return RedirectResponse(url=target, status_code=302)


@api_router.post("/admin/donors/segment-email")
async def send_segment_email(payload: SegmentEmail, user=Depends(require_admin)):
    seg = (payload.segment or "all").strip().lower()
    subject = (payload.subject or "").strip()
    message = (payload.message or "").strip()
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message are required")
    result = await _dispatch_segment_appeal(seg, subject, message, user.get("user_id"), user.get("name") or user.get("email") or "Admin")
    if result.get("empty"):
        raise HTTPException(status_code=400, detail="No donors match this segment")
    return {"segment": seg, "recipients": result["recipients"], "sent": result["sent"]}


@api_router.post("/admin/donors/segment-email/test")
async def send_segment_email_test(payload: SegmentEmail, user=Depends(require_admin)):
    # Sends a preview of the appeal to the logged-in admin's OWN email only.
    subject = (payload.subject or "").strip()
    message = (payload.message or "").strip()
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message are required")
    to = (user.get("email") or "").strip()
    if not to:
        raise HTTPException(status_code=400, detail="Your admin account has no email on file")
    message_html = _esc(message).replace("\n", "<br/>")
    result = await send_email(to=to, subject=f"[Test] {subject}", html=_appeal_email_html(user.get("name") or "Friend", subject, message_html))
    if result is None:
        return {"sent": False, "to": to, "detail": "The email provider could not deliver to your address."}
    return {"sent": True, "to": to}


@api_router.get("/admin/appeals")
async def donor_appeal_history(user=Depends(require_admin)):
    items = await db.segment_emails.find({}, {"_id": 0}).sort("sent_at", -1).to_list(50)
    ids = [a["id"] for a in items if a.get("id")]
    stats = {}
    if ids:
        async for row in db.payment_transactions.aggregate([
            {"$match": {"appeal_id": {"$in": ids}, "payment_status": "paid"}},
            {"$group": {"_id": "$appeal_id", "donations": {"$sum": 1}, "raised": {"$sum": "$amount"}}},
        ]):
            stats[row["_id"]] = row
    for a in items:
        st = stats.get(a.get("id"), {})
        a["clicks"] = a.get("clicks", 0)
        a["donations"] = st.get("donations", 0)
        a["raised"] = round(float(st.get("raised", 0)), 2)
    return {"items": items}


# ---------- Appeal templates (reusable) ----------
class AppealTemplate(BaseModel):
    name: str
    subject: str
    message: str


@api_router.get("/admin/appeal-templates")
async def list_appeal_templates(user=Depends(require_admin)):
    items = await db.appeal_templates.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": items}


@api_router.post("/admin/appeal-templates")
async def create_appeal_template(payload: AppealTemplate, user=Depends(require_admin)):
    name = (payload.name or "").strip()
    subject = (payload.subject or "").strip()
    message = (payload.message or "").strip()
    if not name or not subject or not message:
        raise HTTPException(status_code=400, detail="Name, subject and message are required")
    doc = {
        "id": str(uuid.uuid4()), "name": name, "subject": subject, "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(), "created_by": user.get("user_id"),
    }
    await db.appeal_templates.insert_one(dict(doc))
    return doc


@api_router.delete("/admin/appeal-templates/{tid}")
async def delete_appeal_template(tid: str, user=Depends(require_admin)):
    res = await db.appeal_templates.delete_one({"id": tid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True}


# ---------- Scheduled appeals (sent by the daily scheduler) ----------
class ScheduledAppeal(BaseModel):
    segment: str
    subject: str
    message: str
    send_on: str  # YYYY-MM-DD
    repeat: str = "none"  # none | monthly | quarterly


REPEAT_MONTHS = {"monthly": 1, "quarterly": 3}


def _add_months(day, months: int):
    import calendar
    m = day.month - 1 + months
    y, m = day.year + m // 12, m % 12 + 1
    return day.replace(year=y, month=m, day=min(day.day, calendar.monthrange(y, m)[1]))


@api_router.get("/admin/scheduled-appeals")
async def list_scheduled_appeals(user=Depends(require_admin)):
    items = await db.scheduled_appeals.find({}, {"_id": 0}).sort("send_on", 1).to_list(100)
    return {"items": items}


@api_router.post("/admin/scheduled-appeals")
async def create_scheduled_appeal(payload: ScheduledAppeal, user=Depends(require_admin)):
    seg = (payload.segment or "all").strip().lower()
    subject = (payload.subject or "").strip()
    message = (payload.message or "").strip()
    send_on = (payload.send_on or "").strip()
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message are required")
    try:
        day = datetime.strptime(send_on, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="send_on must be a valid date (YYYY-MM-DD)")
    if day < datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="Scheduled date cannot be in the past")
    repeat = (payload.repeat or "none").strip().lower()
    if repeat not in ("none", *REPEAT_MONTHS):
        raise HTTPException(status_code=400, detail="repeat must be none, monthly or quarterly")
    doc = {
        "id": str(uuid.uuid4()), "segment": seg, "subject": subject, "message": message,
        "send_on": send_on, "status": "scheduled", "repeat": repeat, "runs": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("user_id"),
        "created_by_name": user.get("name") or user.get("email") or "Admin",
        "sent_at": None, "result": None,
    }
    await db.scheduled_appeals.insert_one(dict(doc))
    return doc


@api_router.delete("/admin/scheduled-appeals/{sid}")
async def delete_scheduled_appeal(sid: str, user=Depends(require_admin)):
    res = await db.scheduled_appeals.delete_one({"id": sid, "status": "scheduled"})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scheduled appeal not found or already sent")
    return {"deleted": True}


async def _run_scheduled_appeals() -> dict:
    """Daily: dispatch any scheduled appeals whose send date has arrived."""
    today = datetime.now(timezone.utc).date().isoformat()
    due = await db.scheduled_appeals.find({"status": "scheduled", "send_on": {"$lte": today}}, {"_id": 0}).to_list(100)
    processed = 0
    for a in due:
        result = await _dispatch_segment_appeal(
            a["segment"], a["subject"], a["message"],
            a.get("created_by"), a.get("created_by_name") or "Scheduled",
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        summary = {"recipients": result.get("recipients", 0), "sent": result.get("sent", 0)}
        months = REPEAT_MONTHS.get(a.get("repeat") or "none")
        if months:
            nxt = datetime.strptime(a["send_on"], "%Y-%m-%d").date()
            while nxt.isoformat() <= today:
                nxt = _add_months(nxt, months)
            update = {"send_on": nxt.isoformat(), "sent_at": now_iso, "result": summary}
        else:
            update = {"status": "empty" if result.get("empty") else "sent", "sent_at": now_iso, "result": summary}
        await db.scheduled_appeals.update_one({"id": a["id"]}, {"$set": update, "$inc": {"runs": 1}})
        processed += 1
    return {"processed": processed}


# ---------- Events & RSVPs ----------
import secrets
from urllib.parse import quote as _urlquote
from zoneinfo import ZoneInfo

EVENT_TZ = ZoneInfo("America/New_York")
WAITLIST_MODES = ("auto", "invite")
INVITE_HOURS = 24


def _csv_safe(v) -> str:
    v = str(v or "")
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


class EventIn(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    time: str = ""
    location: str = ""
    description: str = ""
    category: str = ""
    image_url: str = ""
    capacity: int = 50
    waitlist_mode: str = "auto"


class RsvpIn(BaseModel):
    name: str
    email: str
    guests: int = 1


def _clean_event(p: EventIn) -> dict:
    title = (p.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Event title is required")
    try:
        datetime.strptime((p.date or "").strip(), "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Event date must be YYYY-MM-DD")
    if p.capacity < 1 or p.capacity > 100000:
        raise HTTPException(status_code=400, detail="Capacity must be at least 1")
    img = (p.image_url or "").strip()
    if img and not (img.startswith("/api/media/file/") or img.startswith("https://")):
        raise HTTPException(status_code=400, detail="Image must be an uploaded image or https URL")
    mode = (p.waitlist_mode or "auto").strip().lower()
    if mode not in WAITLIST_MODES:
        raise HTTPException(status_code=400, detail="Waitlist mode must be auto or invite")
    return {
        "title": title[:200], "date": p.date.strip(), "time": (p.time or "").strip()[:50],
        "location": (p.location or "").strip()[:300], "description": (p.description or "").strip()[:4000],
        "category": (p.category or "").strip()[:50], "image_url": img, "capacity": int(p.capacity),
        "waitlist_mode": mode,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _rsvp_totals(event_ids: list) -> dict:
    out = {}
    async for row in db.event_rsvps.aggregate([
        {"$match": {"event_id": {"$in": event_ids}}},
        {"$group": {"_id": "$event_id", "seats": {"$sum": "$guests"}, "rsvps": {"$sum": 1}}},
    ]):
        out[row["_id"]] = row
    return out


async def _held_seats(event_ids: list) -> dict:
    out = {}
    async for row in db.event_waitlist.aggregate([
        {"$match": {"event_id": {"$in": event_ids}, "status": "invited", "invite_expires": {"$gt": _now_iso()}}},
        {"$group": {"_id": "$event_id", "seats": {"$sum": "$guests"}}},
    ]):
        out[row["_id"]] = row["seats"]
    return out


async def _waitlist_counts(event_ids: list) -> dict:
    out = {}
    async for row in db.event_waitlist.aggregate([
        {"$match": {"event_id": {"$in": event_ids}, "status": {"$in": ["waiting", "invited"]}}},
        {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
    ]):
        out[row["_id"]] = row["n"]
    return out


async def _spots_left(ev: dict) -> int:
    taken = (await _rsvp_totals([ev["id"]])).get(ev["id"], {}).get("seats", 0)
    held = (await _held_seats([ev["id"]])).get(ev["id"], 0)
    return ev["capacity"] - taken - held


async def _events_with_counts(query: dict, sort_dir: int) -> list:
    items = await db.events.find(query, {"_id": 0}).sort("date", sort_dir).to_list(500)
    ids = [e["id"] for e in items]
    totals, held, wl = await _rsvp_totals(ids), await _held_seats(ids), await _waitlist_counts(ids)
    for e in items:
        t = totals.get(e["id"], {})
        e.setdefault("waitlist_mode", "auto")
        e["seats_taken"] = t.get("seats", 0)
        e["seats_held"] = held.get(e["id"], 0)
        e["rsvp_count"] = t.get("rsvps", 0)
        e["waitlist_count"] = wl.get(e["id"], 0)
        e["spots_left"] = max(0, e["capacity"] - e["seats_taken"] - e["seats_held"])
    return items


# --- Calendar helpers (event times are Eastern Time) ---
def _event_window(ev: dict):
    """Returns (start_utc, end_utc) for timed events, or None for all-day."""
    t = (ev.get("time") or "").strip()
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m", t, re.I)
    if m:
        h, mi = int(m.group(1)) % 12, int(m.group(2) or 0)
        if m.group(3).lower() == "p":
            h += 12
    else:
        m = re.match(r"^\s*(\d{1,2}):(\d{2})\b", t)
        if not m:
            return None
        h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        return None
    day = datetime.strptime(ev["date"], "%Y-%m-%d")
    start = day.replace(hour=h, minute=mi, tzinfo=EVENT_TZ).astimezone(timezone.utc)
    return start, start + timedelta(hours=2)


def _gcal_url(ev: dict) -> str:
    win = _event_window(ev)
    if win:
        dates = f"{win[0].strftime('%Y%m%dT%H%M%SZ')}/{win[1].strftime('%Y%m%dT%H%M%SZ')}"
    else:
        d = datetime.strptime(ev["date"], "%Y-%m-%d")
        dates = f"{d.strftime('%Y%m%d')}/{(d + timedelta(days=1)).strftime('%Y%m%d')}"
    details = (ev.get("description") or "")[:800] + f"\n\nDetails: {PUBLIC_APP_URL}/events"
    return ("https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={_urlquote(ev['title'])}&dates={dates}"
            f"&details={_urlquote(details)}&location={_urlquote(ev.get('location') or '')}")


def _ics_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _event_ics(ev: dict) -> str:
    win = _event_window(ev)
    if win:
        when = [f"DTSTART:{win[0].strftime('%Y%m%dT%H%M%SZ')}", f"DTEND:{win[1].strftime('%Y%m%dT%H%M%SZ')}"]
    else:
        d = datetime.strptime(ev["date"], "%Y-%m-%d")
        when = [f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}"]
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Caring Sisters Club//Events//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "BEGIN:VEVENT", f"UID:{ev['id']}@caringsistersclub", f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        *when, f"SUMMARY:{_ics_escape(ev['title'])}",
        f"DESCRIPTION:{_ics_escape((ev.get('description') or '')[:800])}",
        f"LOCATION:{_ics_escape(ev.get('location') or '')}", f"URL:{PUBLIC_APP_URL}/events",
        "BEGIN:VALARM", "TRIGGER:-PT2H", "ACTION:DISPLAY", f"DESCRIPTION:{_ics_escape(ev['title'])}", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


@api_router.get("/events/{eid}/calendar.ics")
async def event_calendar_file(eid: str):
    ev = await db.events.find_one({"id": eid}, {"_id": 0})
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    fname = re.sub(r"[^A-Za-z0-9]+", "-", ev["title"]).strip("-")[:60] or "event"
    return Response(content=_event_ics(ev), media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{fname}.ics"', "X-Content-Type-Options": "nosniff"})


@api_router.get("/events")
async def public_events():
    today = datetime.now(timezone.utc).date().isoformat()
    items = await _events_with_counts({"date": {"$gte": today}}, 1)
    for e in items:
        for k in ("created_by", "rsvp_count", "seats_held", "waitlist_count"):
            e.pop(k, None)
        e["gcal_url"] = _gcal_url(e)
    return {"items": items}


@api_router.get("/admin/events")
async def admin_list_events(user=Depends(require_admin)):
    return {"items": await _events_with_counts({}, -1)}


@api_router.post("/admin/events")
async def admin_create_event(payload: EventIn, user=Depends(require_admin)):
    doc = {"id": str(uuid.uuid4()), **_clean_event(payload), "created_at": _now_iso(), "created_by": user.get("email")}
    await db.events.insert_one(dict(doc))
    return doc


@api_router.put("/admin/events/{eid}")
async def admin_update_event(eid: str, payload: EventIn, background: BackgroundTasks, user=Depends(require_admin)):
    res = await db.events.update_one({"id": eid}, {"$set": {**_clean_event(payload), "updated_at": _now_iso()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    background.add_task(_process_waitlist, eid)
    return await db.events.find_one({"id": eid}, {"_id": 0})


@api_router.delete("/admin/events/{eid}")
async def admin_delete_event(eid: str, user=Depends(require_admin)):
    res = await db.events.delete_one({"id": eid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.event_rsvps.delete_many({"event_id": eid})
    await db.event_waitlist.delete_many({"event_id": eid})
    return {"deleted": True}


@api_router.get("/admin/events/{eid}/rsvps")
async def admin_event_rsvps(eid: str, user=Depends(require_admin)):
    items = await db.event_rsvps.find({"event_id": eid}, {"_id": 0, "cancel_token": 0}).sort("created_at", 1).to_list(5000)
    return {"items": items}


@api_router.get("/admin/events/{eid}/waitlist")
async def admin_event_waitlist(eid: str, user=Depends(require_admin)):
    items = await db.event_waitlist.find({"event_id": eid}, {"_id": 0, "invite_token": 0}).sort("created_at", 1).to_list(5000)
    return {"items": items}


@api_router.delete("/admin/events/{eid}/waitlist/{wid}")
async def admin_remove_waitlist(eid: str, wid: str, background: BackgroundTasks, user=Depends(require_admin)):
    res = await db.event_waitlist.update_one({"id": wid, "event_id": eid, "status": {"$in": ["waiting", "invited"]}},
                                             {"$set": {"status": "removed", "updated_at": _now_iso()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    background.add_task(_process_waitlist, eid)
    return {"removed": True}


@api_router.get("/admin/events/{eid}/rsvps/export")
async def admin_export_rsvps(eid: str, user=Depends(require_admin)):
    ev = await db.events.find_one({"id": eid}, {"_id": 0})
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    items = await db.event_rsvps.find({"event_id": eid}, {"_id": 0}).sort("created_at", 1).to_list(5000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Email", "Guests", "RSVP Date", "Source", "Reminder Sent"])
    for r in items:
        w.writerow([_csv_safe(r.get("name")), _csv_safe(r.get("email")), r.get("guests", 1), r.get("created_at", "")[:10],
                    r.get("source", "direct"), "yes" if r.get("reminder_sent") else "no"])
    fname = re.sub(r"[^A-Za-z0-9]+", "-", ev["title"]).strip("-")[:60] or "event"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="rsvps-{fname}.csv"'})


@api_router.delete("/admin/events/{eid}/rsvps/{rid}")
async def admin_delete_rsvp(eid: str, rid: str, background: BackgroundTasks, user=Depends(require_admin)):
    res = await db.event_rsvps.delete_one({"id": rid, "event_id": eid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="RSVP not found")
    background.add_task(_process_waitlist, eid)
    return {"deleted": True}


def _fmt_event_date(d: str) -> str:
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%A, %B %-d, %Y")
    except ValueError:
        return d


_EVENT_COPY = {
    "confirm": ("RSVP Confirmed", "You're registered!", "Thank you for your RSVP to <strong>{t}</strong>. Your spot is confirmed."),
    "reminder": ("Event Reminder", "See you tomorrow!", "This is a friendly reminder that <strong>{t}</strong> is tomorrow. We can't wait to see you."),
    "promoted": ("Off the Waitlist", "Great news, you're in!", "A spot opened up at <strong>{t}</strong> and we've moved you off the waitlist. Your spot is now confirmed."),
    "invite": ("A Spot Opened Up", "A spot is waiting for you!", "A spot opened up at <strong>{t}</strong>. Claim it within " + str(INVITE_HOURS) + " hours, after which it will be offered to the next person on the waitlist."),
    "waitlist": ("You're on the Waitlist", "You're on the waitlist", "<strong>{t}</strong> is currently full, so we've added you to the waitlist. We'll email you the moment a spot opens."),
}


def _btn(href: str, label: str, primary: bool = False) -> str:
    style = ("background:#B4247E;color:#fff;" if primary else "background:#fff;color:#3B0A2E;border:1px solid #e3d3dd;")
    return (f'<a href="{href}" style="display:inline-block;{style}text-decoration:none;font-weight:bold;font-size:13px;'
            f'padding:11px 20px;border-radius:999px;margin:0 8px 8px 0">{label}</a>')


def _event_email_html(name: str, ev: dict, guests: int, kind: str = "confirm", action_url: str = None) -> str:
    badge, heading, intro = _EVENT_COPY[kind]
    intro = intro.format(t=_esc(ev["title"]))
    rows = [("Date", _fmt_event_date(ev["date"])), ("Time", f'{ev["time"]} ET' if ev.get("time") else ""),
            ("Location", ev.get("location")), ("Party size", f'{guests} {"guest" if guests == 1 else "guests"}')]
    details = "".join(
        f'<tr><td style="padding:8px 18px;font-size:13px;color:#6b5560">{k}</td><td style="padding:8px 18px;font-size:14px;color:#3B0A2E;font-weight:bold">{_esc(str(v))}</td></tr>'
        for k, v in rows if v
    )
    attending = kind in ("confirm", "reminder", "promoted")
    buttons = ""
    if kind == "invite" and action_url:
        buttons = _btn(action_url, "Claim My Spot", primary=True)
    elif attending:
        buttons = (_btn(_gcal_url(ev), "Add to Google Calendar", primary=True)
                   + _btn(f"{PUBLIC_APP_URL}/api/events/{ev['id']}/calendar.ics", "Add to Apple / Outlook"))
    else:
        buttons = _btn(f"{PUBLIC_APP_URL}/events", "View Events", primary=True)
    footer_note = ""
    if attending and action_url:
        footer_note = f'Can\'t make it after all? <a href="{action_url}" style="color:#B4247E">Cancel your RSVP</a> so a sister on the waitlist can take your spot.<br/><br/>'
    elif attending:
        footer_note = "If your plans change, simply reply to this email to let us know.<br/><br/>"
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header(badge) +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 14px">{heading}</h1>'
        f'<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 6px">Dear {_esc(name)},</p>'
        f'<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">{intro}</p>'
        f'<table role="presentation" width="100%" style="background:#faf2f7;border-radius:12px;margin:0 0 20px">{details}</table>'
        f'<div>{buttons}</div>'
        f'<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">{footer_note}With warmth,<br/>The Caring Sisters Club</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you RSVP\'d on our website. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


_EVENT_SUBJECTS = {
    "confirm": "You're registered: {t}", "reminder": "Reminder: {t} is tomorrow", "promoted": "You're in! {t}",
    "invite": "A spot opened up: {t}", "waitlist": "You're on the waitlist: {t}",
}


async def _send_event_email(person: dict, ev: dict, kind: str, action_url: str = None):
    try:
        return await send_email(to=person["email"], subject=_EVENT_SUBJECTS[kind].format(t=ev["title"])[:150],
                                html=_event_email_html(person["name"], ev, person.get("guests", 1), kind, action_url))
    except Exception as e:
        logging.error(f"Event email ({kind}) failed: {e}")
        return None


def _token_url(token: str) -> str:
    return f"{PUBLIC_APP_URL}/rsvp?token={token}"


async def _insert_rsvp(ev: dict, name: str, email: str, guests: int, source: str) -> dict:
    rsvp = {"id": str(uuid.uuid4()), "event_id": ev["id"], "name": name[:200], "email": email, "guests": guests,
            "created_at": _now_iso(), "reminder_sent": False, "source": source, "cancel_token": secrets.token_urlsafe(24)}
    await db.event_rsvps.insert_one(dict(rsvp))
    return rsvp


def _validate_rsvp_input(payload: RsvpIn):
    name, email = _validate_person({"name": payload.name, "email": payload.email})
    guests = int(payload.guests or 1)
    if guests < 1 or guests > 10:
        raise HTTPException(status_code=400, detail="Party size must be between 1 and 10.")
    return name.strip(), email.lower(), guests


async def _open_event(eid: str) -> dict:
    ev = await db.events.find_one({"id": eid}, {"_id": 0})
    if not ev or ev["date"] < datetime.now(timezone.utc).date().isoformat():
        raise HTTPException(status_code=404, detail="This event is no longer open for RSVPs.")
    return ev


@api_router.post("/events/{eid}/rsvp")
async def create_rsvp(eid: str, payload: RsvpIn, request: Request, background: BackgroundTasks):
    _rate_limit(request, "rsvp", max_hits=5, window_s=60)
    name, email, guests = _validate_rsvp_input(payload)
    ev = await _open_event(eid)
    if await db.event_rsvps.find_one({"event_id": eid, "email": email}):
        raise HTTPException(status_code=409, detail="You're already registered for this event with that email.")
    left = await _spots_left(ev)
    if left <= 0:
        raise HTTPException(status_code=409, detail="Sorry, this event is full. You can join the waitlist instead.")
    if guests > left:
        raise HTTPException(status_code=409, detail=f"Only {left} spot{'s' if left != 1 else ''} left. Reduce your party size or join the waitlist.")
    rsvp = await _insert_rsvp(ev, name, email, guests, "direct")
    sub_data = {"event": ev["title"], "event_date": ev["date"], "name": rsvp["name"], "email": email, "guests": guests}
    await db.submissions.insert_one({"id": str(uuid.uuid4()), "type": "rsvp", "data": sub_data, "read": False, "created_at": rsvp["created_at"]})
    background.add_task(_send_event_email, rsvp, ev, "confirm", _token_url(rsvp["cancel_token"]))
    background.add_task(_notify_staff, "rsvp", sub_data)
    return {"id": rsvp["id"], "event": ev["title"], "spots_left": left - guests,
            "gcal_url": _gcal_url(ev), "ics_url": f"/api/events/{eid}/calendar.ics"}


@api_router.post("/events/{eid}/waitlist")
async def join_waitlist(eid: str, payload: RsvpIn, request: Request, background: BackgroundTasks):
    _rate_limit(request, "waitlist", max_hits=5, window_s=60)
    name, email, guests = _validate_rsvp_input(payload)
    ev = await _open_event(eid)
    if await db.event_rsvps.find_one({"event_id": eid, "email": email}):
        raise HTTPException(status_code=409, detail="You're already registered for this event with that email.")
    if await db.event_waitlist.find_one({"event_id": eid, "email": email, "status": {"$in": ["waiting", "invited"]}}):
        raise HTTPException(status_code=409, detail="You're already on the waitlist for this event.")
    entry = {"id": str(uuid.uuid4()), "event_id": eid, "name": name[:200], "email": email, "guests": guests,
             "status": "waiting", "created_at": _now_iso()}
    await db.event_waitlist.insert_one(dict(entry))
    position = await db.event_waitlist.count_documents({"event_id": eid, "status": {"$in": ["waiting", "invited"]}, "created_at": {"$lte": entry["created_at"]}})
    sub_data = {"event": ev["title"], "event_date": ev["date"], "name": entry["name"], "email": email, "guests": guests, "list": "waitlist"}
    await db.submissions.insert_one({"id": str(uuid.uuid4()), "type": "rsvp", "data": sub_data, "read": False, "created_at": entry["created_at"]})
    background.add_task(_send_event_email, entry, ev, "waitlist")
    background.add_task(_notify_staff, "rsvp", sub_data)
    background.add_task(_process_waitlist, eid)
    return {"id": entry["id"], "position": position}


async def _process_waitlist(eid: str) -> dict:
    """Expire stale invites, then fill open seats from the waitlist in sign-up order."""
    result = {"promoted": 0, "invited": 0, "expired": 0}
    try:
        ev = await db.events.find_one({"id": eid}, {"_id": 0})
        if not ev:
            return result
        now = datetime.now(timezone.utc)
        exp = await db.event_waitlist.update_many(
            {"event_id": eid, "status": "invited", "invite_expires": {"$lte": now.isoformat()}},
            {"$set": {"status": "expired", "updated_at": now.isoformat()}})
        result["expired"] = exp.modified_count
        if ev["date"] < now.date().isoformat():
            return result
        left = await _spots_left(ev)
        if left <= 0:
            return result
        waiting = await db.event_waitlist.find({"event_id": eid, "status": "waiting"}, {"_id": 0}).sort("created_at", 1).to_list(1000)
        for w in waiting:
            if left <= 0:
                break
            if w["guests"] > left:
                continue
            if ev.get("waitlist_mode") == "invite":
                token = secrets.token_urlsafe(24)
                res = await db.event_waitlist.update_one({"id": w["id"], "status": "waiting"}, {"$set": {
                    "status": "invited", "invite_token": token, "invited_at": now.isoformat(),
                    "invite_expires": (now + timedelta(hours=INVITE_HOURS)).isoformat()}})
                if res.modified_count:
                    await _send_event_email(w, ev, "invite", _token_url(token))
                    result["invited"] += 1
            else:
                res = await db.event_waitlist.update_one({"id": w["id"], "status": "waiting"},
                                                         {"$set": {"status": "promoted", "promoted_at": now.isoformat()}})
                if res.modified_count:
                    rsvp = await _insert_rsvp(ev, w["name"], w["email"], w["guests"], "waitlist")
                    await _send_event_email(rsvp, ev, "promoted", _token_url(rsvp["cancel_token"]))
                    result["promoted"] += 1
            left -= w["guests"]
    except Exception as e:
        logging.error(f"Waitlist processing failed for {eid}: {e}")
    return result


async def _process_all_waitlists():
    for eid in await db.event_waitlist.distinct("event_id", {"status": {"$in": ["waiting", "invited"]}}):
        await _process_waitlist(eid)


async def _resolve_token(token: str):
    if not token or len(token) > 100:
        return None, None, None
    r = await db.event_rsvps.find_one({"cancel_token": token}, {"_id": 0})
    if r:
        return "cancel", r, await db.events.find_one({"id": r["event_id"]}, {"_id": 0})
    w = await db.event_waitlist.find_one({"invite_token": token}, {"_id": 0})
    if w:
        return "claim", w, await db.events.find_one({"id": w["event_id"]}, {"_id": 0})
    return None, None, None


def _claim_state(w: dict) -> str:
    if w["status"] == "invited":
        return "open" if w.get("invite_expires", "") > _now_iso() else "expired"
    return {"promoted": "claimed"}.get(w["status"], "expired")


@api_router.get("/events/token/{token}")
async def event_token_info(token: str, request: Request):
    _rate_limit(request, "rsvp-token", max_hits=20, window_s=60)
    kind, person, ev = await _resolve_token(token)
    if not kind or not ev:
        raise HTTPException(status_code=404, detail="This link is invalid or has already been used.")
    info = {"kind": kind, "name": person["name"], "guests": person["guests"],
            "event": {k: ev.get(k) for k in ("id", "title", "date", "time", "location")}}
    if kind == "claim":
        info["state"] = _claim_state(person)
        info["expires_at"] = person.get("invite_expires")
    return info


@api_router.post("/events/token/{token}")
async def event_token_action(token: str, request: Request, background: BackgroundTasks):
    _rate_limit(request, "rsvp-token", max_hits=20, window_s=60)
    kind, person, ev = await _resolve_token(token)
    if not kind or not ev:
        raise HTTPException(status_code=404, detail="This link is invalid or has already been used.")
    if kind == "cancel":
        await db.event_rsvps.delete_one({"id": person["id"]})
        background.add_task(_process_waitlist, ev["id"])
        return {"done": "cancelled"}
    state = _claim_state(person)
    if state != "open":
        raise HTTPException(status_code=410, detail="Sorry, this invitation has expired." if state == "expired" else "You've already claimed this spot.")
    if ev["date"] < datetime.now(timezone.utc).date().isoformat():
        raise HTTPException(status_code=410, detail="This event has already taken place.")
    res = await db.event_waitlist.update_one({"id": person["id"], "status": "invited"},
                                             {"$set": {"status": "promoted", "promoted_at": _now_iso()}})
    if not res.modified_count:
        raise HTTPException(status_code=409, detail="You've already claimed this spot.")
    rsvp = await _insert_rsvp(ev, person["name"], person["email"], person["guests"], "waitlist")
    background.add_task(_send_event_email, rsvp, ev, "confirm", _token_url(rsvp["cancel_token"]))
    return {"done": "claimed", "gcal_url": _gcal_url(ev), "ics_url": f"/api/events/{ev['id']}/calendar.ics"}


async def _send_event_reminders() -> dict:
    """Daily: remind guests of events happening tomorrow (once per RSVP)."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    sent = 0
    async for ev in db.events.find({"date": tomorrow}, {"_id": 0}):
        async for r in db.event_rsvps.find({"event_id": ev["id"], "reminder_sent": {"$ne": True}}, {"_id": 0}):
            res = await _send_event_email(r, ev, "reminder", _token_url(r["cancel_token"]) if r.get("cancel_token") else None)
            await db.event_rsvps.update_one({"id": r["id"]}, {"$set": {"reminder_sent": True, "reminder_ok": res is not None, "reminder_at": _now_iso()}})
            sent += 1 if res is not None else 0
    return {"sent": sent}


# ---------- Donor Self-Service (Stripe Customer Portal) ----------
class ManageLinkIn(BaseModel):
    email: str


class PortalIn(BaseModel):
    token: str


async def _monthly_sub_for(email: str):
    txn = await db.payment_transactions.find_one(
        {"donor_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}, "frequency": "monthly",
         "payment_status": "paid", "stripe_subscription_id": {"$nin": [None, ""]}},
        {"_id": 0, "stripe_subscription_id": 1}, sort=[("created_at", -1)])
    return txn["stripe_subscription_id"] if txn else None


async def _create_manage_token(email: str, kind: str) -> str:
    """All tokens are single-use. 'request' expires in 1 hour; 'receipt' in 30 days."""
    token = secrets.token_urlsafe(32)
    ttl = timedelta(hours=1) if kind == "request" else timedelta(days=30)
    await db.donor_manage_tokens.insert_one({
        "token": token, "email": email.lower(), "kind": kind, "used": False,
        "created_at": _now_iso(), "expires_at": (datetime.now(timezone.utc) + ttl).isoformat()})
    return token


async def _manage_url(email: str, kind: str = "receipt") -> str:
    return f"{PUBLIC_APP_URL}/manage-gift?token={await _create_manage_token(email, kind)}"


def _manage_link_email_html(name: str, url: str) -> str:
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Manage Your Monthly Gift") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 14px">Hi {_esc(name)},</h1>'
        '<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">You asked to manage your monthly gift to The Caring Sisters Club. '
        'Use the secure button below to update your payment method, view past invoices, or cancel. The link works once and expires in 1 hour.</p>'
        + _btn(url, "Manage My Monthly Gift", primary=True) +
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">Payments are handled securely by Stripe. If you didn\'t request this, you can safely ignore this email.<br/><br/>With gratitude,<br/>The Caring Sisters Club</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


@api_router.post("/donor/manage-link")
async def donor_manage_link(payload: ManageLinkIn, request: Request, background: BackgroundTasks):
    _rate_limit(request, "manage-link", max_hits=3, window_s=300)
    email = (payload.email or "").strip().lower()
    if not _EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if await _monthly_sub_for(email):
        async def _send():
            try:
                txn = await db.payment_transactions.find_one({"donor_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}},
                                                             {"_id": 0, "donor_name": 1})
                name = ((txn or {}).get("donor_name") or "").strip() or "Friend"
                url = await _manage_url(email, "request")
                await send_email(to=email, subject="Your secure link to manage your monthly gift", html=_manage_link_email_html(name, url))
            except Exception as e:
                logging.error(f"Manage-link email failed: {e}")
        background.add_task(_send)
    return {"message": "If a monthly gift is linked to that email, we've sent a secure link. Please check your inbox."}


async def _portal_configuration() -> str:
    mode = "live" if (stripe.api_key or "").startswith("sk_live") else "test"
    key = f"stripe_portal_config_{mode}"
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0, key: 1}) or {}
    if doc.get(key):
        return doc[key]
    cfg = stripe.billing_portal.Configuration.create(
        business_profile={"headline": "The Caring Sisters Club: manage your monthly gift"},
        features={
            "payment_method_update": {"enabled": True},
            "invoice_history": {"enabled": True},
            "subscription_cancel": {"enabled": True, "mode": "at_period_end",
                                    "cancellation_reason": {"enabled": True, "options": ["too_expensive", "unused", "other"]}},
            "customer_update": {"enabled": False},
        },
        default_return_url=f"{PUBLIC_APP_URL}/manage-gift?done=1",
    )
    await db.settings.update_one({"key": "site"}, {"$set": {key: cfg.id}}, upsert=True)
    return cfg.id


@api_router.get("/donor/manage-token/{token}")
async def donor_manage_token_info(token: str, request: Request):
    _rate_limit(request, "manage-portal", max_hits=20, window_s=60)
    t = await db.donor_manage_tokens.find_one({"token": token}, {"_id": 0})
    valid = bool(t and not t["used"] and t["expires_at"] > _now_iso())
    return {"valid": valid}


@api_router.post("/donor/portal")
async def donor_portal(payload: PortalIn, request: Request):
    _rate_limit(request, "manage-portal", max_hits=10, window_s=60)
    t = await db.donor_manage_tokens.find_one({"token": (payload.token or "")[:100]}, {"_id": 0})
    if not t or t["expires_at"] <= _now_iso() or t["used"]:
        raise HTTPException(status_code=410, detail="This link has expired or was already used. Please request a new one.")
    claimed = await db.donor_manage_tokens.update_one({"token": t["token"], "used": False}, {"$set": {"used": True, "used_at": _now_iso()}})
    if not claimed.modified_count:
        raise HTTPException(status_code=410, detail="This link has expired or was already used. Please request a new one.")
    sub_id = await _monthly_sub_for(t["email"])
    if not sub_id:
        raise HTTPException(status_code=404, detail="We couldn't find a monthly gift for this email.")
    try:
        customer = stripe.Subscription.retrieve(sub_id).get("customer")
        cfg = await _portal_configuration()
        try:
            session = stripe.billing_portal.Session.create(customer=customer, configuration=cfg,
                                                           return_url=f"{PUBLIC_APP_URL}/manage-gift?done=1")
        except stripe.error.InvalidRequestError:
            await db.settings.update_one({"key": "site"}, {"$unset": {f"stripe_portal_config_{'live' if (stripe.api_key or '').startswith('sk_live') else 'test'}": ""}})
            session = stripe.billing_portal.Session.create(customer=customer, configuration=await _portal_configuration(),
                                                           return_url=f"{PUBLIC_APP_URL}/manage-gift?done=1")
    except Exception as e:
        logging.error(f"Stripe portal session failed: {e}")
        raise HTTPException(status_code=424, detail="We couldn't open the secure billing page right now. Please try again shortly.")
    return {"url": session.url}


# ---------- Transparency (editable) ----------
SPEND_COLORS = ("var(--csc-magenta)", "var(--csc-plum-soft)", "var(--csc-gold)", "#3B0A2E", "#D14FA0", "#8a6a2c")
REPORT_TYPES = ("990", "annual", "audit", "other")
DEFAULT_TRANSPARENCY = {
    "headline_text": "of every dollar goes directly to programs and services for our sisters.",
    "breakdown": [
        {"label": "Programs & Services", "pct": 82, "color": "var(--csc-magenta)"},
        {"label": "Administration", "pct": 11, "color": "var(--csc-plum-soft)"},
        {"label": "Fundraising", "pct": 7, "color": "var(--csc-gold)"},
    ],
    "stats": [
        {"value": "2,400+", "label": "Sisters in our network"},
        {"value": "38", "label": "Community programs delivered"},
        {"value": "$610K", "label": "Granted to member initiatives"},
        {"value": "14", "label": "Cities across the Diaspora"},
    ],
    "financials": [],
    "reports": [],
    "updated_at": None,
}


class SpendItem(BaseModel):
    label: str
    pct: float
    color: str = "var(--csc-magenta)"


class StatItem(BaseModel):
    value: str
    label: str


class FinancialYear(BaseModel):
    year: str
    revenue: float = 0
    expenses: float = 0
    program_expenses: float = 0


class ReportItem(BaseModel):
    id: Optional[str] = None
    year: str
    type: str = "annual"
    title: str = ""
    url: str
    size: str = ""


class TransparencyIn(BaseModel):
    headline_text: str = ""
    breakdown: List[SpendItem] = []
    stats: List[StatItem] = []
    financials: List[FinancialYear] = []
    reports: List[ReportItem] = []


async def _get_transparency() -> dict:
    doc = await db.settings.find_one({"key": "transparency"}, {"_id": 0, "key": 0}) or {}
    return {k: doc.get(k, v) for k, v in DEFAULT_TRANSPARENCY.items()}


@api_router.get("/transparency")
async def public_transparency():
    return await _get_transparency()


@api_router.put("/admin/transparency")
async def admin_update_transparency(payload: TransparencyIn, user=Depends(require_admin)):
    bad = lambda msg: HTTPException(status_code=400, detail=msg)  # noqa: E731
    if not payload.breakdown or len(payload.breakdown) > 8:
        raise bad("Add between 1 and 8 spending categories.")
    for b in payload.breakdown:
        if not b.label.strip() or not (0 <= b.pct <= 100):
            raise bad("Each spending category needs a name and a percentage between 0 and 100.")
        if b.color not in SPEND_COLORS:
            raise bad("Invalid category color.")
    if abs(sum(b.pct for b in payload.breakdown) - 100) > 0.5:
        raise bad(f"Spending percentages must add up to 100% (currently {sum(b.pct for b in payload.breakdown):g}%).")
    if len(payload.stats) > 8 or any(not s.value.strip() or not s.label.strip() for s in payload.stats):
        raise bad("Each impact stat needs a value and a label (max 8).")
    for f in payload.financials:
        if not re.match(r"^\d{4}$", f.year.strip()) or min(f.revenue, f.expenses, f.program_expenses) < 0:
            raise bad("Financial years must be 4 digits with non-negative amounts.")
    reports = []
    for r in payload.reports:
        if not re.match(r"^\d{4}$", r.year.strip()) or r.type not in REPORT_TYPES:
            raise bad("Each report needs a 4-digit year and a valid type.")
        if not (r.url.startswith("/api/media/file/") or r.url.startswith("https://")):
            raise bad("Report file must be an uploaded document or https link.")
        reports.append({"id": r.id or str(uuid.uuid4()), "year": r.year.strip(), "type": r.type,
                        "title": r.title.strip()[:200], "url": r.url.strip(), "size": r.size.strip()[:20]})
    doc = {
        "headline_text": payload.headline_text.strip()[:200] or DEFAULT_TRANSPARENCY["headline_text"],
        "breakdown": [{"label": b.label.strip()[:60], "pct": round(b.pct, 1), "color": b.color} for b in payload.breakdown],
        "stats": [{"value": s.value.strip()[:20], "label": s.label.strip()[:60]} for s in payload.stats],
        "financials": sorted([{"year": f.year.strip(), "revenue": round(f.revenue, 2), "expenses": round(f.expenses, 2),
                               "program_expenses": round(f.program_expenses, 2)} for f in payload.financials],
                             key=lambda f: f["year"], reverse=True),
        "reports": sorted(reports, key=lambda r: r["year"], reverse=True),
        "updated_at": _now_iso(), "updated_by": user.get("email"),
    }
    await db.settings.update_one({"key": "transparency"}, {"$set": doc}, upsert=True)
    return await _get_transparency()


# ---------- Monthly cancellation alerts ----------
class ThankNoteIn(BaseModel):
    subject: str
    message: str


def _default_thank_note(name: str) -> dict:
    return {
        "subject": "Thank you for being part of our sisterhood",
        "message": (f"Dear {name},\n\nWe noticed your monthly gift has ended, and we simply wanted to say thank you. "
                    "Every month you gave helped women across the Diaspora find mentorship, stable housing and community care.\n\n"
                    "You'll always be part of the Caring Sisters family, and our door is open whenever you'd like to reconnect, "
                    "volunteer or join us at an event.\n\nWith heartfelt gratitude,\nThe Caring Sisters Club"),
    }


def _note_email_html(message: str) -> str:
    body = _esc(message).replace("\n", "<br/>")
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("With Gratitude") +
        f'<tr><td style="padding:32px;font-family:Arial,sans-serif;font-size:15px;line-height:1.75;color:#4a3340">{body}</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">Sent by The Caring Sisters Club. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


def _cancel_alert_html(c: dict, url: str) -> str:
    ends = c.get("ends_on") or "now"
    rows = "".join(
        f'<tr><td style="padding:7px 16px;font-size:13px;color:#6b5560">{k}</td><td style="padding:7px 16px;font-size:14px;color:#3B0A2E;font-weight:bold">{_esc(str(v))}</td></tr>'
        for k, v in [("Donor", c["name"]), ("Email", c["email"]), ("Monthly gift", f"${c['amount']:,.2f}"), ("Gift ends", ends),
                     ("Reason", c.get("reason") or "Not given")]
    )
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:24px 12px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Donor Alert") +
        '<tr><td style="padding:28px;font-family:Arial,sans-serif;color:#241019">'
        '<h2 style="font-family:Georgia,serif;color:#3B0A2E;font-size:21px;margin:0 0 12px">A monthly donor cancelled</h2>'
        f'<table role="presentation" width="100%" style="background:#faf2f7;border-radius:10px;margin:0 0 18px">{rows}</table>'
        '<p style="font-size:13.5px;line-height:1.6;color:#4a3340;margin:0 0 16px">A warm thank-you goes a long way. Review a ready-made note, personalise it, and send it in one click.</p>'
        + _btn(url, "Send Thank-You Note", primary=True) +
        '</td></tr></table></td></tr></table>'
    )


async def _handle_cancellation(sub: dict):
    """Idempotent: record a monthly cancellation once and alert staff."""
    sub_id = sub.get("id")
    if not sub_id or await db.cancellations.find_one({"sub_id": sub_id}):
        return False
    orig = await db.payment_transactions.find_one({"stripe_subscription_id": sub_id}, {"_id": 0}, sort=[("created_at", 1)])
    if not orig or not orig.get("donor_email"):
        return False
    end_ts = sub.get("cancel_at") or sub.get("ended_at") or sub.get("canceled_at")
    c = {
        "id": str(uuid.uuid4()), "sub_id": sub_id, "email": orig["donor_email"].lower(),
        "name": (orig.get("donor_name") or "").strip() or "Friend", "amount": float(orig.get("amount") or 0),
        "ends_on": datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%B %-d, %Y") if end_ts else "",
        "reason": ((sub.get("cancellation_details") or {}).get("feedback") or "").replace("_", " "),
        "token": secrets.token_urlsafe(24), "thanked": False, "created_at": _now_iso(),
    }
    try:
        await db.cancellations.insert_one(dict(c))
    except Exception:
        return False
    to = (await _get_settings()).get("staff_notify_email")
    if to:
        try:
            await send_email(to=to, subject=f"Monthly donor cancelled: {c['name']} (${c['amount']:,.0f}/mo)"[:150],
                             html=_cancel_alert_html(c, f"{PUBLIC_APP_URL}/cancel-thanks?token={c['token']}"))
        except Exception as e:
            logging.error(f"Cancellation alert failed: {e}")
    return True


async def _check_cancellations() -> int:
    """Daily safety net in case a webhook was missed."""
    found = 0
    sub_ids = await db.payment_transactions.distinct("stripe_subscription_id", {"frequency": "monthly", "payment_status": "paid"})
    done = set(await db.cancellations.distinct("sub_id"))
    for sub_id in sub_ids:
        if not sub_id or sub_id in done:
            continue
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            if sub.get("status") == "canceled" or sub.get("cancel_at_period_end") or sub.get("cancel_at"):
                found += 1 if await _handle_cancellation(sub) else 0
        except Exception as e:
            logging.warning(f"Cancellation check failed for {sub_id}: {e}")
    return found


async def _find_cancellation(token: str):
    c = await db.cancellations.find_one({"token": (token or "")[:100]}, {"_id": 0}) if token else None
    if not c:
        raise HTTPException(status_code=404, detail="This link is invalid.")
    return c


@api_router.get("/cancellations/token/{token}")
async def cancellation_token_info(token: str, request: Request):
    _rate_limit(request, "cancel-thanks", max_hits=20, window_s=60)
    c = await _find_cancellation(token)
    return {"name": c["name"], "email": c["email"], "amount": c["amount"], "ends_on": c["ends_on"], "reason": c.get("reason"),
            "thanked": c["thanked"], "thanked_at": c.get("thanked_at"), **_default_thank_note(c["name"])}


@api_router.post("/cancellations/token/{token}")
async def cancellation_send_thanks(token: str, payload: ThankNoteIn, request: Request):
    _rate_limit(request, "cancel-thanks", max_hits=20, window_s=60)
    c = await _find_cancellation(token)
    subject, message = payload.subject.strip()[:150], payload.message.strip()[:5000]
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message are required.")
    res = await db.cancellations.update_one({"id": c["id"], "thanked": False}, {"$set": {"thanked": True, "thanked_at": _now_iso()}})
    if not res.modified_count:
        raise HTTPException(status_code=409, detail="A thank-you note was already sent to this donor.")
    try:
        sent = await send_email(to=c["email"], subject=subject, html=_note_email_html(message))
    except ValueError as e:
        sent, err = None, str(e)
    else:
        err = "Email provider rejected the message."
    if sent is None:
        await db.cancellations.update_one({"id": c["id"]}, {"$set": {"thanked": False}, "$unset": {"thanked_at": ""}})
        raise HTTPException(status_code=424, detail=f"Note not sent: {err}")
    return {"sent": True}


# ---------- Programs & Initiatives (editable) ----------
DEFAULT_PROGRAM_CATEGORIES = ["Professional", "Philanthropy", "Housing", "Community"]


class ImpactItem(BaseModel):
    value: str
    label: str


class GalleryItem(BaseModel):
    url: str
    caption: str = ""
    added_at: Optional[str] = None


class TestimonialItem(BaseModel):
    id: Optional[str] = None
    quote: str
    name: str
    role: str = ""
    photo_url: str = ""
    added_at: Optional[str] = None


def _ok_img(url: str) -> bool:
    return not url or url.startswith("/api/media/file/") or url.startswith("https://")


def _clean_testimonials(items: list, limit: int) -> list:
    out = []
    for t in items[:limit]:
        if not t.quote.strip() or not t.name.strip():
            raise HTTPException(status_code=400, detail="Each testimonial needs a quote and a name.")
        if not _ok_img(t.photo_url.strip()):
            raise HTTPException(status_code=400, detail="Testimonial photo must be an uploaded image or https URL")
        out.append({"id": t.id or str(uuid.uuid4()), "quote": t.quote.strip()[:600], "name": t.name.strip()[:80],
                    "role": t.role.strip()[:80], "photo_url": t.photo_url.strip(), "added_at": t.added_at or _now_iso()})
    return out


class ProgramIn(BaseModel):
    gallery: List[GalleryItem] = []
    testimonials: List[TestimonialItem] = []
    home_testimonial_ids: List[str] = []
    title: str
    category: str = ""
    image_url: str = ""
    summary: str = ""
    body: str = ""
    goals: List[str] = []
    impact: List[ImpactItem] = []
    cta_text: str = "Get Involved"
    cta_link: str = "/volunteer"
    published: bool = True
    capacity: int = 0
    waitlist_mode: str = "claim"


class CategoriesIn(BaseModel):
    categories: List[str]


class ReorderIn(BaseModel):
    ids: List[str]


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80] or "program"


async def _unique_slug(title: str, exclude_id: str = None) -> str:
    base, n = _slugify(title), 1
    slug = base
    while await db.programs.find_one({"slug": slug, "id": {"$ne": exclude_id}}):
        n += 1
        slug = f"{base}-{n}"
    return slug


def _clean_gallery(items: list) -> list:
    out = []
    for g in items[:24]:
        url = g.url.strip()
        if not url or not _ok_img(url):
            raise HTTPException(status_code=400, detail="Gallery photos must be uploaded images or https URLs")
        out.append({"url": url, "caption": g.caption.strip()[:150], "added_at": g.added_at or _now_iso()})
    return out


def _clean_program(p: ProgramIn) -> dict:
    title = p.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Program title is required")
    img = p.image_url.strip()
    if img and not (img.startswith("/api/media/file/") or img.startswith("https://")):
        raise HTTPException(status_code=400, detail="Image must be an uploaded image or https URL")
    link = p.cta_link.strip() or "/volunteer"
    if not (re.match(r"^/[A-Za-z0-9/_\-?=&#.]*$", link) or link.startswith("https://")) or link.startswith("//"):
        raise HTTPException(status_code=400, detail="Button link must be a site path like /donate or an https:// URL")
    return {
        "title": title[:150], "category": p.category.strip()[:50], "image_url": img, "summary": p.summary.strip()[:600],
        "body": p.body.strip()[:10000], "goals": [g.strip()[:200] for g in p.goals if g.strip()][:12],
        "impact": [{"value": i.value.strip()[:20], "label": i.label.strip()[:60]} for i in p.impact if i.value.strip() and i.label.strip()][:6],
        "cta_text": p.cta_text.strip()[:40] or "Get Involved", "cta_link": link, "published": bool(p.published),
        "gallery": _clean_gallery(p.gallery), "testimonials": _clean_testimonials(p.testimonials, 6),
        "home_testimonial_ids": [i[:64] for i in p.home_testimonial_ids][:6],
        "capacity": max(0, min(int(p.capacity or 0), 100000)),
        "waitlist_mode": p.waitlist_mode if p.waitlist_mode in WAITLIST_MODES else "claim",
    }


async def _seats_taken(p: dict) -> int:
    return await db.submissions.count_documents({
        "type": "program_signup", "stage": {"$ne": "not_fit"},
        "$and": [{"$or": [{"program_id": p["id"]}, {"program_id": {"$exists": False}, "data.program_slug": p["slug"]}]},
                 {"$or": [{"waitlist": {"$ne": True}}, {"stage": "enrolled"}]}]})


async def _with_seats(p: dict) -> dict:
    cap = p.get("capacity") or 0
    if cap:
        p["seats_left"] = max(0, cap - await _seats_taken(p))
        p["full"] = p["seats_left"] == 0
    return p


async def _seed_programs():
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0, "programs_seeded": 1}) or {}
    if doc.get("programs_seeded"):
        return
    await db.settings.update_one({"key": "site"}, {"$set": {"programs_seeded": True}}, upsert=True)
    if await db.programs.count_documents({}):
        return
    seed = [
        ("Business Elevation Lab", "Professional", "https://images.pexels.com/photos/8555600/pexels-photo-8555600.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
         "A 12-week accelerator pairing members with mentors, capital readiness coaching, and peer accountability circles."),
        ("Sisterhood Housing Support", "Housing", "https://images.unsplash.com/photo-1628717341663-0007b0ee2597?crop=entropy&cs=srgb&fm=jpg&q=85&w=940",
         "Emergency housing navigation, rental assistance, and relocation resources for sisters in transition."),
        ("Community Care Drives", "Philanthropy", "https://images.unsplash.com/photo-1593113616828-6f22bca04804?crop=entropy&cs=srgb&fm=jpg&q=85&w=940",
         "Quarterly food, wellness, and back-to-school drives serving families across our chapters."),
        ("Leadership & Mentorship", "Professional", "https://images.unsplash.com/photo-1590650046871-92c887180603?crop=entropy&cs=srgb&fm=jpg&q=85&w=940",
         "Structured mentorship circles connecting emerging leaders with seasoned executives and entrepreneurs."),
        ("Wellness Workshops", "Community", "https://images.unsplash.com/photo-1652148439208-3e73641d0725?crop=entropy&cs=srgb&fm=jpg&q=85&w=940",
         "Mental health, financial literacy, and self-care workshops led by member experts."),
        ("The Sisterhood Fund", "Philanthropy", "https://images.pexels.com/photos/6647027/pexels-photo-6647027.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
         "Micro-grants distributed to member-led businesses and community relief projects."),
    ]
    docs = [{"id": str(uuid.uuid4()), "slug": _slugify(t), "title": t, "category": c, "image_url": img, "summary": s, "body": "",
             "goals": [], "impact": [], "cta_text": "Get Involved", "cta_link": "/volunteer", "published": True,
             "order": i, "created_at": _now_iso()} for i, (t, c, img, s) in enumerate(seed)]
    await db.programs.insert_many(docs)


async def _program_categories() -> list:
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0, "program_categories": 1}) or {}
    return doc.get("program_categories") or DEFAULT_PROGRAM_CATEGORIES


@api_router.get("/programs")
async def public_programs():
    await _seed_programs()
    items = await db.programs.find({"published": True}, {"_id": 0, "body": 0}).sort("order", 1).to_list(200)
    return {"items": [await _with_seats(p) for p in items], "categories": await _program_categories()}


@api_router.get("/programs/{slug}")
async def public_program(slug: str):
    p = await db.programs.find_one({"slug": slug[:100], "published": True}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    ids = p.get("home_testimonial_ids") or []
    if ids:
        home = {t["id"]: t for t in (await _get_home_content())["testimonials"]}
        p["testimonials"] = (p.get("testimonials") or []) + [home[i] for i in ids if i in home]
    return await _with_seats(p)


@api_router.get("/admin/programs")
async def admin_programs(user=Depends(require_admin)):
    await _seed_programs()
    items = await db.programs.find({}, {"_id": 0}).sort("order", 1).to_list(200)
    return {"items": [await _with_seats(p) for p in items], "categories": await _program_categories()}


@api_router.post("/admin/programs")
async def admin_create_program(payload: ProgramIn, user=Depends(require_admin)):
    data = _clean_program(payload)
    last = await db.programs.find_one({}, {"_id": 0, "order": 1}, sort=[("order", -1)])
    doc = {"id": str(uuid.uuid4()), "slug": await _unique_slug(data["title"]), **data,
           "order": (last or {}).get("order", -1) + 1, "created_at": _now_iso()}
    await db.programs.insert_one(dict(doc))
    return doc


@api_router.put("/admin/programs/{pid}")
async def admin_update_program(pid: str, payload: ProgramIn, background: BackgroundTasks, user=Depends(require_admin)):
    cur = await db.programs.find_one({"id": pid}, {"_id": 0})
    if not cur:
        raise HTTPException(status_code=404, detail="Program not found")
    data = _clean_program(payload)
    if data["title"] != cur["title"]:
        data["slug"] = await _unique_slug(data["title"], exclude_id=pid)
    await db.programs.update_one({"id": pid}, {"$set": {**data, "updated_at": _now_iso()}})
    background.add_task(_fill_seats, pid)
    return await db.programs.find_one({"id": pid}, {"_id": 0})


@api_router.delete("/admin/programs/{pid}")
async def admin_delete_program(pid: str, user=Depends(require_admin)):
    if not (await db.programs.delete_one({"id": pid})).deleted_count:
        raise HTTPException(status_code=404, detail="Program not found")
    return {"deleted": True}


@api_router.post("/admin/programs/reorder")
async def admin_reorder_programs(payload: ReorderIn, user=Depends(require_admin)):
    for i, pid in enumerate(payload.ids[:200]):
        await db.programs.update_one({"id": pid}, {"$set": {"order": i}})
    return {"ok": True}


@api_router.put("/admin/program-categories")
async def admin_program_categories(payload: CategoriesIn, user=Depends(require_admin)):
    cats = []
    for c in payload.categories:
        c = c.strip()[:40]
        if c and c.lower() != "all" and c.lower() not in [x.lower() for x in cats]:
            cats.append(c)
    if not cats or len(cats) > 12:
        raise HTTPException(status_code=400, detail="Add between 1 and 12 categories.")
    await db.settings.update_one({"key": "site"}, {"$set": {"program_categories": cats}}, upsert=True)
    return {"categories": cats}


# ---------- Home page content (editable) ----------
HOME_ICONS = ("Briefcase", "HeartHandshake", "Home", "Users", "GraduationCap", "Sparkles", "HandHeart", "Globe", "Heart", "Star", "Crown", "Sprout")
DEFAULT_HOME = {
    "mission_heading": "Our Mission",
    "mission_title": "Bridging the distance for women in the Diaspora",
    "mission_body": ("Caring Sisters Club, Inc. is dedicated to bridging the distance for women in the Diaspora. We provide a powerhouse platform "
                     "for professional business elevation, comprehensive housing assistance, and targeted philanthropic outreach. Through shared "
                     "strength, we transform collective vision into lasting community change."),
    "mission_quote": "Through shared strength, we transform collective vision into lasting community change.",
    "mission_image": "",
    "pillars": [
        {"icon": "Briefcase", "title": "Professional Empowerment", "text": "Connect with high-achieving women from the Diaspora to scale your business, share professional insights, and foster mutual growth in a supportive hub designed for excellence.", "cta": "Explore Opportunities", "to": "/initiatives"},
        {"icon": "HeartHandshake", "title": "Philanthropy", "text": "Join our collective mission to solve the evolving challenges women face and spearhead philanthropic endeavors that empower communities while building lifelong bonds of friendship.", "cta": "Join the Cause", "to": "/donate"},
        {"icon": "Home", "title": "Housing Assistance", "text": "We provide comprehensive housing navigation, emergency support, and resource connection so every sister has a stable foundation to build her future upon.", "cta": "Learn More", "to": "/initiatives"},
    ],
    "testimonials": [
        {"id": "t-adaeze", "quote": "The Caring Sisters Club gave me a mentor, a grant, and a sisterhood. My business tripled in a year.", "name": "Adaeze N.", "role": "Elevation Lab Graduate", "photo_url": "", "added_at": "2020-01-01T00:00:00+00:00"},
        {"id": "t-louise", "quote": "When I needed housing support, my sisters showed up. This community is family.", "name": "Louise M.", "role": "Member since 2022", "photo_url": "", "added_at": "2020-01-01T00:00:00+00:00"},
        {"id": "t-chantal", "quote": "I found my leadership voice here. Now I mentor five other women.", "name": "Chantal B.", "role": "Chapter Lead, Brooklyn", "photo_url": "", "added_at": "2020-01-01T00:00:00+00:00"},
    ],
    "updated_at": None,
}


class PillarItem(BaseModel):
    icon: str = "Sparkles"
    title: str
    text: str = ""
    cta: str = "Learn More"
    to: str = "/initiatives"


class HomeContentIn(BaseModel):
    mission_heading: str = ""
    mission_title: str = ""
    mission_body: str = ""
    mission_quote: str = ""
    mission_image: str = ""
    pillars: List[PillarItem] = []
    testimonials: List[TestimonialItem] = []


async def _get_home_content() -> dict:
    doc = await db.settings.find_one({"key": "home"}, {"_id": 0, "key": 0}) or {}
    return {k: doc.get(k, v) for k, v in DEFAULT_HOME.items()}


@api_router.get("/home-content")
async def public_home_content():
    return await _get_home_content()


@api_router.put("/admin/home-content")
async def admin_update_home_content(payload: HomeContentIn, user=Depends(require_admin)):
    if not payload.mission_title.strip() or not payload.mission_body.strip():
        raise HTTPException(status_code=400, detail="Mission title and paragraph are required.")
    if not _ok_img(payload.mission_image.strip()):
        raise HTTPException(status_code=400, detail="Mission image must be an uploaded image or https URL")
    if not 1 <= len(payload.pillars) <= 6:
        raise HTTPException(status_code=400, detail="Add between 1 and 6 mission cards.")
    pillars = []
    for c in payload.pillars:
        if not c.title.strip():
            raise HTTPException(status_code=400, detail="Each mission card needs a title.")
        to = c.to.strip() or "/"
        if not (re.match(r"^/[A-Za-z0-9/_\-?=&#.]*$", to) or to.startswith("https://")) or to.startswith("//"):
            raise HTTPException(status_code=400, detail="Card links must be a site path like /donate or an https:// URL")
        pillars.append({"icon": c.icon if c.icon in HOME_ICONS else "Sparkles", "title": c.title.strip()[:80],
                        "text": c.text.strip()[:500], "cta": c.cta.strip()[:40] or "Learn More", "to": to})
    doc = {
        "mission_heading": payload.mission_heading.strip()[:60] or "Our Mission",
        "mission_title": payload.mission_title.strip()[:150], "mission_body": payload.mission_body.strip()[:2000],
        "mission_quote": payload.mission_quote.strip()[:300], "mission_image": payload.mission_image.strip(),
        "pillars": pillars, "testimonials": _clean_testimonials(payload.testimonials, 12),
        "updated_at": _now_iso(), "updated_by": user.get("email"),
    }
    await db.settings.update_one({"key": "home"}, {"$set": doc}, upsert=True)
    return await _get_home_content()


# ---------- Win-back tracking ----------
@api_router.get("/admin/winbacks")
async def admin_winbacks(user=Depends(require_admin)):
    cancels = await db.cancellations.find({}, {"_id": 0, "token": 0}).sort("created_at", -1).to_list(1000)
    rows, returned, recovered = [], 0, 0.0
    for c in cancels:
        row = {k: c.get(k) for k in ("name", "email", "amount", "ends_on", "reason", "thanked", "thanked_at", "created_at")}
        row.update({"returned": False, "returned_at": None, "recovered": 0.0})
        if c.get("thanked") and c.get("thanked_at"):
            gifts = await db.payment_transactions.find({
                "donor_email": {"$regex": f"^{re.escape(c['email'])}$", "$options": "i"}, "payment_status": "paid",
                "created_at": {"$gt": c["thanked_at"]}, "stripe_subscription_id": {"$ne": c.get("sub_id")},
            }, {"_id": 0, "amount": 1, "created_at": 1, "updated_at": 1}).to_list(500)
            if gifts:
                row["returned"] = True
                row["returned_at"] = min(g.get("updated_at") or g.get("created_at") for g in gifts)
                row["recovered"] = round(sum(float(g.get("amount") or 0) for g in gifts), 2)
                returned += 1
                recovered += row["recovered"]
        rows.append(row)
    notes = sum(1 for c in cancels if c.get("thanked"))
    return {"cancellations": len(cancels), "notes_sent": notes, "returned": returned,
            "rate": round(returned / notes * 100, 1) if notes else 0, "recovered": round(recovered, 2), "items": rows}


# ---------- About page content (editable) ----------
VALUE_ICONS = ("Heart", "Shield", "Sparkles", "Users", "HandHeart", "Star", "Crown", "Globe", "Sprout", "GraduationCap", "Briefcase", "HeartHandshake")
DEFAULT_ABOUT = {
    "hero_subtitle": "What began as ten women around a kitchen table is now a global network transforming individual ambition into shared empowerment.",
    "mission_title": "Why we exist",
    "mission_body": DEFAULT_HOME["mission_body"],
    "mission_image": "",
    "values": [
        {"icon": "Heart", "title": "Love", "text": "We lead with empathy, meeting every sister where she is with genuine care."},
        {"icon": "Shield", "title": "Respect", "text": "Mutual respect is the foundation of trust that holds our sisterhood together."},
        {"icon": "Sparkles", "title": "Empowerment", "text": "We equip women with tools, mentorship, and capital to rise and lead."},
        {"icon": "Users", "title": "Community", "text": "We invest in the collective, knowing our impact multiplies when we grow together."},
    ],
    "story_title": "A journey of shared strength",
    "story": [
        {"year": "2019", "title": "A Circle of Ten", "text": "Ten women of the Diaspora gathered around a kitchen table with a shared belief: no sister should build alone.", "image": ""},
        {"year": "2021", "title": "Formal 501(c)(3) Status", "text": "The club incorporated as a nonprofit, launching its first mentorship and housing-support cohort.", "image": ""},
        {"year": "2023", "title": "Regional Expansion", "text": "Chapters opened across 14 cities, delivering workshops, grants, and community drives.", "image": ""},
        {"year": "2025", "title": "The Sisterhood Fund", "text": "We launched a member grant fund distributing over $600K toward member-led businesses and relief.", "image": ""},
    ],
    "updated_at": None,
}


class ValueItem(BaseModel):
    icon: str = "Heart"
    title: str
    text: str = ""


class StoryItem(BaseModel):
    year: str = ""
    title: str
    text: str = ""
    image: str = ""


class AboutIn(BaseModel):
    hero_subtitle: str = ""
    mission_title: str = ""
    mission_body: str = ""
    mission_image: str = ""
    values: List[ValueItem] = []
    story_title: str = ""
    story: List[StoryItem] = []


async def _get_about() -> dict:
    doc = await db.settings.find_one({"key": "about"}, {"_id": 0, "key": 0}) or {}
    return {k: doc.get(k, v) for k, v in DEFAULT_ABOUT.items()}


@api_router.get("/about-content")
async def public_about():
    return await _get_about()


@api_router.put("/admin/about-content")
async def admin_update_about(payload: AboutIn, user=Depends(require_admin)):
    bad = lambda m: HTTPException(status_code=400, detail=m)  # noqa: E731
    if not payload.mission_body.strip():
        raise bad("Mission paragraph is required.")
    if not 1 <= len(payload.values) <= 8 or any(not v.title.strip() for v in payload.values):
        raise bad("Add 1–8 values, each with a title.")
    if len(payload.story) > 12 or any(not st.title.strip() for st in payload.story):
        raise bad("Each story milestone needs a title (max 12).")
    if not all(_ok_img(u.strip()) for u in [payload.mission_image] + [st.image for st in payload.story]):
        raise bad("Photos must be uploaded images or https URLs")
    doc = {
        "hero_subtitle": payload.hero_subtitle.strip()[:300] or DEFAULT_ABOUT["hero_subtitle"],
        "mission_title": payload.mission_title.strip()[:120] or "Why we exist",
        "mission_body": payload.mission_body.strip()[:3000], "mission_image": payload.mission_image.strip(),
        "values": [{"icon": v.icon if v.icon in VALUE_ICONS else "Heart", "title": v.title.strip()[:60], "text": v.text.strip()[:400]} for v in payload.values],
        "story_title": payload.story_title.strip()[:120] or DEFAULT_ABOUT["story_title"],
        "story": [{"year": st.year.strip()[:12], "title": st.title.strip()[:100], "text": st.text.strip()[:800], "image": st.image.strip()} for st in payload.story],
        "updated_at": _now_iso(), "updated_by": user.get("email"),
    }
    await db.settings.update_one({"key": "about"}, {"$set": doc}, upsert=True)
    return await _get_about()


# ---------- Member story submissions ----------
class StorySubmitIn(BaseModel):
    name: str
    email: str
    role: str = ""
    quote: str
    photo_url: str = ""
    program_slug: str = ""


class StoryApproveIn(BaseModel):
    target: str  # "home" or a program id
    quote: Optional[str] = None


@api_router.post("/stories")
async def submit_story(payload: StorySubmitIn, request: Request, background: BackgroundTasks):
    _rate_limit(request, "story", max_hits=3, window_s=600)
    name, email = _validate_person({"name": payload.name, "email": payload.email})
    quote = payload.quote.strip()
    if len(quote) < 20:
        raise HTTPException(status_code=400, detail="Please share a little more of your story (at least 20 characters).")
    photo = payload.photo_url.strip()
    if photo and not re.match(r"^/api/media/file/[A-Za-z0-9-]+$", photo):
        raise HTTPException(status_code=400, detail="Invalid photo.")
    program = await db.programs.find_one({"slug": payload.program_slug[:100], "published": True}, {"_id": 0, "id": 1, "title": 1}) if payload.program_slug else None
    doc = {"id": str(uuid.uuid4()), "name": name[:80], "email": email.lower(), "role": payload.role.strip()[:80], "quote": quote[:1000],
           "photo_url": photo, "program_id": (program or {}).get("id"), "program_title": (program or {}).get("title"),
           "status": "pending", "created_at": _now_iso()}
    await db.story_submissions.insert_one(dict(doc))
    background.add_task(_notify_staff, "story", {"name": doc["name"], "email": doc["email"], "role": doc["role"],
                                                 "program": doc["program_title"] or "General", "story": doc["quote"]})
    return {"id": doc["id"], "message": "Thank you for sharing your story! Our team will review it shortly."}


@api_router.get("/admin/stories")
async def admin_list_stories(user=Depends(require_admin)):
    items = await db.story_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items}


@api_router.post("/admin/stories/{sid}/approve")
async def admin_approve_story(sid: str, payload: StoryApproveIn, user=Depends(require_admin)):
    st = await db.story_submissions.find_one({"id": sid, "status": "pending"}, {"_id": 0})
    if not st:
        raise HTTPException(status_code=404, detail="Pending story not found")
    t = {"id": str(uuid.uuid4()), "quote": (payload.quote or st["quote"]).strip()[:600], "name": st["name"], "role": st["role"],
         "photo_url": st["photo_url"], "added_at": _now_iso()}
    if payload.target == "home":
        home = await _get_home_content()
        if len(home["testimonials"]) >= 12:
            raise HTTPException(status_code=400, detail="The Home page already has 12 testimonials. Remove one first.")
        await db.settings.update_one({"key": "home"}, {"$set": {**{k: v for k, v in home.items() if k != "testimonials"},
                                                               "testimonials": home["testimonials"] + [t], "updated_at": _now_iso()}}, upsert=True)
        label = "Home page"
    else:
        prog = await db.programs.find_one({"id": payload.target}, {"_id": 0, "testimonials": 1, "title": 1})
        if not prog:
            raise HTTPException(status_code=404, detail="Program not found")
        if len(prog.get("testimonials") or []) >= 6:
            raise HTTPException(status_code=400, detail="That program already has 6 testimonials. Remove one first.")
        await db.programs.update_one({"id": payload.target}, {"$push": {"testimonials": t}})
        label = prog["title"]
    await db.story_submissions.update_one({"id": sid}, {"$set": {"status": "approved", "featured_on": label, "reviewed_at": _now_iso(), "reviewed_by": user.get("email")}})
    return {"approved": True, "featured_on": label}


@api_router.post("/admin/stories/{sid}/reject")
async def admin_reject_story(sid: str, user=Depends(require_admin)):
    res = await db.story_submissions.update_one({"id": sid, "status": "pending"}, {"$set": {"status": "rejected", "reviewed_at": _now_iso()}})
    if not res.modified_count:
        raise HTTPException(status_code=404, detail="Pending story not found")
    return {"rejected": True}


# ---------- Program sign-ups ----------
class ProgramSignupIn(BaseModel):
    name: str
    email: str
    phone: str = ""
    message: str = ""


def _signup_confirm_html(name: str, prog: dict, waitlist: bool = False) -> str:
    lead = (f'Thank you for your interest in <strong>{_esc(prog["title"])}</strong>. The program is currently full, so you have been added to the <strong>waitlist</strong>. '
            'We will reach out as soon as a spot opens up.</p>') if waitlist else (
            f'Thank you for your interest in <strong>{_esc(prog["title"])}</strong>. '
            'A member of our team will reach out within 3 business days with next steps.</p>')
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Program Sign-Up") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 14px">Welcome, {_esc(name)}!</h1>'
        '<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">' + lead
        + _btn(f'{PUBLIC_APP_URL}/initiatives/{prog["slug"]}', "View the Program", primary=True) +
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">With warmth,<br/>The Caring Sisters Club</p></td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you signed up on our website. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _send_signup_confirm(email: str, name: str, prog: dict, waitlist: bool = False):
    try:
        subj = f"You're on the waitlist: {prog['title']}" if waitlist else f"You're signed up: {prog['title']}"
        await send_email(to=email, subject=subj[:150], html=_signup_confirm_html(name, prog, waitlist))
    except Exception as e:
        logging.error(f"Signup confirmation failed: {e}")


@api_router.post("/programs/{slug}/signup")
async def program_signup(slug: str, payload: ProgramSignupIn, request: Request, background: BackgroundTasks):
    _rate_limit(request, "submission", max_hits=5, window_s=60)
    name, email = _validate_person({"name": payload.name, "email": payload.email, "message": payload.message})
    prog = await db.programs.find_one({"slug": slug[:100], "published": True}, {"_id": 0, "id": 1, "title": 1, "slug": 1, "capacity": 1})
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    full = bool((await _with_seats(dict(prog))).get("full"))
    phone = re.sub(r"[^0-9+()\- .]", "", payload.phone)[:30]
    data = {"program": prog["title"], "program_slug": prog["slug"], "name": name, "email": email.lower(), "phone": phone, "message": payload.message.strip()[:3000]}
    if full:
        data["list"] = "Waitlist"
    await db.submissions.insert_one({"id": str(uuid.uuid4()), "type": "program_signup", "program_id": prog["id"], "waitlist": full,
                                     "data": data, "read": False, "created_at": _now_iso()})
    background.add_task(_notify_staff, "program_signup", data)
    background.add_task(_send_signup_confirm, email.lower(), name, prog, full)
    if full:
        return {"waitlist": True, "message": "This program is full, so you've been added to the waitlist. Check your email for details."}
    return {"waitlist": False, "message": "You're signed up! Check your email for a confirmation."}


# ---------- Waitlist spot alerts ----------
WAITLIST_MODES = ("claim", "auto", "broadcast")
OFFER_HOURS = 48


async def _signup_program_id(sub: dict):
    if sub.get("program_id"):
        return sub["program_id"]
    p = await db.programs.find_one({"slug": (sub.get("data") or {}).get("program_slug")}, {"_id": 0, "id": 1})
    return (p or {}).get("id")


def _spot_email_html(name: str, prog: dict, mode: str, link: str = "") -> str:
    if mode == "auto":
        head, body, btn = "You're in!", f'Great news: a spot opened in <strong>{_esc(prog["title"])}</strong> and you have been moved from the waitlist into the program. Our team will reach out with next steps.', _btn(f'{PUBLIC_APP_URL}/initiatives/{prog["slug"]}', "View the Program", primary=True)
    else:
        race = " Spots go to whoever claims first, so act quickly." if mode == "broadcast" else ""
        head, body, btn = "A spot just opened!", f'A seat is now available in <strong>{_esc(prog["title"])}</strong>. Claim it within {OFFER_HOURS} hours to secure your place.{race}', _btn(link, "Claim My Spot", primary=True)
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Waitlist Update") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 14px">{head}</h1>'
        f'<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">Hi {_esc(name)}, {body}</p>' + btn +
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">With warmth,<br/>The Caring Sisters Club</p></td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you joined a program waitlist on our website. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _spot_email(sub: dict, prog: dict, mode: str, link: str = ""):
    d = sub.get("data") or {}
    subj = f"You're in: {prog['title']}" if mode == "auto" else f"A spot opened in {prog['title']}"
    try:
        await send_email(to=d.get("email"), subject=subj[:150], html=_spot_email_html((d.get("name") or "there").split()[0], prog, mode, link))
    except Exception as e:
        logging.error(f"Waitlist spot email failed: {e}")


async def _fill_seats(pid: str) -> int:
    """Offer or assign freed seats to waitlisted sign-ups per the program's waitlist mode."""
    p = await db.programs.find_one({"id": pid}, {"_id": 0})
    if not p or not p.get("capacity") or not p.get("published"):
        return 0
    now = datetime.now(timezone.utc)
    wq = {"type": "program_signup", "program_id": pid, "waitlist": True, "stage": {"$nin": ["enrolled", "not_fit"]}}
    await db.submissions.update_many({**wq, "offer_status": "open", "offer_expires": {"$lte": now.isoformat()}}, {"$set": {"offer_status": "expired"}})
    free = p["capacity"] - await _seats_taken(p)
    if free <= 0:
        return 0
    mode = p.get("waitlist_mode") or "claim"
    if mode == "auto":
        subs = await db.submissions.find({**wq, "offer_status": {"$ne": "open"}}, {"_id": 0}).sort("created_at", 1).to_list(free)
        for s in subs:
            await db.submissions.update_one({"id": s["id"]}, {"$set": {"waitlist": False, "data.list": "Moved in from waitlist", "moved_at": now.isoformat()}})
            await _spot_email(s, p, "auto")
        return len(subs)
    if mode == "claim":
        free -= await db.submissions.count_documents({**wq, "offer_status": "open"})
        if free <= 0:
            return 0
        subs = await db.submissions.find({**wq, "offer_status": {"$exists": False}}, {"_id": 0}).sort("created_at", 1).to_list(free)
    else:
        subs = await db.submissions.find({**wq, "offer_status": {"$exists": False}}, {"_id": 0}).sort("created_at", 1).to_list(500)
    for s in subs:
        tok = secrets.token_urlsafe(24)
        await db.submissions.update_one({"id": s["id"]}, {"$set": {"offer_status": "open", "offer_token": tok, "offer_mode": mode,
                                                                    "offer_sent_at": now.isoformat(), "offer_expires": (now + timedelta(hours=OFFER_HOURS)).isoformat()}})
        await _spot_email(s, p, mode, f"{PUBLIC_APP_URL}/waitlist/claim?token={tok}")
    return len(subs)


class ClaimIn(BaseModel):
    token: str


async def _offer(token: str, request: Request):
    _rate_limit(request, "claim", max_hits=20, window_s=60)
    sub = await db.submissions.find_one({"offer_token": token[:64], "type": "program_signup"}, {"_id": 0}) if token else None
    if not sub:
        raise HTTPException(status_code=404, detail="This link is invalid.")
    prog = await db.programs.find_one({"id": sub.get("program_id")}, {"_id": 0})
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    status = sub.get("offer_status")
    if status == "open" and sub.get("offer_expires", "") <= _now_iso():
        status = "expired"
    if status == "open" and prog.get("capacity") and prog["capacity"] - await _seats_taken(prog) <= 0:
        status = "full"
    return sub, prog, status


@api_router.get("/waitlist/offer")
async def waitlist_offer(token: str, request: Request):
    sub, prog, status = await _offer(token, request)
    return {"status": status, "program": prog["title"], "slug": prog["slug"], "name": (sub["data"].get("name") or "").split(" ")[0], "expires": sub.get("offer_expires")}


@api_router.post("/waitlist/claim")
async def waitlist_claim(payload: ClaimIn, request: Request, background: BackgroundTasks):
    sub, prog, status = await _offer(payload.token, request)
    if status == "claimed":
        return {"status": "claimed", "program": prog["title"]}
    if status == "expired":
        raise HTTPException(status_code=410, detail="This offer has expired. You're still on the waitlist, and we'll let you know if another spot opens.")
    if status == "full":
        raise HTTPException(status_code=409, detail="Sorry, this spot was just claimed by someone else. You're still on the waitlist.")
    res = await db.submissions.update_one({"id": sub["id"], "offer_status": "open"}, {"$set": {"offer_status": "claimed", "waitlist": False, "claimed_at": _now_iso(), "data.list": "Claimed from waitlist"}})
    if not res.modified_count:
        raise HTTPException(status_code=409, detail="This offer is no longer available.")
    background.add_task(_spot_email, sub, prog, "auto")
    return {"status": "claimed", "program": prog["title"]}


# ---------- Monthly impact email ----------
def _abs_img(url: str) -> str:
    return f"{PUBLIC_APP_URL}{url}" if url.startswith("/api/") else url


async def _impact_content(since: str) -> dict:
    photos, stories = [], []
    async for p in db.programs.find({"published": True}, {"_id": 0}):
        for g in p.get("gallery") or []:
            if (g.get("added_at") or "") > since:
                photos.append({"url": _abs_img(g["url"]), "caption": g.get("caption") or p["title"], "program": p["title"], "slug": p["slug"]})
        for t in p.get("testimonials") or []:
            if (t.get("added_at") or "") > since:
                stories.append({**t, "program": p["title"]})
    for t in (await _get_home_content())["testimonials"]:
        if (t.get("added_at") or "") > since:
            stories.append({**t, "program": ""})
    return {"photos": photos[:6], "stories": stories[:3]}


def _impact_email_html(name: str, content: dict, month: str, track: tuple = None) -> str:
    def link(path: str) -> str:
        if not track:
            return f"{PUBLIC_APP_URL}{path}"
        return f"{PUBLIC_APP_URL}/api/t/impact/{track[0]}/click?r={track[1]}&u={_urlquote(path, safe='/')}"
    pixel = (f'<img src="{PUBLIC_APP_URL}/api/t/impact/{track[0]}/open.gif?r={track[1]}" width="1" height="1" alt="" style="display:block;width:1px;height:1px;border:0"/>'
             if track else "")
    cells = "".join(
        f'<td width="50%" style="padding:6px;vertical-align:top"><img src="{_esc(ph["url"])}" alt="" width="260" style="width:100%;max-width:260px;height:170px;object-fit:cover;border-radius:10px;display:block"/>'
        f'<p style="font-size:12px;color:#6b5560;margin:6px 0 0">{_esc(ph["caption"])}</p></td>' + ("</tr><tr>" if i % 2 == 1 else "")
        for i, ph in enumerate(content["photos"]))
    photos = f'<table role="presentation" width="100%" style="margin:0 0 18px"><tr>{cells}</tr></table>' if cells else ""
    stories = "".join(
        f'<div style="background:#faf2f7;border-radius:12px;padding:16px 18px;margin:0 0 12px"><p style="font-family:Georgia,serif;font-style:italic;font-size:15px;line-height:1.6;color:#3B0A2E;margin:0 0 8px">&ldquo;{_esc(st["quote"])}&rdquo;</p>'
        f'<p style="font-size:12.5px;color:#B4247E;font-weight:bold;margin:0">{_esc(st["name"])}{(" · " + _esc(st["role"])) if st.get("role") else ""}{(" · " + _esc(st["program"])) if st.get("program") else ""}</p></div>'
        for st in content["stories"])
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header(f"Your Impact · {month}") +
        '<tr><td style="padding:30px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 12px">Dear {_esc(name)}, look what you made possible</h1>'
        '<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">Your monthly gift keeps our programs running. Here is a glimpse of the sisterhood you supported this month.</p>'
        + photos + stories +
        _btn(link("/initiatives"), "See Our Programs", primary=True) + pixel +
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">With gratitude,<br/>The Caring Sisters Club</p></td></tr>'
        f'<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You receive this monthly update as a monthly donor. Manage your gift anytime at <a href="{link("/manage-gift")}" style="color:#CBA24B">our Manage My Gift page</a>. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _monthly_recipients() -> list:
    cancelled = set(await db.cancellations.distinct("sub_id"))
    seen, out = set(), []
    async for t in db.payment_transactions.find({"frequency": "monthly", "payment_status": "paid", "stripe_subscription_id": {"$nin": [None, ""]}},
                                                 {"_id": 0, "donor_email": 1, "donor_name": 1, "stripe_subscription_id": 1}).sort("created_at", -1):
        em = (t.get("donor_email") or "").lower()
        if em and em not in seen and t["stripe_subscription_id"] not in cancelled:
            seen.add(em)
            out.append({"email": em, "name": (t.get("donor_name") or "").strip() or "Friend"})
    return out


def _impact_window():
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=31)).isoformat(), now.strftime("%B %Y")


@api_router.get("/admin/impact-email/preview")
async def impact_preview(user=Depends(require_admin)):
    since, month = _impact_window()
    content = await _impact_content(since)
    last = await db.impact_emails.find_one({}, {"_id": 0}, sort=[("sent_at", -1)])
    return {"html": _impact_email_html("Friend", content, month), "recipients": len(await _monthly_recipients()),
            "photos": len(content["photos"]), "stories": len(content["stories"]), "last_sent": last}


async def _send_impact_email(trigger: str, test_to: str = None) -> dict:
    since, month = _impact_window()
    content = await _impact_content(since)
    if not content["photos"] and not content["stories"]:
        return {"sent": 0, "skipped": "No new program photos or stories in the past month."}
    recipients = [{"email": test_to, "name": "Friend"}] if test_to else await _monthly_recipients()
    cid, sent = str(uuid.uuid4()), 0
    for r in recipients:
        track = None
        if not test_to:
            track = (cid, secrets.token_urlsafe(12))
            await db.impact_recipients.insert_one({"cid": cid, "rid": track[1], "email": r["email"], "opened_at": None,
                                                   "clicked_at": None, "opens": 0, "clicks": 0})
        try:
            if await send_email(to=r["email"], subject=f"Your impact this month · {month}"[:150], html=_impact_email_html(r["name"], content, month, track)) is not None:
                sent += 1
        except Exception as e:
            logging.error(f"Impact email failed: {e}")
    if not test_to:
        await db.impact_emails.insert_one({"id": cid, "month": datetime.now(timezone.utc).strftime("%Y-%m"), "trigger": trigger, "sent": sent,
                                           "recipients": len(recipients), "photos": len(content["photos"]), "stories": len(content["stories"]), "sent_at": _now_iso()})
    return {"sent": sent, "recipients": len(recipients)}


@api_router.post("/admin/impact-email/send")
async def impact_send(user=Depends(require_admin)):
    return await _send_impact_email("manual")


@api_router.post("/admin/impact-email/test")
async def impact_test(user=Depends(require_admin)):
    return await _send_impact_email("test", test_to=user.get("email"))


async def _maybe_monthly_impact():
    now = datetime.now(timezone.utc)
    if now.day > 3 or await db.impact_emails.find_one({"month": now.strftime("%Y-%m"), "trigger": "auto"}):
        return
    await _send_impact_email("auto")


# ---------- Story request emails (60 days after program sign-up) ----------
def _story_request_html(name: str, program: str, url: str) -> str:
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Share Your Story") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 14px">How has it been, {_esc(name)}?</h1>'
        f'<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">It has been about two months since you joined <strong>{_esc(program)}</strong>. '
        'We would love to hear how it has made a difference for you. Your story could inspire another sister to take her first step.</p>'
        + _btn(url, "Share My Story", primary=True) +
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">It only takes a minute, and our team reviews every story before it is shared.<br/><br/>With warmth,<br/>The Caring Sisters Club</p></td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you signed up for a program on our website. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _send_story_requests() -> int:
    if not (await _get_settings()).get("story_requests_enabled", True):
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    sent = 0
    async for sub in db.submissions.find({"type": "program_signup", "created_at": {"$lte": cutoff}, "story_request_sent": {"$ne": True}}, {"_id": 0}):
        d = sub.get("data") or {}
        await db.submissions.update_one({"id": sub["id"]}, {"$set": {"story_request_sent": True, "story_request_at": _now_iso()}})
        prog = await db.programs.find_one({"$or": [{"slug": d.get("program_slug") or "-"}, {"title": d.get("program")}], "published": True}, {"_id": 0, "slug": 1, "title": 1})
        if not prog or not d.get("email"):
            continue
        try:
            if await send_email(to=d["email"], subject=f"How has {prog['title']} been for you?"[:150],
                                html=_story_request_html(d.get("name") or "Friend", prog["title"], f"{PUBLIC_APP_URL}/initiatives/{prog['slug']}?share=1")) is not None:
                sent += 1
        except Exception as e:
            logging.error(f"Story request email failed: {e}")
    return sent


# ---------- Program interest report ----------
def _last_months(n: int) -> list:
    now = datetime.now(timezone.utc)
    y, m, out = now.year, now.month, []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return list(reversed(out))


@api_router.get("/admin/reports/program-signups")
async def report_program_signups(months: int = 6, user=Depends(require_admin)):
    months = max(1, min(int(months), 24))
    keys = _last_months(months)
    counts = {}
    async for row in db.submissions.aggregate([
        {"$match": {"type": "program_signup", "created_at": {"$gte": keys[0]}}},
        {"$group": {"_id": {"p": "$data.program", "m": {"$substr": ["$created_at", 0, 7]}}, "n": {"$sum": 1}}},
    ]):
        counts.setdefault(row["_id"]["p"] or "Unknown", {})[row["_id"]["m"]] = row["n"]
    stages = {}
    async for row in db.submissions.aggregate([
        {"$match": {"type": "program_signup", "created_at": {"$gte": keys[0]}}},
        {"$group": {"_id": {"p": "$data.program", "s": {"$ifNull": ["$stage", "new"]}}, "n": {"$sum": 1}}},
    ]):
        stages.setdefault(row["_id"]["p"] or "Unknown", {})[row["_id"]["s"]] = row["n"]
    titles = [p["title"] async for p in db.programs.find({}, {"_id": 0, "title": 1}).sort("order", 1)]
    rows = []
    for t in titles + [t for t in counts if t not in titles]:
        c = [counts.get(t, {}).get(k, 0) for k in keys]
        trend = "up" if len(c) > 1 and c[-1] > c[-2] else "down" if len(c) > 1 and c[-1] < c[-2] else "flat"
        st = stages.get(t, {})
        total = sum(c)
        reached = st.get("contacted", 0) + st.get("enrolled", 0) + st.get("not_fit", 0)
        rows.append({"program": t, "counts": c, "total": total, "trend": trend, "stages": st,
                     "contacted_pct": round(reached / total * 100) if total else 0,
                     "enrolled_pct": round(st.get("enrolled", 0) / total * 100) if total else 0})
    return {"months": keys, "rows": rows, "totals": [sum(r["counts"][i] for r in rows) for i in range(len(keys))]}


# ---------- Impact email tracking ----------
_PIXEL = bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")


@api_router.get("/t/impact/{cid}/open.gif")
async def impact_open(cid: str, r: str = ""):
    await db.impact_recipients.update_one({"cid": cid[:64], "rid": r[:64], "opened_at": None}, {"$set": {"opened_at": _now_iso()}})
    await db.impact_recipients.update_one({"cid": cid[:64], "rid": r[:64]}, {"$inc": {"opens": 1}})
    return Response(content=_PIXEL, media_type="image/gif", headers={"Cache-Control": "no-store, max-age=0"})


@api_router.get("/t/impact/{cid}/click")
async def impact_click(cid: str, r: str = "", u: str = "/"):
    path = u if re.match(r"^/[A-Za-z0-9/_\-?=&.]*$", u or "") and not u.startswith("//") else "/"
    rec = await db.impact_recipients.find_one({"cid": cid[:64], "rid": r[:64]}, {"_id": 0, "opened_at": 1})
    if rec:
        now = _now_iso()
        await db.impact_recipients.update_one({"cid": cid[:64], "rid": r[:64], "clicked_at": None}, {"$set": {"clicked_at": now}})
        if not rec.get("opened_at"):
            await db.impact_recipients.update_one({"cid": cid[:64], "rid": r[:64]}, {"$set": {"opened_at": now}})
        await db.impact_recipients.update_one({"cid": cid[:64], "rid": r[:64]}, {"$inc": {"clicks": 1}})
    return RedirectResponse(url=f"{PUBLIC_APP_URL}{path}", status_code=302)


@api_router.get("/admin/impact-email/history")
async def impact_history(user=Depends(require_admin)):
    sends = await db.impact_emails.find({"id": {"$exists": True}}, {"_id": 0}).sort("sent_at", -1).to_list(12)
    for s in sends:
        q = {"cid": s["id"]}
        s["opens"] = await db.impact_recipients.count_documents({**q, "opened_at": {"$ne": None}})
        s["clicks"] = await db.impact_recipients.count_documents({**q, "clicked_at": {"$ne": None}})
        s["open_rate"] = round(s["opens"] / s["sent"] * 100, 1) if s.get("sent") else 0
        s["click_rate"] = round(s["clicks"] / s["sent"] * 100, 1) if s.get("sent") else 0
    return {"items": sends}


# ---------- Volunteer hours ----------
class HoursIn(BaseModel):
    name: str
    email: str
    program_id: str
    date: str
    hours: float
    note: str = ""
    leaderboard: bool = False


@api_router.post("/volunteer-hours")
async def log_hours(payload: HoursIn, request: Request, background: BackgroundTasks):
    _rate_limit(request, "hours", max_hits=10, window_s=600)
    name, email = _validate_person({"name": payload.name, "email": payload.email, "note": payload.note})
    if not 0.25 <= payload.hours <= 24:
        raise HTTPException(status_code=400, detail="Hours must be between 0.25 and 24 for a single day.")
    try:
        day = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Please choose a valid date.")
    today = datetime.now(timezone.utc).date()
    if day > today or day < today - timedelta(days=365):
        raise HTTPException(status_code=400, detail="Date must be within the past year and not in the future.")
    prog = await db.programs.find_one({"id": payload.program_id[:64], "published": True}, {"_id": 0, "id": 1, "title": 1})
    if not prog:
        raise HTTPException(status_code=400, detail="Please choose a program.")
    doc = {"id": str(uuid.uuid4()), "name": name[:80], "email": email.lower(), "program_id": prog["id"], "program": prog["title"],
           "date": payload.date, "hours": round(payload.hours, 2), "note": payload.note.strip()[:500], "status": "pending",
           "leaderboard": bool(payload.leaderboard), "created_at": _now_iso()}
    await db.volunteer_hours.insert_one(dict(doc))
    return {"id": doc["id"], "message": "Thank you! Your hours were submitted for review."}


@api_router.get("/volunteer-hours/summary")
async def hours_summary():
    by = [{"program": r["_id"], "hours": round(r["h"], 1)} async for r in db.volunteer_hours.aggregate([
        {"$match": {"status": "approved"}}, {"$group": {"_id": "$program", "h": {"$sum": "$hours"}}}, {"$sort": {"h": -1}}])]
    vols = len(await db.volunteer_hours.distinct("email", {"status": "approved"}))
    return {"total_hours": round(sum(b["hours"] for b in by), 1), "volunteers": vols, "by_program": by}


@api_router.get("/admin/volunteer-hours")
async def admin_hours(user=Depends(require_admin)):
    return {"items": await db.volunteer_hours.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)}


@api_router.post("/admin/volunteer-hours/{hid}/{action}")
async def admin_review_hours(hid: str, action: str, background: BackgroundTasks, user=Depends(require_admin)):
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Invalid action")
    res = await db.volunteer_hours.update_one({"id": hid, "status": "pending"}, {"$set": {
        "status": "approved" if action == "approve" else "rejected", "reviewed_at": _now_iso(), "reviewed_by": user.get("email")}})
    if not res.modified_count:
        raise HTTPException(status_code=404, detail="Pending entry not found")
    if action == "approve":
        background.add_task(_send_volunteer_thanks)
    return {"ok": True}


# ---------- Volunteer thank-yous, leaderboard ----------
def _short_name(name: str) -> str:
    parts = (name or "").split()
    return f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else (parts[0] if parts else "Sister")


async def _hours_total(email: str, since: str = "") -> float:
    q = {"email": email, "status": "approved"}
    if since:
        q["date"] = {"$gte": since}
    rows = await db.volunteer_hours.find(q, {"_id": 0, "hours": 1}).to_list(10000)
    return round(sum(h["hours"] for h in rows), 2)


def _badges_html(badges: list) -> str:
    if not badges:
        return ""
    cells = "".join(f'<td style="padding:8px;text-align:center"><div style="display:inline-block;width:74px;height:74px;border-radius:50%;background:#3B0A2E;border:3px solid #CBA24B;color:#CBA24B;font-family:Georgia,serif;font-size:22px;font-weight:bold;line-height:74px">{b["threshold"]}h</div>'
                    f'<p style="font-size:12px;color:#3B0A2E;font-weight:bold;margin:6px 0 0">{_esc(b["label"])}</p></td>' for b in badges)
    return f'<table role="presentation" width="100%" style="background:#fdf7e8;border-radius:12px;margin:0 0 18px"><tr><td colspan="9" style="padding:12px 16px 0;font-size:13px;color:#8a6a2c;font-weight:bold">New badge{"s" if len(badges) > 1 else ""} earned!</td></tr><tr>{cells}</tr></table>'


def _vol_thanks_html(name: str, entries: list, year_total: float, all_total: float, badges: list = None) -> str:
    rows = "".join(f'<tr><td style="padding:7px 16px;font-size:13px;color:#4a3340">{_esc(e["date"])} &middot; {_esc(e["program"])}</td>'
                   f'<td style="padding:7px 16px;font-size:14px;color:#3B0A2E;font-weight:bold;text-align:right">{e["hours"]:g}h</td></tr>' for e in entries)
    stat = lambda v, l: (f'<td width="50%" style="padding:14px;text-align:center"><p style="font-family:Georgia,serif;font-size:30px;color:#B4247E;font-weight:bold;margin:0">{v:g}</p>'  # noqa: E731
                         f'<p style="font-size:12px;color:#6b5560;margin:4px 0 0">{l}</p></td>')
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Thank You, Volunteer") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 14px">Thank you, {_esc(name)}!</h1>'
        '<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 16px">Your volunteer hours have been confirmed. Every hour you give strengthens our sisterhood.</p>'
        f'<table role="presentation" width="100%" style="background:#faf2f7;border-radius:12px;margin:0 0 16px">{rows}</table>'
        f'<table role="presentation" width="100%" style="border:1px solid #eadfe6;border-radius:12px;margin:0 0 20px"><tr>{stat(year_total, "hours this year")}{stat(all_total, "hours all-time")}</tr></table>'
        + _badges_html(badges or [])
        + _btn(f"{PUBLIC_APP_URL}/volunteer#log-hours", "Log More Hours", primary=True) +
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">With gratitude,<br/>The Caring Sisters Club</p></td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you logged volunteer hours on our website. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _send_volunteer_thanks() -> int:
    """At most one thank-you per volunteer per day, combining all approved-but-unthanked entries."""
    today = datetime.now(timezone.utc).date().isoformat()
    year_start = f"{today[:4]}-01-01"
    sent = 0
    for email in await db.volunteer_hours.distinct("email", {"status": "approved", "thanked": {"$ne": True}}):
        if await db.volunteer_thanks.find_one({"email": email, "day": today}):
            continue
        entries = await db.volunteer_hours.find({"email": email, "status": "approved", "thanked": {"$ne": True}}, {"_id": 0}).sort("date", 1).to_list(100)
        try:
            await db.volunteer_thanks.insert_one({"email": email, "day": today, "entries": len(entries), "sent_at": _now_iso()})
        except Exception:
            continue
        await db.volunteer_hours.update_many({"id": {"$in": [e["id"] for e in entries]}}, {"$set": {"thanked": True, "thanked_at": _now_iso()}})
        year_total, all_total = await _hours_total(email, year_start), await _hours_total(email)
        first = entries[-1]["name"].split()[0]
        badges = await _award_milestones(email, today[:4], year_total, all_total)
        try:
            if await send_email(to=email, subject="Thank you for volunteering with The Caring Sisters Club",
                                html=_vol_thanks_html(first, entries, year_total, all_total, badges)) is not None:
                sent += 1
        except Exception as e:
            logging.error(f"Volunteer thank-you failed: {e}")
        for b in badges:
            try:
                await send_email(to=email, subject=f"You earned a badge: {b['label']}!", html=_milestone_html(first, b, year_total, all_total))
            except Exception as e:
                logging.error(f"Milestone badge email failed: {e}")
    return sent


VOL_MILESTONES = (10, 50, 100)


async def _award_milestones(email: str, year: str, year_total: float, all_total: float) -> list:
    """Records each newly crossed milestone exactly once (all-time and per calendar year)."""
    out = []
    for scope, total, label in (("all", all_total, "{n} Hours All-Time"), (f"year:{year}", year_total, "{n} Hours in " + year)):
        for n in VOL_MILESTONES:
            if total >= n:
                r = await db.volunteer_milestones.update_one({"email": email, "scope": scope, "threshold": n},
                                                             {"$setOnInsert": {"hours": total, "awarded_at": _now_iso()}}, upsert=True)
                if r.upserted_id is not None:
                    out.append({"scope": scope, "threshold": n, "label": label.format(n=n)})
    return out


def _milestone_html(name: str, b: dict, year_total: float, all_total: float) -> str:
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Volunteer Milestone") +
        '<tr><td style="padding:36px 32px;font-family:Arial,sans-serif;color:#241019;text-align:center">'
        f'<div style="display:inline-block;width:120px;height:120px;border-radius:50%;background:#3B0A2E;border:5px solid #CBA24B;color:#CBA24B;font-family:Georgia,serif;font-size:36px;font-weight:bold;line-height:120px;margin:0 0 18px">{b["threshold"]}h</div>'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:26px;margin:0 0 10px">Congratulations, {_esc(name)}!</h1>'
        f'<p style="font-size:15px;line-height:1.7;color:#4a3340;margin:0 0 8px">You have earned the <strong>{_esc(b["label"])}</strong> badge.</p>'
        f'<p style="font-size:13.5px;line-height:1.7;color:#6b5560;margin:0 0 22px">That is {year_total:g} hours this year and {all_total:g} hours all-time given to our sisterhood. Thank you for showing up again and again.</p>'
        + _btn(f"{PUBLIC_APP_URL}/volunteer#log-hours", "Keep Going", primary=True) +
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you logged volunteer hours on our website. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


# ---------- Enrollment reminders (staff digest) ----------
def _enroll_digest_html(items: list) -> str:
    rows = "".join(f'<tr><td style="padding:8px 14px;font-size:13px;color:#3B0A2E;font-weight:bold">{_esc(s["data"].get("name", ""))}</td>'
                   f'<td style="padding:8px 14px;font-size:12.5px;color:#4a3340">{_esc(s["data"].get("program", ""))}</td>'
                   f'<td style="padding:8px 14px;font-size:12.5px;color:#4a3340">{_esc(s["data"].get("email", ""))}</td>'
                   f'<td style="padding:8px 14px;font-size:12px;color:#9b3b4f;text-align:right">{(datetime.now(timezone.utc) - datetime.fromisoformat(s["created_at"])).days}d</td></tr>' for s in items[:100])
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="640" style="max-width:640px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header("Sign-Ups Waiting") +
        '<tr><td style="padding:30px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:22px;margin:0 0 10px">{len(items)} sign-up{"s" if len(items) != 1 else ""} still marked "New" after 7+ days</h1>'
        '<p style="font-size:13.5px;line-height:1.6;color:#4a3340;margin:0 0 16px">These sisters are waiting to hear from us. Reach out and update their stage to Contacted, Enrolled, or Not a fit.</p>'
        f'<table role="presentation" width="100%" style="background:#faf2f7;border-radius:12px;margin:0 0 18px">{rows}</table>'
        + _btn(f"{PUBLIC_APP_URL}/admin", "Open Form Submissions", primary=True) +
        '</td></tr></table></td></tr></table>'
    )


async def _send_enrollment_reminders(force: bool = False) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    items = await db.submissions.find(_overdue_q(), {"_id": 0}).sort("created_at", 1).to_list(1000)
    to = (await _get_settings()).get("staff_notify_email")
    if not items or not to:
        return {"overdue": len(items), "sent": False}
    if not force and await db.scheduled_runs.find_one({"key": f"enroll-remind:{today}"}):
        return {"overdue": len(items), "sent": False}
    res = await send_email(to=to, subject=f"Reminder: {len(items)} program sign-up{'s' if len(items) != 1 else ''} waiting 7+ days", html=_enroll_digest_html(items))
    if res is None:
        if force:
            raise HTTPException(status_code=502, detail="The reminder email could not be sent.")
        return {"overdue": len(items), "sent": False}
    await db.scheduled_runs.update_one({"key": f"enroll-remind:{today}"}, {"$set": {"ran_at": _now_iso(), "count": len(items)}}, upsert=True)
    return {"overdue": len(items), "sent": True}


@api_router.post("/admin/signups/send-reminders")
async def admin_send_enroll_reminders(user=Depends(require_admin)):
    return await _send_enrollment_reminders(force=True)


# ---------- Year in Review ----------
async def _yir_public_years() -> list:
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0, "yir_public": 1}) or {}
    return doc.get("yir_public") or []


async def _year_in_review(year: int) -> dict:
    y = str(year)
    nxt = str(year + 1)
    rng = {"$gte": f"{y}-01-01", "$lt": f"{nxt}-01-01"}
    paid = await db.payment_transactions.find({"payment_status": "paid", "created_at": rng}, {"_id": 0, "amount": 1, "donor_email": 1}).to_list(20000)
    donors = {(t.get("donor_email") or "").lower() for t in paid if t.get("donor_email")}
    anon = sum(1 for t in paid if not t.get("donor_email"))
    hrs = await db.volunteer_hours.find({"status": "approved", "date": rng}, {"_id": 0, "hours": 1, "email": 1}).to_list(20000)
    stories = await db.story_submissions.find({"status": "approved", "created_at": rng}, {"_id": 0}).sort("created_at", -1).to_list(500)
    signups = await db.submissions.count_documents({"type": "program_signup", "created_at": rng})
    enrolled = await db.submissions.count_documents({"type": "program_signup", "created_at": rng, "stage": "enrolled"})
    return {
        "year": year,
        "donations_total": round(sum(float(t.get("amount") or 0) for t in paid), 2),
        "gifts": len(paid), "donors": len(donors) + anon,
        "volunteer_hours": round(sum(h["hours"] for h in hrs), 1), "volunteers": len({h["email"] for h in hrs}),
        "stories": len(stories), "signups": signups, "enrolled": enrolled,
        "featured_stories": [{"name": _short_name(s["name"]), "role": s.get("role", ""), "quote": s["quote"], "photo_url": s.get("photo_url", ""),
                              "program": s.get("program_title") or ""} for s in stories[:6]],
    }


@api_router.get("/year-in-review/{year}")
async def public_year_in_review(year: int):
    if year not in await _yir_public_years():
        raise HTTPException(status_code=404, detail="This Year in Review is not published yet.")
    return await _year_in_review(year)


@api_router.get("/admin/year-in-review/{year}")
async def admin_year_in_review(year: int, user=Depends(require_admin)):
    if not 2000 <= year <= 2100:
        raise HTTPException(status_code=400, detail="Invalid year")
    site = await _yir_site()
    return {**await _year_in_review(year), "public": year in (site.get("yir_public") or []), "autosend": bool(site.get("yir_autosend")),
            "image_url": (site.get("yir_images") or {}).get(str(year), "")}


class YirPublishIn(BaseModel):
    public: Optional[bool] = None
    autosend: Optional[bool] = None
    image_url: Optional[str] = None


async def _yir_site() -> dict:
    return await db.settings.find_one({"key": "site"}, {"_id": 0, "yir_public": 1, "yir_images": 1, "yir_autosend": 1}) or {}


@api_router.put("/admin/year-in-review/{year}")
async def admin_publish_yir(year: int, payload: YirPublishIn, background: BackgroundTasks, user=Depends(require_admin)):
    if not 2000 <= year <= 2100:
        raise HTTPException(status_code=400, detail="Invalid year")
    if payload.public is not None:
        op = {"$addToSet": {"yir_public": year}} if payload.public else {"$pull": {"yir_public": year}}
        await db.settings.update_one({"key": "site"}, op, upsert=True)
    if payload.autosend is not None:
        await db.settings.update_one({"key": "site"}, {"$set": {"yir_autosend": bool(payload.autosend)}}, upsert=True)
    if payload.image_url is not None:
        img = payload.image_url.strip()
        if img and not re.match(r"^/api/media/file/[A-Za-z0-9-]+$", img):
            raise HTTPException(status_code=400, detail="Share image must be an uploaded image.")
        await db.settings.update_one({"key": "site"}, {"$set": {f"yir_images.{year}": img}}, upsert=True)
    site = await _yir_site()
    queued = False
    if payload.public and site.get("yir_autosend") and not await db.yir_emails.find_one({"year": year}):
        queued = await _queue_yir_send(year, background, user.get("email"), "auto-publish")
    return {"year": year, "public": year in (site.get("yir_public") or []), "autosend": bool(site.get("yir_autosend")),
            "image_url": (site.get("yir_images") or {}).get(str(year), ""), "email_queued": queued}


# ---------- Year in Review: share card & share page ----------
_FONT_DIR = ROOT_DIR / "fonts"


def _yir_card_png(d: dict) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#3B0A2E")
    dr = ImageDraw.Draw(img)
    dr.ellipse((820, -220, 1420, 380), fill="#4d1240")
    dr.ellipse((-160, 420, 260, 840), fill="#5a1a4b")
    dr.rectangle((0, 0, W, 10), fill="#CBA24B")
    f = lambda name, size: ImageFont.truetype(str(_FONT_DIR / name), size)  # noqa: E731
    try:
        logo = Image.open(ROOT_DIR / "brand_logo.png").convert("RGBA")
        logo.thumbnail((110, 110))
        img.paste(logo, (70, 60), logo)
    except Exception:
        pass
    dr.text((200, 78), "THE CARING SISTERS CLUB", font=f("LiberationSans-Bold.ttf", 26), fill="#CBA24B")
    dr.text((200, 118), "Year in Review", font=f("LiberationSans-Regular.ttf", 26), fill="#F7EFE9")
    dr.text((70, 200), f"{d['year']}: A year of sisterhood", font=f("LiberationSerif-Bold.ttf", 68), fill="#F7EFE9")
    stats = [(f"${int(round(d['donations_total'])):,}", "raised"), (f"{d['volunteer_hours']:g}", "volunteer hours"),
             (f"{d['signups']:,}", "program sign-ups"), (f"{d['stories']:,}", "stories shared")]
    x = 70
    for v, lbl in stats:
        dr.rounded_rectangle((x, 340, x + 250, 520), radius=22, fill="#4d1240", outline="#CBA24B", width=2)
        dr.text((x + 24, 370), v, font=f("LiberationSerif-Bold.ttf", 52 if len(v) < 8 else 40), fill="#CBA24B")
        dr.text((x + 24, 462), lbl, font=f("LiberationSans-Regular.ttf", 22), fill="#F7EFE9")
        x += 270
    dr.text((70, 560), "See what we built together", font=f("LiberationSans-Bold.ttf", 24), fill="#D14FA0")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


async def _yir_visible(year: int, request: Request) -> bool:
    if year in ((await _yir_site()).get("yir_public") or []):
        return True
    try:
        await require_admin(request)
        return True
    except HTTPException:
        return False


@api_router.get("/share/year-in-review/{year}/card.png")
async def yir_card(year: int, request: Request):
    if not await _yir_visible(year, request):
        raise HTTPException(status_code=404, detail="Not published")
    png = await asyncio.to_thread(_yir_card_png, await _year_in_review(year))
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=600"})


@api_router.get("/share/year-in-review/{year}")
async def yir_share_page(year: int):
    site = await _yir_site()
    if year not in (site.get("yir_public") or []):
        raise HTTPException(status_code=404, detail="Not published")
    d = await _year_in_review(year)
    custom = (site.get("yir_images") or {}).get(str(year))
    img = f"{PUBLIC_APP_URL}{custom}" if custom else f"{PUBLIC_APP_URL}/api/share/year-in-review/{year}/card.png"
    page = f"{PUBLIC_APP_URL}/year-in-review/{year}"
    title = f"{year} Year in Review | The Caring Sisters Club"
    desc = f"${int(round(d['donations_total'])):,} raised, {d['volunteer_hours']:g} volunteer hours and {d['signups']:,} program sign-ups. See what we built together."
    e = _esc
    body = (f'<!doctype html><html><head><meta charset="utf-8"><title>{e(title)}</title>'
            f'<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
            f'<meta property="og:image" content="{e(img)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta property="og:url" content="{e(page)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}">'
            f'<meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(img)}"><meta name="description" content="{e(desc)}">'
            f'<link rel="canonical" href="{e(page)}"><meta http-equiv="refresh" content="0; url={e(page)}"></head>'
            f'<body><p>Redirecting to <a href="{e(page)}">our {year} Year in Review</a>…</p></body></html>')
    return HTMLResponse(body)


# ---------- Year in Review: email distribution ----------
async def _yir_recipients(year: int) -> list:
    rng = {"$gte": f"{year}-01-01", "$lt": f"{year + 1}-01-01"}
    out = {}
    async for t in db.payment_transactions.find({"payment_status": "paid", "created_at": rng, "donor_email": {"$nin": [None, ""]}}, {"_id": 0, "donor_email": 1, "donor_name": 1}):
        out.setdefault(t["donor_email"].strip().lower(), t.get("donor_name") or "")
    async for h in db.volunteer_hours.find({"status": "approved", "date": rng}, {"_id": 0, "email": 1, "name": 1}):
        out.setdefault(h["email"].lower(), h.get("name") or "")
    return [{"email": k, "name": v} for k, v in out.items() if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", k)]


def _yir_email_html(d: dict, name: str) -> str:
    stat = lambda v, l: (f'<td width="50%" style="padding:14px;text-align:center"><p style="font-family:Georgia,serif;font-size:28px;color:#B4247E;font-weight:bold;margin:0">{v}</p>'  # noqa: E731
                         f'<p style="font-size:12px;color:#6b5560;margin:4px 0 0">{l}</p></td>')
    stories = "".join(f'<p style="font-size:14px;line-height:1.7;color:#4a3340;font-style:italic;margin:0 0 6px">&ldquo;{_esc(s["quote"][:260])}&rdquo;</p>'
                      f'<p style="font-size:12px;color:#B4247E;font-weight:bold;margin:0 0 16px">{_esc(s["name"])}</p>' for s in d["featured_stories"][:2])
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        + _brand_header(f"{d['year']} Year in Review") +
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:24px;margin:0 0 14px">Dear {_esc(name or "friend")}, look what we did together</h1>'
        f'<p style="font-size:14px;line-height:1.7;color:#4a3340;margin:0 0 18px">Because of you, {d["year"]} was a year of real sisterhood. Here is a look at what our community achieved.</p>'
        '<table role="presentation" width="100%" style="border:1px solid #eadfe6;border-radius:12px;margin:0 0 20px">'
        f'<tr>{stat("$" + format(int(round(d["donations_total"])), ","), "raised")}{stat(format(d["volunteer_hours"], "g"), "volunteer hours")}</tr>'
        f'<tr>{stat(format(d["signups"], ","), "program sign-ups")}{stat(format(d["stories"], ","), "member stories")}</tr></table>'
        + (f'<div style="background:#faf2f7;border-radius:12px;padding:18px 20px 4px;margin:0 0 20px">{stories}</div>' if stories else "")
        + _btn(f"{PUBLIC_APP_URL}/year-in-review/{d['year']}", "See Our Year in Review", primary=True) +
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">With gratitude,<br/>The Caring Sisters Club</p></td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">You are receiving this because you donated or volunteered with us this year. We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _run_yir_send(year: int, log_id: str):
    d = await _year_in_review(year)
    sent = failed = 0
    for r in await _yir_recipients(year):
        try:
            ok = await send_email(to=r["email"], subject=f"Our {year} Year in Review: look what we did together", html=_yir_email_html(d, (r["name"] or "").split(" ")[0]))
        except Exception as e:
            logging.error(f"YIR email failed: {e}")
            ok = None
        sent, failed = (sent + 1, failed) if ok is not None else (sent, failed + 1)
        await asyncio.sleep(0.6)
    await db.yir_emails.update_one({"id": log_id}, {"$set": {"status": "done", "sent": sent, "failed": failed, "finished_at": _now_iso()}})


async def _queue_yir_send(year: int, background: BackgroundTasks, by: str, trigger: str) -> bool:
    rec = await _yir_recipients(year)
    if not rec:
        return False
    log_id = str(uuid.uuid4())
    await db.yir_emails.insert_one({"id": log_id, "year": year, "recipients": len(rec), "status": "sending", "trigger": trigger, "by": by, "started_at": _now_iso()})
    background.add_task(_run_yir_send, year, log_id)
    return True


@api_router.get("/admin/year-in-review/{year}/email")
async def admin_yir_email_preview(year: int, user=Depends(require_admin)):
    rec = await _yir_recipients(year)
    log = await db.yir_emails.find({"year": year}, {"_id": 0}).sort("started_at", -1).to_list(20)
    return {"html": _yir_email_html(await _year_in_review(year), "Sister"), "recipients": len(rec), "history": log}


class YirTestIn(BaseModel):
    email: str


@api_router.post("/admin/year-in-review/{year}/email/test")
async def admin_yir_email_test(year: int, payload: YirTestIn, user=Depends(require_admin)):
    em = payload.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if await send_email(to=em, subject=f"[Test] Our {year} Year in Review", html=_yir_email_html(await _year_in_review(year), "Sister")) is None:
        raise HTTPException(status_code=502, detail="The test email could not be sent.")
    return {"sent": True}


class YirSendIn(BaseModel):
    force: bool = False


@api_router.post("/admin/year-in-review/{year}/email/send")
async def admin_yir_email_send(year: int, payload: YirSendIn, background: BackgroundTasks, user=Depends(require_admin)):
    if year not in ((await _yir_site()).get("yir_public") or []):
        raise HTTPException(status_code=400, detail="Publish the Year in Review page first so the email link works.")
    if not payload.force and await db.yir_emails.find_one({"year": year}):
        raise HTTPException(status_code=409, detail="This Year in Review was already emailed. Confirm to send again.")
    if not await _queue_yir_send(year, background, user.get("email"), "manual"):
        raise HTTPException(status_code=400, detail="No donors or volunteers to email for this year.")
    return {"queued": True, "recipients": len(await _yir_recipients(year))}


@api_router.get("/volunteer-hours/leaderboard")
async def hours_leaderboard():
    year = datetime.now(timezone.utc).strftime("%Y")
    out = []
    async for r in db.volunteer_hours.aggregate([
        {"$match": {"status": "approved", "date": {"$gte": f"{year}-01-01"}}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$email", "hours": {"$sum": "$hours"}, "name": {"$first": "$name"}, "opt": {"$first": "$leaderboard"}}},
        {"$match": {"opt": True}}, {"$sort": {"hours": -1}}, {"$limit": 10},
    ]):
        top = await db.volunteer_milestones.find_one({"email": r["_id"], "scope": "all"}, {"_id": 0, "threshold": 1}, sort=[("threshold", -1)])
        out.append({"name": _short_name(r["name"]), "hours": round(r["hours"], 1), "badge": (top or {}).get("threshold")})
    return {"year": year, "items": out}


# ---------- Story request results & sign-up stages ----------
@api_router.get("/admin/reports/story-requests")
async def report_story_requests(user=Depends(require_admin)):
    invites = await db.submissions.find({"type": "program_signup", "story_request_sent": True}, {"_id": 0, "data.email": 1, "story_request_at": 1}).to_list(5000)
    submitted = approved = 0
    for inv in invites:
        em = ((inv.get("data") or {}).get("email") or "").lower()
        st = await db.story_submissions.find_one({"email": em, "created_at": {"$gte": inv.get("story_request_at") or ""}}, {"_id": 0, "status": 1}, sort=[("created_at", 1)]) if em else None
        if st:
            submitted += 1
            approved += 1 if st["status"] == "approved" else 0
    n = len(invites)
    return {"invites": n, "submitted": submitted, "approved": approved, "rate": round(submitted / n * 100, 1) if n else 0}


class StageIn(BaseModel):
    stage: str


@api_router.put("/admin/submissions/{sid}/stage")
async def set_signup_stage(sid: str, payload: StageIn, background: BackgroundTasks, user=Depends(require_admin)):
    if payload.stage not in ("new", "contacted", "enrolled", "not_fit"):
        raise HTTPException(status_code=400, detail="Invalid stage")
    sub = await db.submissions.find_one_and_update({"id": sid, "type": "program_signup"}, {"$set": {"stage": payload.stage, "stage_at": _now_iso(), "read": True}})
    if not sub:
        raise HTTPException(status_code=404, detail="Sign-up not found")
    pid = await _signup_program_id(sub)
    if pid:
        background.add_task(_fill_seats, pid)
    return {"stage": payload.stage}


# ---------- Recurring Reminders (pre-renewal heads-up) ----------
def _reminder_email_html(name: str, amount, next_date: str) -> str:
    when = f" around <strong>{_esc(next_date)}</strong>" if next_date else " soon"
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0"><tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden">'
        '<tr><td style="background:#3B0A2E;padding:26px 32px;color:#F7EFE9;font-family:Georgia,serif">'
        '<div style="font-size:19px;font-weight:bold">The Caring Sisters Club</div>'
        '<div style="font-size:11px;color:#CBA24B;letter-spacing:3px;text-transform:uppercase;margin-top:4px">Monthly Gift Reminder</div></td></tr>'
        '<tr><td style="padding:32px;font-family:Arial,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#3B0A2E;font-size:22px;margin:0 0 12px">Hello {_esc(name)},</h1>'
        f'<p style="font-size:14px;line-height:1.6;color:#4a3340;margin:0 0 16px">This is a friendly heads-up that your recurring monthly gift of <strong>${_esc(str(amount))}</strong> to The Caring Sisters Club will renew{when}. There is nothing you need to do &mdash; we just like to keep you informed.</p>'
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:0 0 8px">Thank you for your continued generosity. If you would like to update or pause your gift, simply reply to this email and our team will help.</p>'
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:16px 0 0">With gratitude,<br/>The Caring Sisters Club</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif"><p style="font-size:11px;color:#b79aae;margin:0">We never ask for your password or card details by email.</p></td></tr>'
        '</table></td></tr></table>'
    )


async def _send_renewal_reminders() -> dict:
    """Email active monthly donors a heads-up ~3 days before their next charge."""
    sub_ids = await db.payment_transactions.distinct(
        "stripe_subscription_id", {"frequency": "monthly", "payment_status": "paid"}
    )
    sent = 0
    today = datetime.now(timezone.utc).date()
    for sub_id in sub_ids:
        if not sub_id:
            continue
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            if sub.get("status") not in ("active", "trialing"):
                continue
            period_end = sub.get("current_period_end")
            if not period_end:
                continue
            renew_date = datetime.fromtimestamp(period_end, tz=timezone.utc).date()
            days = (renew_date - today).days
            if days != 3:  # only 3 days before renewal
                continue
            key = f"{sub_id}:{renew_date.isoformat()}"
            if await db.reminders_sent.find_one({"key": key}):
                continue
            orig = await db.payment_transactions.find_one({"stripe_subscription_id": sub_id}, {"_id": 0})
            email = (orig.get("donor_email") if orig else "") or ""
            if not email:
                continue
            name = (orig.get("donor_name") or "").strip() or "Friend"
            amount = orig.get("amount")
            html = _reminder_email_html(name, amount, renew_date.strftime("%B %d, %Y"))
            if await send_email(to=email, subject="Your monthly gift renews soon — The Caring Sisters Club", html=html) is not None:
                sent += 1
            await db.reminders_sent.insert_one({"key": key, "sent_at": datetime.now(timezone.utc).isoformat()})
        except Exception as e:
            logging.warning(f"Renewal reminder failed for {sub_id}: {e}")
    return {"sent": sent, "subscriptions_checked": len(sub_ids)}


@api_router.post("/admin/recurring/send-reminders")
async def trigger_renewal_reminders(user=Depends(require_admin)):
    return await _send_renewal_reminders()


async def _send_lapsed_reactivations() -> dict:
    """Daily: auto-send a 'we miss you' email to newly-lapsed monthly donors, with a cooldown."""
    settings = await _get_settings()
    if not settings.get("lapsed_autoemail_enabled"):
        return {"sent": 0, "skipped": "disabled"}
    cooldown_days = int(settings.get("lapsed_cooldown_days") or 30)
    now = datetime.now(timezone.utc)
    paid = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(5000)
    # Build per-email monthly profiles
    profiles = {}
    for t in paid:
        email = (t.get("donor_email") or "").strip().lower()
        if not email:
            continue
        p = profiles.setdefault(email, {"name": "", "last_monthly": "", "has_monthly": False})
        if t.get("frequency") == "monthly":
            p["has_monthly"] = True
            upd = t.get("updated_at") or ""
            if upd > p["last_monthly"]:
                p["last_monthly"] = upd
            if not t.get("anonymous") and (t.get("donor_name") or "").strip():
                p["name"] = t["donor_name"].strip()
    sent = 0
    for email, p in profiles.items():
        if not (p["has_monthly"] and _is_lapsed(p["last_monthly"])):
            continue
        last = await db.reactivation_sent.find_one({"email": email}, {"_id": 0}, sort=[("sent_at", -1)])
        if last and last.get("sent_at"):
            try:
                prev = datetime.fromisoformat(last["sent_at"].replace("Z", "+00:00"))
                if prev.tzinfo is None:
                    prev = prev.replace(tzinfo=timezone.utc)
                if (now - prev).days < cooldown_days:
                    continue  # still within cooldown
            except ValueError:
                pass
        result = await send_email(
            to=email,
            subject="We miss you at The Caring Sisters Club",
            html=_reactivation_email_html(p["name"] or "Friend"),
        )
        await db.reactivation_sent.insert_one({
            "email": email, "sent_at": now.isoformat(), "sent_by": "scheduler",
            "delivered": result is not None, "auto": True,
        })
        if result is not None:
            sent += 1
    return {"sent": sent}


# ---------- Background scheduler (daily tasks) ----------
import asyncio


async def _daily_scheduler():
    """Runs daily: Jan 1 -> send prior-year statements; every day -> renewal reminders."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            # Year-end statements: run once on Jan 1 for the previous year
            if now.month == 1 and now.day == 1:
                prev_year = now.year - 1
                marker = f"statements:{prev_year}"
                if not await db.scheduled_runs.find_one({"key": marker}):
                    result = await _run_year_statements(prev_year)
                    await db.scheduled_runs.insert_one({"key": marker, "ran_at": now.isoformat(), "result": result})
                    logging.info(f"Auto year-end statements sent for {prev_year}: {result}")
            # Daily renewal reminders
            await _send_renewal_reminders()
            # Daily lapsed-donor reactivation emails (with cooldown)
            await _send_lapsed_reactivations()
            # Daily: dispatch any scheduled segment appeals that are now due
            await _run_scheduled_appeals()
            # Daily: day-before reminders for event RSVPs
            await _send_event_reminders()
            await _process_all_waitlists()
            await _check_cancellations()
            await _maybe_monthly_impact()
            await _send_story_requests()
            await _send_enrollment_reminders()
            await db.donor_manage_tokens.delete_many({"expires_at": {"$lt": datetime.now(timezone.utc).isoformat()}})
        except Exception as e:
            logging.error(f"Daily scheduler error: {e}")
        await asyncio.sleep(24 * 60 * 60)  # once per day


async def _hourly_scheduler():
    while True:
        await asyncio.sleep(3600)
        try:
            await _process_all_waitlists()
            await _send_volunteer_thanks()
            for p in await db.programs.find({"capacity": {"$gt": 0}}, {"_id": 0, "id": 1}).to_list(200):
                await _fill_seats(p["id"])
        except Exception as e:
            logging.error(f"Hourly waitlist job failed: {e}")


@app.on_event("startup")
async def _start_scheduler():
    await _refresh_site_url()
    asyncio.create_task(_daily_scheduler())
    asyncio.create_task(_hourly_scheduler())





MILESTONES = [25, 50, 100]



def _milestone_email_html(pct: int, raised: float, goal: float, title: str) -> str:
    title = title or "our fundraising campaign"
    return (
        '<table role="presentation" width="100%" style="background:#f7efe9;padding:0;margin:0">'
        '<tr><td align="center" style="padding:28px 16px">'
        '<table role="presentation" width="600" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden">'
        '<tr><td style="background:#3B0A2E;padding:26px 32px;color:#F7EFE9;font-family:Georgia,serif">'
        '<div style="font-size:19px;font-weight:bold">The Caring Sisters Club</div>'
        '<div style="font-size:11px;color:#CBA24B;letter-spacing:3px;text-transform:uppercase;margin-top:4px">Campaign Update</div>'
        '</td></tr>'
        '<tr><td style="padding:32px;font-family:Arial,Helvetica,sans-serif;color:#241019">'
        f'<h1 style="font-family:Georgia,serif;color:#B4247E;font-size:30px;margin:0 0 8px">{pct}% reached!</h1>'
        f'<p style="font-size:15px;line-height:1.6;color:#4a3340;margin:0 0 16px">Great news &mdash; <strong>{_esc(title)}</strong> has reached <strong>{pct}%</strong> of its goal.</p>'
        '<table role="presentation" width="100%" style="background:#faf2f7;border-radius:12px">'
        f'<tr><td style="padding:16px 22px;font-size:14px;color:#3B0A2E">Raised so far</td>'
        f'<td align="right" style="padding:16px 22px;font-size:18px;font-weight:bold;color:#B4247E">${_esc(f"{raised:,.0f}")} of ${_esc(f"{goal:,.0f}")}</td></tr>'
        '</table>'
        '<p style="font-size:13px;line-height:1.6;color:#6b5560;margin:18px 0 0">This is an automated update for staff. Keep up the wonderful work!</p>'
        '</td></tr>'
        '<tr><td style="background:#29061F;padding:16px 32px;font-family:Arial,sans-serif">'
        '<p style="font-size:11px;color:#b79aae;margin:0">Sent by The Caring Sisters Club admin system.</p>'
        '</td></tr>'
        '</table></td></tr></table>'
    )


async def _check_milestones():
    try:
        settings = await _get_settings()
        goal = float(settings.get("goal") or 0)
        if goal <= 0:
            return
        paid = await db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}).to_list(5000)
        total = sum(float(t.get("amount", 0)) for t in paid)
        pct = (total / goal) * 100
        for m in MILESTONES:
            if pct < m:
                continue
            already = await db.milestones_sent.find_one({"goal": goal, "milestone": m})
            if already:
                continue
            await db.milestones_sent.insert_one({
                "goal": goal, "milestone": m,
                "total_at_send": round(total, 2),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            })
            admins = await db.users.find({"role": "admin"}, {"_id": 0, "email": 1}).to_list(200)
            html = _milestone_email_html(m, total, goal, settings.get("campaign_title"))
            for a in admins:
                if a.get("email"):
                    await send_email(
                        to=a["email"],
                        subject=f"Milestone reached: {m}% of your fundraising goal!",
                        html=html,
                    )
    except Exception as e:
        logging.error(f"Milestone check failed: {e}")


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
        await db.cancellations.create_index("sub_id", unique=True)
        await db.volunteer_thanks.create_index([("email", 1), ("day", 1)], unique=True)
        await db.volunteer_milestones.create_index([("email", 1), ("scope", 1), ("threshold", 1)], unique=True)
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


# CSRF protection (SEC-002): require a custom header on any state-changing request
# that carries a session cookie. A cross-site <form> auto-POST sends the victim's
# cookie but cannot set a custom header (and a cross-origin XHR that tries is blocked
# by CORS). Requests without a session cookie (Stripe webhook, public forms) are
# unaffected, as are safe methods.
from starlette.responses import JSONResponse as _JSONResponse

_CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


@app.middleware("http")
async def csrf_protect(request: Request, call_next):
    if (
        request.method not in _CSRF_SAFE_METHODS
        and request.cookies.get("session_token")
        and request.headers.get("x-requested-with") != "XMLHttpRequest"
    ):
        return _JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
    return await call_next(request)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()