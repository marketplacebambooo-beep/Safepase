import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter for auth and USSD endpoints."""

    def __init__(self, app):
        super().__init__(app)
        self.hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_limited_path(self, path: str) -> bool:
        return path.startswith("/api/auth/login") or path.startswith("/ussd/")

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled or not self._is_limited_path(request.url.path):
            return await call_next(request)

        key = f"{self._client_key(request)}:{request.url.path}"
        now = time.time()
        window = settings.rate_limit_window_seconds
        limit = settings.rate_limit_max_requests

        self.hits[key] = [t for t in self.hits[key] if now - t < window]
        if len(self.hits[key]) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )
        self.hits[key].append(now)
        return await call_next(request)
