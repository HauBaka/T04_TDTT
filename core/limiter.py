from __future__ import annotations

from typing import Callable, Optional, Dict
import inspect

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


RATE_LIMITS = {
    "auth": "5/minute",
    "chat": "20/minute",
    "search": "60/minute",
    "upload": "5/minute",
    "default": "100/minute"
}

ROUTE_GROUPS = {
    "auth": ["/auth"],
    "chat": ["/conversation", "/chat"],
    "search": ["/discover", "/search"],
    "upload": ["/upload"],
    "default": ["/"]
}

def uid_then_ip_key(request: Request) -> str:
    """ Ưu tiên dùng user ID nếu có, nếu không có thì dùng IP để giới hạn tốc độ."""
    user = getattr(request.state, "user", None)

    if user:
        uid = getattr(user, "id", None)
        if not uid and isinstance(user, dict):
            uid = user.get("id")

        if uid:
            return f"user:{uid}"

    return f"ip:{get_remote_address(request) or 'unknown'}"


limiter = Limiter(key_func=uid_then_ip_key)


def match_limit(path: str, method: str) -> Optional[str]:
    for group, prefixes in ROUTE_GROUPS.items():
        if any(path.startswith(prefix) for prefix in prefixes):
            return RATE_LIMITS.get(group)

    return None


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
    async def dispatch(self, request, call_next):
        limit = match_limit(request.url.path, request.method)

        if not limit:
            return await call_next(request)

        handler = get_limited_handler(limit)

        try:
            result = handler(request, call_next)

            if inspect.isawaitable(result):
                return await result
            return result

        except RateLimitExceeded:
            return JSONResponse(
            status_code=429,
            content={
                "status_code": 429,
                "message": "Rate limit exceeded",
                "data": None
            })