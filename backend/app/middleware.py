"""Middleware that decodes the bearer JWT (when present) and stashes the
user_id on `request.state.user_id`.

This runs BEFORE route handlers and BEFORE slowapi's @limiter.limit check, so
slowapi can key rate limits per-user. It does NOT enforce auth — the route's
`Depends(get_current_user)` still does that. This middleware is best-effort:
malformed/expired tokens are silently ignored so the route's normal 401 path
takes over.
"""
import logging

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.config import get_settings

log = logging.getLogger(__name__)


class JWTContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            try:
                payload = jwt.decode(
                    token,
                    self._settings.jwt_secret,
                    algorithms=[self._settings.jwt_algorithm],
                )
                sub = payload.get("sub")
                if sub:
                    request.state.user_id = int(sub)
            except (JWTError, ValueError):
                # Bad token; ignore — Depends(get_current_user) will 401 it.
                pass
        return await call_next(request)
