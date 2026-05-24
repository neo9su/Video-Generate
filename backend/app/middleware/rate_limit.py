"""Rate limiting middleware for FastAPI."""
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter middleware.

    Uses a sliding window counter per user/IP. Can be replaced with
    Redis-based implementation for production use.
    """

    def __init__(
        self,
        app: Callable,
        default_limit: int = 60,
        window_seconds: int = 60,
        whitelist_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.whitelist_paths = whitelist_paths or ["/api/v1/health", "/docs", "/openapi.json"]
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for whitelisted paths
        for path in self.whitelist_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        # Use user ID from auth header if available, else IP
        client_id = self._get_client_id(request)

        # Check rate limit
        if not self._check_rate_limit(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.default_limit),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        window_count = self._get_window_count(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.default_limit - window_count)
        )

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Try to use user ID from auth
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        client_host = request.client.host if request.client else "unknown"
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        return f"ip:{client_host}"

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if the client is within the rate limit."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]

        # Check limit
        if len(self._requests[client_id]) >= self.default_limit:
            return False

        # Record this request
        self._requests[client_id].append(now)
        return True

    def _get_window_count(self, client_id: str) -> int:
        """Get the current request count in the sliding window."""
        now = time.time()
        window_start = now - self.window_seconds
        return sum(1 for t in self._requests[client_id] if t > window_start)
