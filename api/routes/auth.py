"""Mobile Telegram Login and session lifecycle endpoints."""

import html
import re
import secrets
import sqlite3
from typing import Dict
from urllib.parse import parse_qsl, urlencode, urlsplit

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from core.auth.tokens import (
    ACCESS_TOKEN_LIFETIME_SECONDS,
    issue_access_token,
    validate_telegram_id_token,
    validate_telegram_login_payload,
)
from core.config.config import (
    BOT_TOKEN,
    TELEGRAM_LOGIN_BOT_USERNAME,
    TELEGRAM_LOGIN_ORIGIN,
)
from core.database.db import (
    LOGIN_TRANSACTION_TTL_SECONDS,
    complete_telegram_login_and_issue_authorization_code,
    consume_telegram_authorization_code_and_create_refresh_session,
    create_telegram_login_transaction,
    find_telegram_login_transaction,
    provision_telegram_identity_and_create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)

router = APIRouter(prefix="/mobile/auth")


class TelegramStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code_challenge: str
    code_challenge_method: str


class TelegramStartResponse(BaseModel):
    authorization_url: str
    state: str
    expires_in: int = LOGIN_TRANSACTION_TTL_SECONDS


class TelegramExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    state: str
    code_verifier: str


class TelegramNativeExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=24, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_LIFETIME_SECONDS


def _tokens(user_id: int, refresh_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=issue_access_token(user_id),
        refresh_token=refresh_token,
    )


_OPAQUE_VALUE_RE = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
_BOT_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")
_MAX_CALLBACK_BODY_BYTES = 16 * 1024
_CALLBACK_PATH = "/api/mobile/auth/telegram/callback"


def _login_origin() -> str:
    origin = TELEGRAM_LOGIN_ORIGIN.strip().rstrip("/")
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram Login не настроен",
        )
    return origin


def _login_error_response(status_code: int) -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>Вход</title></head>
<body><main><p>Не удалось начать вход. Попробуйте снова.</p></main></body></html>""",
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _login_page(bot_username: str) -> HTMLResponse:
    safe_bot_username = html.escape(bot_username, quote=True)
    content = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Вход через Telegram</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; }}
    main {{ min-height: 100vh; display: grid; place-content: center; text-align: center; gap: 16px; }}
    #error {{ color: #b42318; }}
  </style>
</head>
<body>
  <main>
    <h1>Войти в Carting</h1>
    <script async src="https://telegram.org/js/telegram-widget.js?22"
      data-telegram-login="{safe_bot_username}"
      data-size="large"
      data-onauth="onTelegramAuth(user)"></script>
    <p id="error" role="alert" hidden>Не удалось войти. Попробуйте снова.</p>
  </main>
  <script>
    const loginState = new URLSearchParams(window.location.search).get("state");
    window.history.replaceState({{}}, document.title, window.location.pathname);

    function showLoginError() {{
      document.getElementById("error").hidden = false;
    }}

    function onTelegramAuth(user) {{
      if (!loginState || !user) {{
        showLoginError();
        return;
      }}
      try {{
        const form = document.createElement("form");
        form.method = "post";
        form.action = "{_CALLBACK_PATH}";

        const fields = {{state: loginState, ...user}};
        for (const [name, value] of Object.entries(fields)) {{
          if (value === undefined || value === null) continue;
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = name;
          input.value = String(value);
          form.appendChild(input);
        }}
        document.body.appendChild(form);
        form.submit();
      }} catch (_) {{
        showLoginError();
      }}
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(
        content,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "default-src 'none'; script-src 'unsafe-inline' https://telegram.org; "
                "style-src 'unsafe-inline'; frame-src https://oauth.telegram.org; "
                "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
            ),
        },
    )


async def _callback_form(request: Request) -> Dict[str, str]:
    content_type = request.headers.get("content-type", "").partition(";")[0].strip()
    if content_type != "application/x-www-form-urlencoded":
        raise ValueError("Unsupported callback content type")
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_CALLBACK_BODY_BYTES:
        raise ValueError("Callback payload is too large")
    body = await request.body()
    if len(body) > _MAX_CALLBACK_BODY_BYTES:
        raise ValueError("Callback payload is too large")
    pairs = parse_qsl(
        body.decode("utf-8"),
        keep_blank_values=True,
        strict_parsing=True,
        max_num_fields=16,
    )
    form: Dict[str, str] = {}
    for key, value in pairs:
        if key in form:
            raise ValueError("Duplicate callback field")
        form[key] = value
    return form


def _callback_rejected() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить вход",
    )


@router.post("/telegram/start", response_model=TelegramStartResponse)
async def start_telegram_login(request: TelegramStartRequest) -> TelegramStartResponse:
    origin = _login_origin()
    for _ in range(3):
        state_value = secrets.token_urlsafe(32)
        try:
            created = create_telegram_login_transaction(
                state_value,
                request.code_challenge,
                request.code_challenge_method,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный запрос входа",
            ) from exc
        if created:
            authorization_url = (
                f"{origin}/api/mobile/auth/telegram/login?"
                + urlencode({"state": state_value})
            )
            return TelegramStartResponse(
                authorization_url=authorization_url,
                state=state_value,
            )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Не удалось начать вход",
    )


@router.get("/telegram/login", response_class=HTMLResponse)
async def telegram_login_page(request: Request) -> HTMLResponse:
    state_value = request.scope.get("carting.telegram_login_state")
    if not isinstance(state_value, str):
        return _login_error_response(status.HTTP_401_UNAUTHORIZED)
    if find_telegram_login_transaction(state_value) is None:
        return _login_error_response(status.HTTP_401_UNAUTHORIZED)
    bot_username = TELEGRAM_LOGIN_BOT_USERNAME.strip().lstrip("@")
    if not _BOT_USERNAME_RE.fullmatch(bot_username):
        return _login_error_response(status.HTTP_503_SERVICE_UNAVAILABLE)
    return _login_page(bot_username)


@router.post("/telegram/callback")
async def telegram_login_callback(request: Request) -> RedirectResponse:
    try:
        form = await _callback_form(request)
        state_value = form.pop("state")
    except (KeyError, UnicodeDecodeError, ValueError):
        raise _callback_rejected()

    if find_telegram_login_transaction(state_value) is None:
        raise _callback_rejected()
    if not BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram Login не настроен",
        )

    try:
        user_id = validate_telegram_login_payload(form, BOT_TOKEN)
    except ValueError:
        raise _callback_rejected()

    first_name = form.get("first_name", "").strip()
    last_name = form.get("last_name", "").strip()
    if not first_name:
        raise _callback_rejected()
    telegram_name = " ".join(part for part in (first_name, last_name) if part)
    try:
        code = complete_telegram_login_and_issue_authorization_code(
            state_value,
            user_id,
            telegram_name,
            form.get("username") or None,
            form.get("photo_url") or None,
        )
    except sqlite3.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось завершить вход",
        )
    if code is None:
        raise _callback_rejected()
    location = "carting://auth/callback?" + urlencode(
        {"code": code, "state": state_value}
    )
    return RedirectResponse(location, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/telegram/exchange", response_model=TokenResponse)
async def exchange_telegram_code(request: TelegramExchangeRequest) -> TokenResponse:
    if (
        not _OPAQUE_VALUE_RE.fullmatch(request.code)
        or not _OPAQUE_VALUE_RE.fullmatch(request.state)
        or not _OPAQUE_VALUE_RE.fullmatch(request.code_verifier)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истёкший вход",
        )
    try:
        exchanged = consume_telegram_authorization_code_and_create_refresh_session(
            request.code, request.state, request.code_verifier
        )
    except sqlite3.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось завершить вход",
        )
    if exchanged is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истёкший вход",
        )
    user_id, refresh_token = exchanged
    return _tokens(user_id, refresh_token)


@router.post("/telegram/native/exchange", response_model=TokenResponse)
async def exchange_telegram_native_id_token(
    request: TelegramNativeExchangeRequest,
) -> TokenResponse:
    try:
        identity = validate_telegram_id_token(request.id_token)
    except ValueError:
        raise _callback_rejected()
    try:
        refresh_token = provision_telegram_identity_and_create_refresh_session(
            identity.user_id,
            identity.telegram_name,
            identity.username,
            identity.photo_url,
        )
    except sqlite3.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось завершить вход",
        )
    return _tokens(identity.user_id, refresh_token)


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
