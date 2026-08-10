"""FastAPI dependencies shared by mobile routes."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def require_mobile_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        return decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
