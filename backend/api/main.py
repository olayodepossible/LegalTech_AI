"""
FastAPI backend for FinPlex Financial Advisor
Handles all API routes with Clerk JWT authentication
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
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

from openai import AsyncOpenAI

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
    message: str = Field(..., min_length=1, max_length=12000)
    language: str | None = "en"


class LegalChatResponse(BaseModel):
    reply: str


class RagDocumentUploadResponse(BaseModel):
    document_id: str
    s3_key: str
    bucket: str
    size_bytes: int
    content_type: Optional[str] = None
    ingestion_queued: bool = False
    sqs_message_id: Optional[str] = None


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


# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/user", response_model=UserResponse)
async def get_or_create_user(
    clerk_user_id: str = Depends(get_current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard)
):
    """Get user or create if first time"""

    try:
        # Check if user exists
        user = db.users.find_by_clerk_id(clerk_user_id)

        if user:
            return UserResponse(user=user, created=False)

        # Create new user with defaults from JWT token
        token_data = creds.decoded
        email = token_data.get('email', "no-email@example.com")
        display_name = token_data.get('name') or token_data.get('email', '').split('@')[0] or "New User"

            
            
        # Create user with ALL defaults in one operation
        user_data = {
            'clerk_user_id': clerk_user_id,
            'display_name': display_name,
            'email': email
        }

        db.users.create(user_data, returning="clerk_user_id")

        created_user = db.users.find_by_clerk_id(clerk_user_id)
        logger.info(f"Created new user: {clerk_user_id}")

        return UserResponse(user=created_user, created=True)

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

@app.post("/api/chat", response_model=LegalChatResponse)
async def legal_chat(
    body: LegalChatRequest,
    clerk_user_id: str = Depends(get_current_user_id),
) -> LegalChatResponse:
    """
    General legal Q&A (OpenAI). For structured contract review use RAG and web search.
    """
    _ = clerk_user_id
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat is not configured (OPENAI_API_KEY).",
        )
    try:
        client = AsyncOpenAI(api_key=key, base_url=base_url)
        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        lang = body.language or "en"
        system = (
            "You are a helpful legal information assistant. "
            "You are not a lawyer; provide general information and suggest consulting a qualified professional for specific matters. "
            f"User language preference (ISO-ish code): {lang}."
        )
        r = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": body.message},
            ],
        )
        text = (r.choices[0].message.content or "").strip() or "…"
        return LegalChatResponse(reply=text)
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
async def list_account_activity_histories(clerk_user_id: str = Depends(get_current_user_id)):
    """List user's activity history"""

    try:
        # Get accounts for user
        activity_histories = db.activity_history.find_by_user(clerk_user_id)
        return activity_histories

    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/activity-history")
async def create_account_activity_history(activity: ActivityHistoryCreate, clerk_user_id: str = Depends(get_current_user_id)):
    """Create new account activity history"""

    try:
        # Verify user exists
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create account
        account_id = db.activity_history.create_activity_history(
            clerk_user_id=clerk_user_id,
            account_name=activity.account_name,
            email=activity.email,
            details=activity.details,
            label=activity.label,
            activity_type=activity.activity_type,
            activity_date=activity.activity_date
        )

        # Return created account
        created_account = db.accounts.find_by_id(account_id)
        return created_account

    except Exception as e:
        logger.error(f"Error creating account: {e}")
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
    user_part = re.sub(r"[^a-zA-Z0-9._@+-]+", "_", clerk_user_id)[:128]
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
    )


@app.get("/api/activity-history/{account_id}")
async def list_positions(account_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get activity history for account"""

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Verify ownership - accounts table stores clerk_user_id directly
        if account.get('clerk_user_id') != clerk_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        positions = db.positions.find_by_account(account_id)

        # Format positions with instrument data for frontend
        formatted_positions = []
        for pos in positions:
            # Get full instrument data
            instrument = db.instruments.find_by_symbol(pos['symbol'])
            formatted_positions.append({
                **pos,
                'instrument': instrument
            })

        return {"positions": formatted_positions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)