"""Issue and validate short-lived mobile access tokens."""

from datetime import datetime, timedelta, timezone

import jwt

from core.config.config import ACCESS_TOKEN_TTL_SECONDS, AUTH_SECRET


def issue_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS),
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
