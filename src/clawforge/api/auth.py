"""API Key authentication middleware."""

import hmac
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header on all requests except health check."""

    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key.encode() if api_key else b""

    async def dispatch(self, request: Request, call_next):
        if not self.api_key:
            return await call_next(request)

        # Skip auth for health check
        if request.url.path == "/v1/health":
            return await call_next(request)

        auth_header = request.headers.get("X-API-Key", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header")

        if not hmac.compare_digest(auth_header.encode(), self.api_key):
            raise HTTPException(status_code=403, detail="Invalid API key")

        return await call_next(request)
