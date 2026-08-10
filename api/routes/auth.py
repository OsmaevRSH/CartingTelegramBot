"""Mobile pairing and session lifecycle endpoints."""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from core.auth.tokens import issue_access_token
from core.config.config import ACCESS_TOKEN_TTL_SECONDS
from core.database.db import (
    consume_pairing_code,
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)

router = APIRouter(prefix="/mobile/auth")


class PairingCodeRequest(BaseModel):
    code: str = Field(min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=24, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_TTL_SECONDS


def _tokens(user_id: int, refresh_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=issue_access_token(user_id),
        refresh_token=refresh_token,
    )


@router.post("/exchange", response_model=TokenResponse)
async def exchange_pairing_code(request: PairingCodeRequest) -> TokenResponse:
    user_id = consume_pairing_code(request.code)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истёкший код",
        )
    return _tokens(user_id, create_refresh_session(user_id))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(request: RefreshTokenRequest) -> TokenResponse:
    rotated = rotate_refresh_session(request.refresh_token)
    if rotated is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительная сессия",
        )
    user_id, replacement_token = rotated
    return _tokens(user_id, replacement_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: RefreshTokenRequest) -> Response:
    if not revoke_refresh_session(request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительная сессия",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
