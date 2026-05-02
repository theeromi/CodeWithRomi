"""VaultAI — usage limits + concurrency control.

Adapted from vaultai-fastapi-limits.py (the standalone snippet) to match the
project's sync-SQLAlchemy + Depends-based-auth conventions:

- DB helpers take a `Session` (sync), not an async driver.
- `request.state.user_id` is populated by JWTContextMiddleware (see middleware.py)
  before slowapi reads it, so per-user keying works without changing route signatures.
- Concurrency caps are imported by the routes that actually call Ollama.

Tune LIMITS / SEMAPHORE_SIZE per your hardware reality.
"""
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Document


# ─── Per-user keying for rate limits ─────────────────────────────────────────
# slowapi keys rate limits by a function. We key by the authenticated user_id
# (set on request.state.user_id by JWTContextMiddleware), falling back to the
# real client IP for unauthenticated routes (login/register).

def user_or_ip(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{_real_ip(request)}"


def _real_ip(request: Request) -> str:
    """Cloudflare puts the user's true IP in `Cf-Connecting-Ip`. The socket peer
    is just a CF edge IP so per-IP limits would aggregate everyone together."""
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=user_or_ip, default_limits=["200/hour"])


# ─── Hardware-bound concurrency limits ───────────────────────────────────────
# One eGPU = one big inference at a time, full stop. Embeddings are cheaper but
# still GPU-bound, so we cap them too. Adjust if you ever go multi-GPU.

generation_semaphore = asyncio.Semaphore(1)   # 1 chat generation at a time
embedding_semaphore = asyncio.Semaphore(2)    # 2 concurrent embedding requests


# ─── Per-user account-level quotas ───────────────────────────────────────────
# Policy limits checked before any work happens. Wired against the real DB
# via the project's sync Session.

MAX_DOCUMENTS_PER_USER = 5
MAX_STORAGE_BYTES = 50 * 1024 * 1024     # 50 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_MESSAGES_PER_DAY = 50                # enforced as @limiter.limit("50/day")


def assert_under_document_quota(db: Session, user_id: int) -> None:
    count = db.query(func.count(Document.id)).filter(Document.user_id == user_id).scalar() or 0
    if count >= MAX_DOCUMENTS_PER_USER:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "document_quota_exceeded",
                "limit": MAX_DOCUMENTS_PER_USER,
                "current": count,
                "message": (
                    f"Beta limit: {MAX_DOCUMENTS_PER_USER} documents per account. "
                    "Delete one to upload another, or email hello@codewithromi.com to discuss raising the cap."
                ),
            },
        )


def assert_file_under_size(incoming_bytes: int) -> None:
    if incoming_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "file_too_large",
                "limit_bytes": MAX_FILE_SIZE_BYTES,
                "received_bytes": incoming_bytes,
                "message": f"Beta limit: files must be ≤ {MAX_FILE_SIZE_BYTES // (1024*1024)} MB.",
            },
        )


def assert_under_storage_quota(db: Session, user_id: int, incoming_bytes: int) -> None:
    used = db.query(func.coalesce(func.sum(Document.size_bytes), 0)).filter(
        Document.user_id == user_id
    ).scalar() or 0
    if used + incoming_bytes > MAX_STORAGE_BYTES:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "storage_quota_exceeded",
                "limit_bytes": MAX_STORAGE_BYTES,
                "used_bytes": used,
                "would_be_bytes": used + incoming_bytes,
                "message": (
                    f"Beta limit: {MAX_STORAGE_BYTES // (1024*1024)} MB total per account. "
                    "Delete some documents to free space."
                ),
            },
        )


# ─── Application setup ───────────────────────────────────────────────────────

def attach_limits(app: FastAPI) -> None:
    """Wire slowapi into the FastAPI app. Call once during startup."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _friendly_rate_limit_handler)


def _friendly_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Replace slowapi's default 429 with a clearer JSON shape the SPA can render."""
    detail = (
        "You're going faster than the beta plan allows. "
        "Try again in a few minutes, or email hello@codewithromi.com to discuss raising your cap."
    )
    retry_after = "60"  # generic; per-route Retry-After would be nicer but slowapi doesn't expose it cleanly
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limited", "detail": detail, "limit": str(exc.detail)},
        headers={"Retry-After": retry_after},
    )
