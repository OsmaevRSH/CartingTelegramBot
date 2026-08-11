"""Issue and validate short-lived mobile and Telegram Login tokens."""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Mapping, Optional

import jwt

from core.config.config import AUTH_SECRET

ACCESS_TOKEN_LIFETIME_SECONDS = 900
TELEGRAM_AUTH_MAX_AGE_SECONDS = 10 * 60
TELEGRAM_AUTH_FUTURE_TOLERANCE_SECONDS = 60


def validate_telegram_login_payload(
    payload: Mapping[str, str],
    bot_token: str,
    now: Optional[datetime] = None,
) -> int:
    """Validate a Telegram Login payload and return its numeric user ID."""
    if not bot_token:
        raise ValueError("Telegram Login is not configured")

    provided_hash = payload.get("hash", "")
    signed_fields = {
        key: value for key, value in payload.items() if key != "hash"
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(signed_fields.items())
    )
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(
        secret, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(provided_hash, expected_hash):
        raise ValueError("Invalid Telegram Login signature")

    telegram_id_text = payload.get("id", "")
    auth_date_text = payload.get("auth_date", "")
    if not telegram_id_text.isascii() or not telegram_id_text.isdecimal():
        raise ValueError("Invalid Telegram user ID")
    if not auth_date_text.isascii() or not auth_date_text.isdecimal():
        raise ValueError("Invalid Telegram auth date")

    telegram_id = int(telegram_id_text)
    auth_timestamp = int(auth_date_text)
    if telegram_id <= 0 or telegram_id > 2**63 - 1:
        raise ValueError("Invalid Telegram user ID")

    current_time = now or datetime.now(timezone.utc)
    current_timestamp = int(current_time.timestamp())
    if auth_timestamp < current_timestamp - TELEGRAM_AUTH_MAX_AGE_SECONDS:
        raise ValueError("Stale Telegram Login payload")
    if auth_timestamp > current_timestamp + TELEGRAM_AUTH_FUTURE_TOLERANCE_SECONDS:
        raise ValueError("Future Telegram Login payload")
    return telegram_id


def issue_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=ACCESS_TOKEN_LIFETIME_SECONDS),
        },
        AUTH_SECRET,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, AUTH_SECRET, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("unexpected token type")
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("missing subject")
    try:
        return int(subject)
    except ValueError as exc:
        raise jwt.InvalidTokenError("invalid subject") from exc
