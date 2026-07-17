import hashlib
import hmac
import secrets

from app.config import get_settings


def pseudonymize(value: str, field: str = "default") -> str:
    """Stable HMAC-SHA256 pseudonymization; raw PII is never persisted."""
    settings = get_settings()
    normalized = value.strip().lower()
    message = f"{field}:{normalized}".encode("utf-8")
    key = settings.pseudonymization_key.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def generate_display_token() -> str:
    """Short opaque token for lender-facing SME identification."""
    return secrets.token_hex(8)
