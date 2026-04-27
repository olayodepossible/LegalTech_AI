"""
FastAPI backend for FinPlex Financial Advisor
Handles all API routes with Clerk JWT authentication
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import urllib
import urllib.error
import uuid
import re

from fastapi import FastAPI, HTTPException, Depends, status, Request, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
import boto3
from botocore.exceptions import ClientError
from mangum import Mangum
from dotenv import load_dotenv
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials

from src import Database
from src.schemas import (UserCreate, ActivityHistoryCreate)

from contract_analyst.schemas import ContractAnalysisResult
from contract_analyst.service import analyze_contract_bytes

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class StructuredLogger:
    @staticmethod
    def log_event(event_type, user_id=None, details=None):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details
        }
        logger.info(json.dumps(log_entry))


def _schema_missing_response(exc: BaseException) -> Optional[HTTPException]:
    """Map Aurora undefined_table / missing relation to a clear 503 for operators."""
    text = str(exc)
    if "42P01" in text or ("does not exist" in text and "relation" in text):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database schema is not applied (tables such as 'users' are missing). "
            ),
        )
    return None


# Initialize FastAPI app
app = FastAPI(
    title="Legal Companion API",
    description="Backend API for AI-powered Legal Companion",
    version="1.0.0"
)

# CORS configuration
# Get origins from CORS_ORIGINS env var (comma-separated) or fall back to localhost
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers for better error messages
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with user-friendly messages"""
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid input data. Please check your request and try again."}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with improved messages"""
    # Map technical errors to user-friendly messages
    user_friendly_messages = {
        401: "Your session has expired. Please sign in again.",
        403: "You don't have permission to access this resource.",
        404: "The requested resource was not found.",
        429: "Too many requests. Please slow down and try again later.",
        500: "An internal error occurred. Please try again later.",
        503: "The service is temporarily unavailable. Please try again later."
    }

    message = user_friendly_messages.get(exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": message}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Our team has been notified."}
    )

# Initialize services
db = Database()


def _clerk_profile_from_token(token_data: Dict[str, Any]) -> tuple[str, str]:
    """Email and display name as stored in ``users`` (aligned with Clerk claims)."""
    email = (token_data.get("email") or "").strip() or "no-email@example.com"
    display_name = (token_data.get("name") or "").strip()
    if not display_name:
        fn = (token_data.get("given_name") or "").strip()
        ln = (token_data.get("family_name") or "").strip()
        display_name = f"{fn} {ln}".strip()
    if not display_name:
        display_name = email.split("@")[0] or "New User"
    return email, display_name


def _resolve_user_row(
    clerk_user_id: str,
    creds: HTTPAuthorizationCredentials,
) -> tuple[Dict[str, Any], bool]:
    """
    Load or insert the ``users`` row for this Clerk id and keep ``display_name`` / ``email``
    in sync with JWT claims (name/email changes in Clerk propagate on the next API call).
    """
    token_data = creds.decoded if isinstance(creds.decoded, dict) else {}
    email, display_name = _clerk_profile_from_token(token_data)

    user = db.users.find_by_clerk_id(clerk_user_id)
    if user:
        if user.get("email") != email or user.get("display_name") != display_name:
            db.users.db.update(
                "users",
                {
                    "display_name": display_name,
                    "email": email,
                    "updated_at": datetime.utcnow(),
                },
                "clerk_user_id = :clerk_user_id",
                {"clerk_user_id": clerk_user_id},
            )
            user = db.users.find_by_clerk_id(clerk_user_id)
        return user, False

    user_data = {
        "clerk_user_id": clerk_user_id,
        "display_name": display_name,
        "email": email,
    }
    db.users.create(user_data, returning="clerk_user_id")
    created = db.users.find_by_clerk_id(clerk_user_id)
    logger.info("Created user row for Clerk id %s", clerk_user_id)
    try:
        db.activity_history.create_activity_history(
            clerk_user_id=clerk_user_id,
            account_name=display_name,
            email=email,
            label="Account ready",
            details="User record created; profile synced from Clerk.",
            activity_type="signup",
        )
    except Exception as e:
        logger.warning("Could not insert signup activity: %s", e)
    return created, True


# SQS — region must match the queue URL (cross-region clients get errors)
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "").strip()

def _sqs_region_from_queue_url(queue_url: str) -> str:
    m = re.search(r"sqs\.([a-z0-9-]+)\.amazonaws\.com", queue_url or "")
    if m:
        return m.group(1)
    return os.getenv("DEFAULT_AWS_REGION", "eu-west-2")


def _sqs_client_for_queue(queue_url: str):
    return boto3.client("sqs", region_name=_sqs_region_from_queue_url(queue_url))

# Clerk authentication setup (exactly like saas reference)
clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)

async def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(clerk_guard)) -> str:
    """Extract user ID from validated Clerk token"""
    # The clerk_guard dependency already validated the token
    # creds.decoded contains the JWT payload
    user_id = creds.decoded["sub"]
    logger.info(f"Authenticated user: {user_id}")
    return user_id

# Request/Response models
class UserResponse(BaseModel):
    user: Dict[str, Any]
    created: bool

class UserUpdate(BaseModel):
    """Update user settings"""
    display_name: Optional[str] = None
    years_until_retirement: Optional[int] = None
    target_retirement_income: Optional[float] = None
    asset_class_targets: Optional[Dict[str, float]] = None
    region_targets: Optional[Dict[str, float]] = None


class ActivityLogRequest(BaseModel):
    """Client-originated product analytics / journey events (no PII in ``details`` by default)."""

    activity_type: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=255)
    details: Optional[str] = Field(None, max_length=4000)


class PositionUpdate(BaseModel):
    """Update position"""
    quantity: Optional[float] = None

class AnalyzeRequest(BaseModel):
    analysis_type: str = Field(default="portfolio", description="Type of analysis to perform")
    options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")

class AnalyzeResponse(BaseModel):
    job_id: str
    message: str


class LegalChatRequest(BaseModel):
    """POST /api/chat — message is saved to ``legal_chat_messages`` for ``chat_id``."""

    message: str = Field(..., min_length=1, max_length=12000)
    language: str | None = "en"
    chat_id: str = Field(..., min_length=2, max_length=64, description="Chat session UUID")


class LegalChatResponse(BaseModel):
    reply: str


class LegalChatListItem(BaseModel):
    id: str
    title: str
    language: str
    updated_at: Optional[str] = None
    created_at: Optional[str] = None


class LegalChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    language_code: str
    created_at: Optional[str] = None


class CreateLegalChatRequest(BaseModel):
    """Optional body for POST /api/chats; omit ``id`` to let the server pick a UUID."""

    id: Optional[str] = Field(None, description="Client-generated chat UUID (recommended for offline-first UIs)")


def _short_chat_title(text: str, max_len: int = 120) -> str:
    t = " ".join((text or "").split())
    if not t:
        return "New chat"
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _ensure_user_row(clerk_user_id: str) -> None:
    """``legal_chats`` FK requires a ``users`` row; create a minimal one if needed."""
    if db.users.find_by_clerk_id(clerk_user_id):
        return
    try:
        db.users.create_user(clerk_user_id, display_name="User", email=None)
    except Exception as e:
        logger.warning("Could not create placeholder user row: %s", e)
        raise


class RagDocumentUploadResponse(BaseModel):
    document_id: str
    s3_key: str
    bucket: str
    size_bytes: int
    content_type: Optional[str] = None
    ingestion_queued: bool = False
    sqs_message_id: Optional[str] = None
    # Time-limited HTTPS link to download the object (Clerk auth not required for the URL itself).
    download_url: Optional[str] = None


class RagDocumentListItem(BaseModel):
    document_id: str
    name: str
    s3_key: str
    size_bytes: int
    last_modified: Optional[str] = None
    download_url: Optional[str] = None


class RagDocumentListResponse(BaseModel):
    documents: list[RagDocumentListItem]


RAG_DOCUMENTS_BUCKET = os.getenv("RAG_DOCUMENTS_BUCKET", "").strip()
RAG_S3_KEY_PREFIX = os.getenv("RAG_S3_KEY_PREFIX", "rag-documents").strip().strip("/")
# Ingestion: Upload → S3 → (this queue) → worker → S3 Vectors. Falls back to SQS_QUEUE_URL.
RAG_INGESTION_QUEUE_URL = os.getenv("RAG_INGESTION_QUEUE_URL", "").strip()


def _safe_client_filename(name: Optional[str]) -> str:
    if not name:
        return "document"
    base = name.replace("\\", "/").split("/")[-1]
    if ".." in base or not base.strip():
        return "document"
    return base[:240]


def _rag_s3_user_part(clerk_user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._@+-]+", "_", clerk_user_id)[:128]


def _rag_download_presigned_url(
    s3,
    key: str,
    display_filename: str,
) -> Optional[str]:
    disp_name = re.sub(r'[\r\n"]+', " ", display_filename).strip() or "document"
    if not RAG_DOCUMENTS_BUCKET:
        return None
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": RAG_DOCUMENTS_BUCKET,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{disp_name}"',
            },
            ExpiresIn=int(os.getenv("RAG_DOWNLOAD_URL_EXPIRES_SECONDS", "604800")),
        )
    except Exception as e:
        logger.warning("Could not generate presigned download URL for key=%s: %s", key, e)
        return None


def research_handler(
    message: str,
    language: str | None,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> str:
    """Call App Runner ``POST /research`` and return the assistant reply text."""
    app_runner_url = (os.environ.get("APP_RUNNER_URL") or "").strip()
    if not app_runner_url:
        raise ValueError("APP_RUNNER_URL environment variable not set")

    if app_runner_url.startswith("https://"):
        app_runner_url = app_runner_url[8:]
    elif app_runner_url.startswith("http://"):
        app_runner_url = app_runner_url[7:]
    app_runner_url = app_runner_url.strip().rstrip("/")

    url = f"https://{app_runner_url}/research"
    payload: Dict[str, Any] = {
        "message": message,
        "language": language or "en",
    }
    if conversation_history:
        payload["conversation_history"] = conversation_history
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.error("Researcher HTTP %s: %s", e.code, err_body)
        raise RuntimeError(
            f"Research service returned HTTP {e.code}."
        ) from e
    except urllib.error.URLError as e:
        logger.exception("Could not reach research service: %s", e)
        raise RuntimeError("Could not reach research service") from e

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    if isinstance(payload, dict) and "reply" in payload:
        r = payload.get("reply")
        return r if isinstance(r, str) else (str(r) if r is not None else raw)
    return raw

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/user", response_model=UserResponse)
async def get_or_create_user(
    clerk_user_id: str = Depends(get_current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    """
    Return the ``users`` row for this Clerk subject, creating it on first sight.
    On every call, ``display_name`` and ``email`` are refreshed from the JWT so
    the database stays aligned with Clerk profile changes.
    """
    try:
        user, created = _resolve_user_row(clerk_user_id, creds)
        return UserResponse(user=user, created=created)
    except ClientError as e:
        missing = _schema_missing_response(e)
        if missing:
            logger.error(f"Database schema missing in get_or_create_user: {e}")
            raise missing
        logger.error(f"Error in get_or_create_user: {e}")
        raise HTTPException(status_code=500, detail="Failed to load user profile")
    except Exception as e:
        missing = _schema_missing_response(e)
        if missing:
            logger.error(f"Database schema missing in get_or_create_user: {e}")
            raise missing
        logger.error(f"Error in get_or_create_user: {e}")
        raise HTTPException(status_code=500, detail="Failed to load user profile")


@app.post("/api/activity")
async def log_product_activity(
    body: ActivityLogRequest,
    clerk_user_id: str = Depends(get_current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    """
    Persist a single activity row for analytics / journey / future subscription features.
    Trusts the authenticated Clerk user only (not a client-supplied user id).
    """
    try:
        user, _ = _resolve_user_row(clerk_user_id, creds)
        account_name = (user.get("display_name") or "User")[:255]
        email = user.get("email")
        new_id = db.activity_history.create_activity_history(
            clerk_user_id=clerk_user_id,
            account_name=account_name,
            email=email,
            details=body.details,
            label=body.label,
            activity_type=body.activity_type,
        )
        return {"ok": True, "id": str(new_id)}
    except ClientError as e:
        m = _schema_missing_response(e)
        if m:
            raise m
        logger.error("log_product_activity: %s", e)
        raise HTTPException(
            status_code=500, detail="Could not save activity. Is the database migration applied?"
        ) from e
    except Exception as e:
        logger.exception("log_product_activity: %s", e)
        raise HTTPException(
            status_code=500, detail="Could not save activity."
        ) from e


def _iso_ts(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


@app.get("/api/chats", response_model=list[LegalChatListItem])
async def list_legal_chats(
    clerk_user_id: str = Depends(get_current_user_id),
) -> list[LegalChatListItem]:
    """List legal chat sessions for the signed-in user (newest first)."""
    try:
        _ensure_user_row(clerk_user_id)
        rows = db.legal_chats.list_for_user(clerk_user_id, limit=100)
    except ClientError as e:
        m = _schema_missing_response(e)
        if m:
            raise m
        raise HTTPException(
            status_code=500, detail="Could not load chat list. Try again later."
        ) from e
    return [
        LegalChatListItem(
            id=str(r["id"]),
            title=(r.get("title") or "New chat"),
            language=(r.get("language") or "en"),
            updated_at=_iso_ts(r.get("updated_at")),
            created_at=_iso_ts(r.get("created_at")),
        )
        for r in rows
    ]


@app.post("/api/chats", response_model=LegalChatListItem)
async def create_legal_chat(
    body: CreateLegalChatRequest = CreateLegalChatRequest(),
    clerk_user_id: str = Depends(get_current_user_id),
) -> LegalChatListItem:
    """Create an empty chat row (or claim ``body.id`` if the row does not exist yet)."""
    try:
        _ensure_user_row(clerk_user_id)
        try:
            cid = str(uuid.UUID(body.id)) if body.id else str(uuid.uuid4())
        except ValueError as e:
            raise HTTPException(
                status_code=422, detail="Invalid id (expected UUID format)."
            ) from e
        owner = db.legal_chats.owner_clerk_id(cid)
        if owner and owner != clerk_user_id:
            raise HTTPException(status_code=403, detail="This chat id is already in use.")
        if not owner:
            db.legal_chats.ensure_for_user(
                clerk_user_id, cid, title="New chat", language="en"
            )
        row = db.legal_chats.find_for_user(clerk_user_id, cid)
        if not row:
            raise HTTPException(status_code=500, detail="Chat could not be created.")
    except HTTPException:
        raise
    except ClientError as e:
        m = _schema_missing_response(e)
        if m:
            raise m
        logger.error("create_legal_chat: %s", e)
        raise HTTPException(
            status_code=500, detail="Could not create chat. Is the DB migration applied?"
        ) from e
    return LegalChatListItem(
        id=str(row["id"]),
        title=row.get("title") or "New chat",
        language=row.get("language") or "en",
        updated_at=_iso_ts(row.get("updated_at")),
        created_at=_iso_ts(row.get("created_at")),
    )


@app.get("/api/chats/{chat_id}/messages", response_model=list[LegalChatMessageOut])
async def get_legal_chat_messages(
    chat_id: str,
    clerk_user_id: str = Depends(get_current_user_id),
) -> list[LegalChatMessageOut]:
    """Return messages for a chat the user owns."""
    try:
        uuid.UUID(chat_id)
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail="Invalid chat_id (expected UUID)."
        ) from e
    if not db.legal_chats.find_for_user(clerk_user_id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    try:
        msgs = db.legal_chat_messages.list_for_chat(chat_id)
    except ClientError as e:
        m = _schema_missing_response(e)
        if m:
            raise m
        raise
    return [
        LegalChatMessageOut(
            id=str(m["id"]),
            role=str(m.get("role") or "user"),
            content=str(m.get("content") or ""),
            language_code=str(m.get("language_code") or "en"),
            created_at=_iso_ts(m.get("created_at")),
        )
        for m in msgs
    ]


@app.post("/api/chat", response_model=LegalChatResponse)
async def legal_chat(
    body: LegalChatRequest,
    clerk_user_id: str = Depends(get_current_user_id),
) -> LegalChatResponse:
    """
    General legal Q&A: persists each turn to the database and forwards to the
    research service (with prior turns as ``conversation_history`` when present).
    """
    try:
        chat_uuid = uuid.UUID(body.chat_id)
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail="Invalid chat_id (expected UUID format)."
        ) from e
    cid = str(chat_uuid)
    try:
        _ensure_user_row(clerk_user_id)
        owner = db.legal_chats.owner_clerk_id(cid)
        if owner and owner != clerk_user_id:
            raise HTTPException(
                status_code=403, detail="This chat belongs to another account."
            )
        lang = (body.language or "en").strip() or "en"
        if not owner:
            db.legal_chats.ensure_for_user(
                clerk_user_id, cid, title="New chat", language=lang
            )

        prior_rows = db.legal_chat_messages.list_for_chat(cid)
        prior_for_llm: list[dict[str, str]] = [
            {"role": m["role"], "content": m["content"]}
            for m in prior_rows
            if m.get("role") in ("user", "assistant")
        ]
        db.legal_chat_messages.insert_message(cid, "user", body.message, lang)
        if len(prior_rows) == 0:
            db.legal_chats.update_title(cid, _short_chat_title(body.message))

        reply = research_handler(
            body.message, body.language, prior_for_llm
        )
        db.legal_chat_messages.insert_message(cid, "assistant", reply, lang)
        db.legal_chats.touch(cid)
        return LegalChatResponse(reply=reply)
    except HTTPException:
        raise
    except ClientError as e:
        m = _schema_missing_response(e)
        if m:
            raise m
        logger.error("legal chat DB: %s", e)
        raise HTTPException(
            status_code=500, detail="Could not save chat. Is the database migration applied?"
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("legal chat failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Chat completion failed. Try again later."
        ) from e


@app.put("/api/user")
async def update_user(user_update: UserUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """Update user settings"""

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user - users table uses clerk_user_id as primary key
        update_data = user_update.model_dump(exclude_unset=True)

        # Use the database client directly since users table has clerk_user_id as PK
        db.users.db.update(
            'users',
            update_data,
            "clerk_user_id = :clerk_user_id",
            {'clerk_user_id': clerk_user_id}
        )

        # Return updated user
        updated_user = db.users.find_by_clerk_id(clerk_user_id)
        return updated_user

    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/activity-history")
async def list_user_activity_history(
    clerk_user_id: str = Depends(get_current_user_id),
):
    """Product / journey event log for the signed-in user (``activity_history`` table)."""

    try:
        return db.activity_history.find_by_user(clerk_user_id)

    except Exception as e:
        logger.error("Error listing activity history: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/activity-history")
async def create_account_activity_history(
    activity: ActivityHistoryCreate,
    clerk_user_id: str = Depends(get_current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    """
    Legacy body shape for creating an activity row. The authenticated user is
    used; ``clerk_user_id`` in the JSON body is ignored (if present) for security.
    Prefer ``POST /api/activity`` for new clients.
    """
    try:
        user, _ = _resolve_user_row(clerk_user_id, creds)
        account_name = activity.account_name or user.get("display_name") or "User"
        email = activity.email or user.get("email")
        new_id = db.activity_history.create_activity_history(
            clerk_user_id=clerk_user_id,
            account_name=account_name,
            email=email,
            details=activity.details,
            label=activity.label,
            activity_type=activity.activity_type,
            activity_date=activity.activity_date,
        )
        return {"ok": True, "id": str(new_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating activity history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/contracts/analyze", response_model=ContractAnalysisResult)
async def analyze_contract_document(
    file: UploadFile = File(...),
    message: str = Form(default=""),
    language: str = Form(default="en"),
    clerk_user_id: str = Depends(get_current_user_id),
) -> ContractAnalysisResult:
    """
    Contract analysis (internal `contract_analyst` package). Only this API exposes the route.
    Requires OPENROUTER_API_KEY.
    """
    _ = clerk_user_id
    try:
        body = await file.read()
    except Exception as e:
        logger.error("contract upload read failed: %s", e)
        raise HTTPException(status_code=400, detail="Could not read uploaded file") from e

    if not body:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        return await analyze_contract_bytes(
            data=body,
            filename=file.filename or "document",
            user_message=message or None,
            language=language or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        detail = str(e)
        if "OPENROUTER_API_KEY" in detail:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Contract analysis is not configured (missing API key).",
            ) from e
        raise HTTPException(status_code=500, detail=detail) from e


@app.get("/api/rag/documents", response_model=RagDocumentListResponse)
async def list_rag_documents(
    clerk_user_id: str = Depends(get_current_user_id),
) -> RagDocumentListResponse:
    """
    List objects the current user uploaded under RAG_S3_KEY_PREFIX, with presigned download URLs.
    """
    if not RAG_DOCUMENTS_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG document storage is not configured (set RAG_DOCUMENTS_BUCKET).",
        )

    user_part = _rag_s3_user_part(clerk_user_id)
    prefix = f"{RAG_S3_KEY_PREFIX}/{user_part}/"
    region = os.getenv("DEFAULT_AWS_REGION", "eu-west-2")
    s3 = boto3.client("s3", region_name=region)

    items: list[RagDocumentListItem] = []
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=RAG_DOCUMENTS_BUCKET, Prefix=prefix):
            for obj in page.get("Contents") or ():
                key = obj.get("Key") or ""
                if not key or key.endswith("/"):
                    continue
                rel = key[len(prefix) :] if key.startswith(prefix) else ""
                segs = rel.split("/")
                if len(segs) < 2:
                    continue
                doc_id = segs[0]
                name = segs[-1] if segs else "document"
                if not name or ".." in name:
                    continue
                lm = obj.get("LastModified")
                last_m = lm.isoformat() if hasattr(lm, "isoformat") else None
                size_b = int(obj.get("Size") or 0)
                dl = _rag_download_presigned_url(s3, key, name)
                items.append(
                    RagDocumentListItem(
                        document_id=doc_id,
                        name=name,
                        s3_key=key,
                        size_bytes=size_b,
                        last_modified=last_m,
                        download_url=dl,
                    )
                )
    except ClientError as e:
        logger.exception("RAG S3 list_objects_v2 failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to list RAG documents. Check bucket policy and credentials.",
        ) from e

    # Newest first
    items.sort(
        key=lambda r: (r.last_modified or ""),
        reverse=True,
    )
    return RagDocumentListResponse(documents=items)


@app.post("/api/rag/documents/upload", response_model=RagDocumentUploadResponse)
async def upload_rag_document(
    file: UploadFile = File(...),
    clerk_user_id: str = Depends(get_current_user_id),
) -> RagDocumentUploadResponse:
    """
    Store an uploaded file in S3 for RAG / ingestion (configure RAG_DOCUMENTS_BUCKET).
    """
    if not RAG_DOCUMENTS_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG document storage is not configured (set RAG_DOCUMENTS_BUCKET).",
        )

    try:
        body = await file.read()
    except Exception as e:
        logger.error("rag document read failed: %s", e)
        raise HTTPException(status_code=400, detail="Could not read uploaded file") from e

    if not body:
        raise HTTPException(status_code=400, detail="Empty file")

    safe_name = _safe_client_filename(file.filename)
    doc_id = str(uuid.uuid4())
    user_part = _rag_s3_user_part(clerk_user_id)
    key = f"{RAG_S3_KEY_PREFIX}/{user_part}/{doc_id}/{safe_name}"
    region = os.getenv("DEFAULT_AWS_REGION", "eu-west-2")
    s3 = boto3.client("s3", region_name=region)
    content_type = file.content_type or "application/octet-stream"

    try:
        s3.put_object(
            Bucket=RAG_DOCUMENTS_BUCKET,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
    except ClientError as e:
        logger.exception("RAG S3 put_object failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to store document in S3. Check bucket policy and credentials."
        ) from e

    download_url = _rag_download_presigned_url(s3, key, safe_name)

    ingestion_queued = False
    sqs_message_id: Optional[str] = None
    queue_url = RAG_INGESTION_QUEUE_URL or SQS_QUEUE_URL
    if queue_url:
        payload = {
            "version": 1,
            "type": "rag_document_ingest",
            "document_id": doc_id,
            "s3_key": key,
            "bucket": RAG_DOCUMENTS_BUCKET,
            "clerk_user_id": clerk_user_id,
            "content_type": content_type,
            "original_filename": safe_name,
        }
        try:
            qclient = _sqs_client_for_queue(queue_url)
            sm = qclient.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(payload),
            )
            ingestion_queued = True
            sqs_message_id = sm.get("MessageId")
            logger.info(
                "rag ingest queued doc_id=%s message_id=%s", doc_id, sqs_message_id
            )
        except Exception as e:
            logger.exception(
                "RAG SQS send failed; document is in S3 but not queued: %s", e
            )
    else:
        logger.warning(
            "RAG_INGESTION_QUEUE_URL and SQS_QUEUE_URL are unset; skipping ingest queue (S3 only)."
        )

    return RagDocumentUploadResponse(
        document_id=doc_id,
        s3_key=key,
        bucket=RAG_DOCUMENTS_BUCKET,
        size_bytes=len(body),
        content_type=file.content_type,
        ingestion_queued=ingestion_queued,
        sqs_message_id=sqs_message_id,
        download_url=download_url,
    )


@app.get("/api/accounts/{account_id}/positions")
async def list_account_positions(
    account_id: str,
    clerk_user_id: str = Depends(get_current_user_id),
):
    """
    List portfolio positions for a brokerage account, with instrument metadata.
    Not related to ``activity_history`` (user event log) — use ``GET /api/activity-history`` for that.
    """
    try:
        account = db.accounts.find_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        if account.get("clerk_user_id") != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        positions = db.positions.find_by_account(account_id)

        formatted_positions = []
        for pos in positions:
            instrument = db.instruments.find_by_symbol(pos["symbol"])
            formatted_positions.append({**pos, "instrument": instrument})

        return {"positions": formatted_positions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing account positions: %s", e)
        raise HTTPException(status_code=500, detail=str(e))



# Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)