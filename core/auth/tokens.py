"""Issue and validate short-lived mobile and Telegram Login tokens."""

import hashlib
import hmac
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from time import monotonic
from typing import Mapping, Optional

import jwt
from jwt import PyJWKClient

from core.config.config import (
    AUTH_SECRET,
    TELEGRAM_LOGIN_CLIENT_ID,
    TELEGRAM_LOGIN_JWKS_TIMEOUT_SECONDS,
    TELEGRAM_LOGIN_JWKS_URL,
)

ACCESS_TOKEN_LIFETIME_SECONDS = 900
TELEGRAM_AUTH_MAX_AGE_SECONDS = 10 * 60
TELEGRAM_AUTH_FUTURE_TOLERANCE_SECONDS = 60
_TELEGRAM_HASH_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
_TELEGRAM_ISSUER = "https://oauth.telegram.org"
_TELEGRAM_JWKS_CACHE_SECONDS = 300
_TELEGRAM_JWKS_MAX_KEYS = 16
_TELEGRAM_UNKNOWN_KID_CACHE_SECONDS = 60
_TELEGRAM_UNKNOWN_KID_CACHE_SIZE = 64
_TELEGRAM_PROFILE_FIELD_MAX_LENGTH = 256
_TELEGRAM_NO_MATCHING_KEY_ERROR = "Unable to find a signing key that matches:"
_TELEGRAM_JWK_CLIENT_LOCK = RLock()
_telegram_jwk_client: Optional[PyJWKClient] = None
_telegram_unknown_kids: OrderedDict[str, float] = OrderedDict()


@dataclass(frozen=True)
class TelegramIdentity:
    """Validated Telegram identity, without the source ID token."""

    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

    @property
    def telegram_name(self) -> Optional[str]:
        name = " ".join(
            part for part in (self.first_name, self.last_name) if part
        )
        return name or None


def get_telegram_jwk_client() -> PyJWKClient:
    """Return a bounded cached Telegram JWKS client."""
    global _telegram_jwk_client
    with _TELEGRAM_JWK_CLIENT_LOCK:
        if _telegram_jwk_client is None:
            _telegram_jwk_client = PyJWKClient(
                TELEGRAM_LOGIN_JWKS_URL,
                cache_keys=True,
                max_cached_keys=_TELEGRAM_JWKS_MAX_KEYS,
                cache_jwk_set=True,
                lifespan=_TELEGRAM_JWKS_CACHE_SECONDS,
                timeout=TELEGRAM_LOGIN_JWKS_TIMEOUT_SECONDS,
            )
        return _telegram_jwk_client


def _safe_profile_claim(claims: Mapping[str, object], key: str) -> Optional[str]:
    value = claims.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > _TELEGRAM_PROFILE_FIELD_MAX_LENGTH:
        return None
    return value


def _telegram_user_id(claims: Mapping[str, object]) -> int:
    value = claims.get("id")
    if isinstance(value, bool):
        raise ValueError("Invalid Telegram user ID")
    if isinstance(value, int):
        user_id = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        user_id = int(value)
    else:
        raise ValueError("Invalid Telegram user ID")
    if user_id <= 0 or user_id > 2**63 - 1:
        raise ValueError("Invalid Telegram user ID")
    if claims.get("sub") != str(user_id):
        raise ValueError("Telegram subject does not match ID")
    return user_id


def _telegram_key_id(id_token: str) -> str:
    kid = jwt.get_unverified_header(id_token).get("kid")
    if not isinstance(kid, str) or not kid or len(kid) > 128:
        raise ValueError("Invalid Telegram key ID")
    return kid


def _is_recent_unknown_telegram_key(kid: str, now: float) -> bool:
    while _telegram_unknown_kids:
        oldest_kid, expires_at = next(iter(_telegram_unknown_kids.items()))
        if expires_at > now:
            break
        _telegram_unknown_kids.pop(oldest_kid)
    expires_at = _telegram_unknown_kids.get(kid)
    if expires_at is None or expires_at <= now:
        return False
    _telegram_unknown_kids.move_to_end(kid)
    return True


def _remember_unknown_telegram_key(kid: str, now: float) -> None:
    _telegram_unknown_kids[kid] = now + _TELEGRAM_UNKNOWN_KID_CACHE_SECONDS
    _telegram_unknown_kids.move_to_end(kid)
    while len(_telegram_unknown_kids) > _TELEGRAM_UNKNOWN_KID_CACHE_SIZE:
        _telegram_unknown_kids.popitem(last=False)


def _is_definitive_unknown_telegram_key(error: jwt.PyJWKClientError) -> bool:
    return (
        type(error) is jwt.PyJWKClientError
        and str(error).startswith(_TELEGRAM_NO_MATCHING_KEY_ERROR)
    )


def validate_telegram_id_token(id_token: str) -> TelegramIdentity:
    """Validate a Telegram native ID token and return only safe identity data."""
    if (
        not TELEGRAM_LOGIN_CLIENT_ID
        or not isinstance(id_token, str)
        or not id_token
        or len(id_token) > 16 * 1024
    ):
        raise ValueError("Invalid Telegram ID token")
    try:
        kid = _telegram_key_id(id_token)
        with _TELEGRAM_JWK_CLIENT_LOCK:
            now = monotonic()
            if _is_recent_unknown_telegram_key(kid, now):
                raise ValueError("Unknown Telegram key")
            try:
                signing_key = get_telegram_jwk_client().get_signing_key_from_jwt(
                    id_token
                )
            except jwt.PyJWKClientError as error:
                if _is_definitive_unknown_telegram_key(error):
                    _remember_unknown_telegram_key(kid, now)
                raise
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=TELEGRAM_LOGIN_CLIENT_ID,
            issuer=_TELEGRAM_ISSUER,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        user_id = _telegram_user_id(claims)
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, OSError) as exc:
        raise ValueError("Invalid Telegram ID token") from exc
    return TelegramIdentity(
        user_id=user_id,
        first_name=_safe_profile_claim(claims, "first_name"),
        last_name=_safe_profile_claim(claims, "last_name"),
        username=_safe_profile_claim(claims, "username"),
        photo_url=_safe_profile_claim(claims, "photo_url"),
    )


def validate_telegram_login_payload(
    payload: Mapping[str, str],
    bot_token: str,
    now: Optional[datetime] = None,
) -> int:
    """Validate a Telegram Login payload and return its numeric user ID."""
    if not bot_token:
        raise ValueError("Telegram Login is not configured")

    provided_hash = payload.get("hash", "")
    if not _TELEGRAM_HASH_RE.fullmatch(provided_hash):
        raise ValueError("Invalid Telegram Login signature")
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
