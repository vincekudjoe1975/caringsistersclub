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
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": data.get("name"),
            "picture": data.get("picture"),
            "role": "admin",
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
    user=Depends(get_current_user),
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
async def delete_media(item_id: str, user=Depends(get_current_user)):
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
        "status": "initiated",
        "payment_status": "pending",
        "created_at": now,
        "updated_at": now,
    })
    return {"checkout_url": session.url, "session_id": session.id}


async def _record_paid_donation(session_id: str, txn: dict):
    """Insert a donation submission once, so staff see it in the admin inbox."""
    existing = await db.submissions.find_one({"data.session_id": session_id})
    if existing:
        return
    await db.submissions.insert_one({
        "id": str(uuid.uuid4()),
        "type": "donation",
        "data": {
            "name": txn.get("donor_name") or "Anonymous",
            "email": txn.get("donor_email") or "",
            "amount": f"${txn.get('amount')}",
            "frequency": txn.get("frequency"),
            "status": "Paid",
            "session_id": session_id,
        },
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


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
                await _record_paid_donation(session_id, record)
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
            await _record_paid_donation(obj["id"], txn)
    elif t == "checkout.session.expired":
        await db.payment_transactions.update_one(
            {"session_id": obj["id"]},
            {"$set": {"status": "expired", "payment_status": "expired", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    return {"status": "ok"}


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
async def list_submissions(type: Optional[str] = None, user=Depends(get_current_user)):
    query = {}
    if type:
        query["type"] = type
    items = await db.submissions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


@api_router.get("/submissions/counts")
async def submission_counts(user=Depends(get_current_user)):
    out = {}
    for t in ALLOWED_SUB_TYPES:
        total = await db.submissions.count_documents({"type": t})
        unread = await db.submissions.count_documents({"type": t, "read": False})
        out[t] = {"total": total, "unread": unread}
    return out


@api_router.patch("/submissions/{item_id}/read")
async def mark_submission_read(item_id: str, user=Depends(get_current_user)):
    await db.submissions.update_one({"id": item_id}, {"$set": {"read": True}})
    return {"message": "ok"}


@api_router.delete("/submissions/{item_id}")
async def delete_submission(item_id: str, user=Depends(get_current_user)):
    await db.submissions.delete_one({"id": item_id})
    return {"message": "Deleted"}


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