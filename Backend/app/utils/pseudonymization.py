import hashlib
import hmac
import secrets

from app.config import get_settings


def pseudonymize(value: str, field: str = "default") -> str:
    """
    Stable HMAC-SHA256 pseudonymization for modelling / linkage keys.

    Ethical policy (proposal §3.11): personally identifiable fields are never
    passed into the ML feature matrix. Counterparty linkage uses hashed tokens
    (`counterparty_hash`); lenders see opaque `display_token` values only.
    """
    settings = get_settings()
    normalized = value.strip().lower()
    message = f"{field}:{normalized}".encode("utf-8")
    key = settings.pseudonymization_key.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def strip_pii_from_record(record: dict) -> dict:
    """Drop common PII keys before any modelling / analytics export."""
    blocked = {
        "nida",
        "full_name",
        "phone",
        "email",
        "tin",
        "work_email",
        "counterparty_name",
        "counterparty_tin",
        "login_id",
        "membership_number",
    }
    return {k: v for k, v in record.items() if str(k).lower() not in blocked}


def generate_display_token() -> str:
    """Short opaque token for lender-facing SME identification."""
    return secrets.token_hex(8)
