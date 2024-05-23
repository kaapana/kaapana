from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "no-referrer"

        # Strict-Transport-Security
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        return response
