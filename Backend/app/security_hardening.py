"""Production security helpers: headers and secret checks."""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings
from app.limiter import limiter

_WEAK_SECRETS = {
    "dev-secret-key-change-in-production",
    "dev-pseudonymization-key-change-in-production",
    "change-me",
    "secret",
    "changeme",
}


def assert_secure_settings(settings: Settings) -> None:
    """Refuse to start production with debug mode or placeholder secrets."""
    if settings.app_env != "production":
        return
    if settings.debug:
        raise RuntimeError("DEBUG must be false when APP_ENV=production")
    if not settings.secret_key or settings.secret_key.strip().lower() in _WEAK_SECRETS:
        raise RuntimeError("SECRET_KEY must be set to a strong value in production")
    if (
        not settings.pseudonymization_key
        or settings.pseudonymization_key.strip().lower() in _WEAK_SECRETS
    ):
        raise RuntimeError("PSEUDONYMIZATION_KEY must be set to a strong value in production")
    if len(settings.secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, production: bool = False):
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("X-XSS-Protection", "0")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        if self.production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


def attach_security(application: FastAPI, settings: Settings) -> None:
    assert_secure_settings(settings)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(
        SecurityHeadersMiddleware,
        production=settings.app_env == "production",
    )
