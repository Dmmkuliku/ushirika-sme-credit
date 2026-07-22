"""Shared SlowAPI limiter (enabled in production only)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    enabled=_settings.rate_limit_enabled and _settings.app_env == "production",
    headers_enabled=True,
)
