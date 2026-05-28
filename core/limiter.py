from __future__ import annotations

from typing import Callable, Optional, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.settings import settings

RATE_LIMITS = {
    "auth": "500/minute",
    "chat": "2000/minute",
    "search": "6000/minute",
    "upload": "500/minute",
    "default": "10000/minute",
}

ROUTE_GROUPS = {
    "auth": ["/auth"],
    "chat": ["/conversation", "/chat"],
    "search": ["/discover", "/search"],
    "upload": ["/upload"],
}

def uid_then_ip_key(request: Request) -> str:
    """ Ưu tiên dùng user ID nếu có, nếu không có thì dùng IP để giới hạn tốc độ."""
    user = getattr(request.state, "user", None)

    if user:
        uid = getattr(user, "id", None)
        if not uid and isinstance(user, dict):
            uid = user.get("uid") or user.get("id")

        if uid:
            return f"user:{uid}"

    ip = get_remote_address(request) or "unknown"
    return f"ip:{ip}"


limiter = Limiter(
    key_func=uid_then_ip_key,
)


def match_limit(path: str) -> str:
    for group, prefixes in ROUTE_GROUPS.items():
        for prefix in prefixes:
            if path == prefix or path.startswith(f"{prefix}/"):
                return RATE_LIMITS[group]

    return RATE_LIMITS["default"]


_LIMIT_HANDLER_CACHE: Dict[str, Callable] = {}


def get_limited_handler(limit: str):
    if limit in _LIMIT_HANDLER_CACHE:
        return _LIMIT_HANDLER_CACHE[limit]

    async def _handler(request: Request, call_next: Callable):
        return await call_next(request)

    wrapped = limiter.limit(limit)(_handler)
    _LIMIT_HANDLER_CACHE[limit] = wrapped
    return wrapped

class AutoRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limit = match_limit(request.url.path)

        try:
            handler = get_limited_handler(limit)

            return await handler(request, call_next)

        except RateLimitExceeded:
            return JSONResponse(
                status_code=429,
                content={
                    "status_code": 429,
                    "message": "Rate limit exceeded",
                    "data": None,
                },
            )