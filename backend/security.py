"""
security.py – Production-grade security middleware and utilities for TorobGard.

Features:
- Security HTTP response headers (HSTS, CSP, nosniff, DENY, etc.)
- In-memory thread-safe rate limiter (token bucket / sliding window per client IP)
- Safe static file path resolution (directory traversal prevention)
- Input sanitization helpers
"""

import os
import time
import threading
from typing import Dict, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ─── 1. Rate Limiting ──────────────────────────────────────────

class RateLimiter:
    """
    Sliding-window rate limiter per client IP.
    Thread-safe with periodic garbage collection of expired IP buckets.
    """
    def __init__(self, chat_limit: int = 40, api_limit: int = 150, window_s: int = 60):
        self.chat_limit = chat_limit
        self.api_limit = api_limit
        self.window_s = window_s
        self._lock = threading.Lock()
        # Map: (ip, route_type) -> list of timestamps
        self._requests: Dict[Tuple[str, str], list] = {}
        self._last_gc = time.time()

    def _get_client_ip(self, request: Request) -> str:
        # Check X-Forwarded-For if behind reverse proxy / Liara
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    def is_allowed(self, request: Request) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        Returns: (is_allowed: bool, retry_after: int)
        """
        path = request.url.path
        if not path.startswith("/api/"):
            return True, 0

        # Health endpoint is exempt
        if path == "/api/health":
            return True, 0

        route_type = "chat" if path.startswith("/api/chat") else "api"
        max_requests = self.chat_limit if route_type == "chat" else self.api_limit

        ip = self._get_client_ip(request)
        key = (ip, route_type)
        now = time.time()

        with self._lock:
            # Periodic cleanup every 2 minutes
            if now - self._last_gc > 120:
                self._gc(now)

            timestamps = self._requests.get(key, [])
            cutoff = now - self.window_s
            # Filter timestamps within current window
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_requests:
                earliest = valid_timestamps[0]
                retry_after = max(1, int(self.window_s - (now - earliest)))
                return False, retry_after

            valid_timestamps.append(now)
            self._requests[key] = valid_timestamps
            return True, 0

    def _gc(self, now: float):
        cutoff = now - self.window_s
        to_del = []
        for k, v in self._requests.items():
            fresh = [t for t in v if t > cutoff]
            if fresh:
                self._requests[k] = fresh
            else:
                to_del.append(k)
        for k in to_del:
            del self._requests[k]
        self._last_gc = now


# ─── 2. Security Middleware ────────────────────────────────────

rate_limiter = RateLimiter(chat_limit=45, api_limit=180, window_s=60)


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Rate Limiting Check
        allowed, retry_after = rate_limiter.is_allowed(request)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً چند لحظه صبر کنید.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # 2. Call next handler
        response: Response = await call_next(request)

        # 3. Add OWASP Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"

        # Content Security Policy (Allows necessary assets while preventing XSS/Clickjacking)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: blob: https://image.torob.com https://api.neshan.org https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://unpkg.com",
            "connect-src 'self' https://*.basemaps.cartocdn.com https://api.openai.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response


# ─── 3. Safe Path Resolution (Directory Traversal Protection) ─

def resolve_safe_static_path(base_dir: str, requested_subpath: str) -> str | None:
    """
    Safely resolves a static file path, ensuring it stays strictly inside base_dir.
    Returns the absolute path if safe and exists, or None.
    """
    base_abs = os.path.abspath(base_dir)
    # Strip any leading slashes or backslashes
    clean_subpath = requested_subpath.lstrip("/\\")
    target_abs = os.path.abspath(os.path.join(base_abs, clean_subpath))

    try:
        # Check if base_abs is a common prefix for target_abs
        if os.path.commonpath([base_abs, target_abs]) == base_abs:
            if os.path.isfile(target_abs):
                return target_abs
    except (ValueError, OSError):
        # On Windows, comparing paths on different drives raises ValueError
        return None

    return None
