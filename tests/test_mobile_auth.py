import hashlib
import hmac
import asyncio
import logging
import re
import sqlite3
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from urllib.parse import parse_qs, urlsplit

import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import core.database.db as db
import api.main as api_main
import api.routes.auth as auth_routes
import core.auth.tokens as auth_tokens
from api.dependencies import require_mobile_user
from core.auth.tokens import decode_access_token, issue_access_token
from core.config.config import AUTH_SECRET
from core.database.db import (
    complete_telegram_login_transaction,
    create_refresh_session,
    create_telegram_login_transaction,
    consume_telegram_authorization_code,
    find_telegram_login_transaction,
    issue_telegram_authorization_code,
    revoke_refresh_session,
    rotate_refresh_session,
    upsert_user_profile,
)


@pytest.fixture
def pairing_db(tmp_path):
    original_db_file = db.DB_FILE
    db.DB_FILE = tmp_path / "races.db"
    try:
        db.init_db()
        yield db.DB_FILE
    finally:
        db.DB_FILE = original_db_file


def _s256_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode()


def _create_completed_transaction(state: str, verifier: str, user_id: int = 42) -> None:
    assert create_telegram_login_transaction(state, _s256_challenge(verifier), "S256")
    assert complete_telegram_login_transaction(state, user_id)


@pytest.fixture
def telegram_jwks(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class LocalJwkClient:
        def get_signing_key_from_jwt(self, _id_token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(
        auth_tokens,
        "get_telegram_jwk_client",
        lambda: LocalJwkClient(),
        raising=False,
    )
    monkeypatch.setattr(
        auth_tokens,
        "TELEGRAM_LOGIN_CLIENT_ID",
        "7525532588",
        raising=False,
    )
    return SimpleNamespace(private_key=private_key)


def sign_telegram_id_token(
    private_key,
    *,
    sub: object,
    aud: str,
    telegram_id: Optional[object] = None,
    expires_at: Optional[datetime] = None,
    issuer: str = "https://oauth.telegram.org",
    kid: str = "test-key",
    include_sub: bool = True,
    **profile_claims: str,
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "id": sub if telegram_id is None else telegram_id,
        "aud": aud,
        "iss": issuer,
        "exp": expires_at or now + timedelta(minutes=5),
        **profile_claims,
    }
    if include_sub:
        claims["sub"] = sub
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def test_native_exchange_accepts_telegram_jwt_and_returns_carting_tokens(
    client, telegram_jwks
):
    token = sign_telegram_id_token(
        telegram_jwks.private_key, sub="42", aud="7525532588"
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 200
    assert response.json()["expires_in"] == 900


def test_native_exchange_accepts_oidc_subject_and_official_profile_claims(
    client, telegram_jwks, pairing_db
):
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="telegram-opaque-subject",
        telegram_id=42,
        aud="7525532588",
        name="Alice OIDC",
        given_name="Alice",
        family_name="Smith",
        preferred_username="alice",
        picture="https://example.test/alice.jpg",
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 200
    with sqlite3.connect(pairing_db) as conn:
        assert conn.execute(
            """
            SELECT telegram_name, telegram_username, photo_url
            FROM user_profiles WHERE user_id = 42
            """
        ).fetchone() == ("Alice OIDC", "alice", "https://example.test/alice.jpg")


def test_native_exchange_preserves_legacy_profile_claim_fallbacks(
    client, telegram_jwks, pairing_db
):
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="legacy-subject",
        telegram_id=43,
        aud="7525532588",
        first_name="Legacy",
        last_name="User",
        username="legacy_user",
        photo_url="https://example.test/legacy.jpg",
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 200
    with sqlite3.connect(pairing_db) as conn:
        assert conn.execute(
            """
            SELECT telegram_name, telegram_username, photo_url
            FROM user_profiles WHERE user_id = 43
            """
        ).fetchone() == (
            "Legacy User",
            "legacy_user",
            "https://example.test/legacy.jpg",
        )


def test_native_exchange_rejects_wrong_signature_or_audience(client, telegram_jwks):
    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": "invalid"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_native_exchange_logs_failure_kind_without_logging_the_id_token(
    client, telegram_jwks, caplog
):
    with caplog.at_level(logging.WARNING, logger="core.auth.tokens"):
        response = client.post(
            "/api/mobile/auth/telegram/native/exchange", json={"id_token": "invalid"}
        )

    assert response.status_code == 401
    assert "DecodeError" in caplog.text
    assert "id_token" not in caplog.text
    assert "invalid" not in caplog.text


def test_native_exchange_rejects_wrong_audience(client, telegram_jwks):
    token = sign_telegram_id_token(
        telegram_jwks.private_key, sub="42", aud="other-client"
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_native_exchange_rejects_token_signed_by_unrelated_private_key(
    client, telegram_jwks
):
    unrelated_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = sign_telegram_id_token(
        unrelated_key, sub="42", aud="7525532588"
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_native_exchange_rejects_expired_valid_signature(client, telegram_jwks):
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="42",
        aud="7525532588",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_native_exchange_rejects_wrong_issuer(client, telegram_jwks):
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="42",
        aud="7525532588",
        issuer="https://attacker.example",
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_native_exchange_rejects_nonpositive_numeric_identity(client, telegram_jwks):
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="0",
        telegram_id="0",
        aud="7525532588",
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


@pytest.mark.parametrize(
    ("sub", "include_sub"),
    [("", True), ("   ", True), (42, True), ("ignored", False)],
)
def test_native_exchange_rejects_missing_empty_or_nonstring_subject(
    client, telegram_jwks, sub, include_sub
):
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub=sub,
        telegram_id="42",
        aud="7525532588",
        include_sub=include_sub,
    )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_native_exchange_throttles_unknown_jwk_id_fetches(
    client, monkeypatch, telegram_jwks
):
    attempts = []

    class UnknownKidJwkClient:
        def get_signing_key_from_jwt(self, _id_token):
            attempts.append(1)
            raise jwt.PyJWKClientError(
                "Unable to find a signing key that matches: unknown-test-key"
            )

    monkeypatch.setattr(
        auth_tokens, "get_telegram_jwk_client", lambda: UnknownKidJwkClient()
    )
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="42",
        aud="7525532588",
        kid="unknown-test-key",
    )

    for _ in range(2):
        response = client.post(
            "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Не удалось подтвердить вход"}

    assert attempts == [1]


def test_native_exchange_retries_valid_kid_after_jwks_connection_failure(
    client, monkeypatch, telegram_jwks
):
    attempts = []

    class FlakyJwkClient:
        def get_signing_key_from_jwt(self, _id_token):
            attempts.append(1)
            if len(attempts) == 1:
                raise jwt.PyJWKClientConnectionError("Temporary JWKS outage")
            return SimpleNamespace(key=telegram_jwks.private_key.public_key())

    monkeypatch.setattr(
        auth_tokens, "get_telegram_jwk_client", lambda: FlakyJwkClient()
    )
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="42",
        aud="7525532588",
        kid="transient-test-key",
    )

    failed = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )
    retried = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert failed.status_code == 401
    assert failed.json() == {"detail": "Не удалось подтвердить вход"}
    assert retried.status_code == 200
    assert retried.json()["expires_in"] == 900
    assert attempts == [1, 1]


def test_native_exchange_rolls_back_profile_when_refresh_session_creation_fails(
    client, telegram_jwks, pairing_db
):
    token = sign_telegram_id_token(
        telegram_jwks.private_key,
        sub="42",
        aud="7525532588",
        first_name="Alice",
    )
    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_native_refresh_session_creation
            BEFORE INSERT ON mobile_refresh_sessions
            BEGIN
                SELECT RAISE(ABORT, 'forced refresh failure');
            END
            """
        )

    response = client.post(
        "/api/mobile/auth/telegram/native/exchange", json={"id_token": token}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Не удалось завершить вход"}
    with sqlite3.connect(pairing_db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM user_profiles WHERE user_id = 42"
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT COUNT(*) FROM mobile_refresh_sessions WHERE user_id = 42"
        ).fetchone() == (0,)


def _telegram_payload(
    bot_token: str,
    *,
    user_id: str = "42",
    auth_date: Optional[int] = None,
    **fields: str,
) -> dict[str, str]:
    payload = {
        "id": user_id,
        "first_name": "Alice",
        "auth_date": str(
            auth_date
            if auth_date is not None
            else int(datetime.now(timezone.utc).timestamp())
        ),
        **fields,
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(payload.items())
    )
    secret = hashlib.sha256(bot_token.encode()).digest()
    payload["hash"] = hmac.new(
        secret, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return payload


def _start_telegram_login(client, monkeypatch, verifier: str = "v" * 43):
    monkeypatch.setattr(
        auth_routes, "TELEGRAM_LOGIN_ORIGIN", "https://carting.example"
    )
    response = client.post(
        "/api/mobile/auth/telegram/start",
        json={
            "code_challenge": _s256_challenge(verifier),
            "code_challenge_method": "S256",
        },
    )
    assert response.status_code == 200
    return response.json()


def _callback_location(
    client,
    monkeypatch,
    *,
    state: str,
    payload: dict[str, str],
    bot_token: str = "123456:test-token",
) -> str:
    monkeypatch.setattr(auth_routes, "BOT_TOKEN", bot_token)
    response = client.post(
        "/api/mobile/auth/telegram/callback",
        data={"state": state, **payload},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response.headers["location"]


def test_legacy_pairing_implementation_and_exchange_route_are_absent(client):
    project_root = Path(__file__).resolve().parents[1]
    legacy_sources = {
        "bot": project_root / "bot/handlers/bot.py",
        "auth": project_root / "api/routes/auth.py",
        "database": project_root / "core/database/db.py",
    }

    assert client.post(
        "/api/mobile/auth/exchange", json={"code": "legacy-pairing-code"}
    ).status_code == 404
    assert not hasattr(db, "create_pairing_code")
    assert not hasattr(db, "consume_pairing_code")
    assert "/ios" not in legacy_sources["bot"].read_text()
    with sqlite3.connect(db.DB_FILE) as conn:
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("mobile_pairing_codes",),
        ).fetchone() is None
    assert "consume_pairing_code" not in legacy_sources["auth"].read_text()


def test_telegram_start_returns_fixed_https_login_url(client, monkeypatch):
    verifier = "v" * 43

    body = _start_telegram_login(client, monkeypatch, verifier)

    assert body["expires_in"] == 600
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", body["state"])
    assert body["authorization_url"] == (
        "https://carting.example/api/mobile/auth/telegram/login?state="
        + body["state"]
    )
    assert verifier not in body["authorization_url"]
    assert find_telegram_login_transaction(body["state"]) is not None


@pytest.mark.parametrize(
    ("challenge", "method"),
    [
        ("invalid", "S256"),
        (_s256_challenge("v" * 43), "plain"),
    ],
)
def test_telegram_start_rejects_invalid_pkce(client, monkeypatch, challenge, method):
    monkeypatch.setattr(
        auth_routes, "TELEGRAM_LOGIN_ORIGIN", "https://carting.example"
    )

    response = client.post(
        "/api/mobile/auth/telegram/start",
        json={"code_challenge": challenge, "code_challenge_method": method},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Недействительный запрос входа"}


def test_telegram_start_does_not_accept_redirect_url(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes, "TELEGRAM_LOGIN_ORIGIN", "https://carting.example"
    )

    response = client.post(
        "/api/mobile/auth/telegram/start",
        json={
            "code_challenge": _s256_challenge("v" * 43),
            "code_challenge_method": "S256",
            "redirect_url": "https://attacker.example/callback",
        },
    )

    assert response.status_code == 422


def test_telegram_login_page_is_available_only_for_live_state(client, monkeypatch):
    monkeypatch.setattr(auth_routes, "TELEGRAM_LOGIN_BOT_USERNAME", "CartingTestBot")
    started = _start_telegram_login(client, monkeypatch)

    response = client.get(
        "/api/mobile/auth/telegram/login", params={"state": started["state"]}
    )

    assert response.status_code == 200
    assert "https://telegram.org/js/telegram-widget.js" in response.text
    assert 'data-telegram-login="CartingTestBot"' in response.text
    assert 'action="/api/mobile/auth/telegram/callback"' not in response.text
    assert started["state"] not in response.text
    assert response.headers["cache-control"] == "no-store"

    rejected = client.get(
        "/api/mobile/auth/telegram/login", params={"state": "unknown-state"}
    )
    assert rejected.status_code == 401
    assert "unknown-state" not in rejected.text


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/api/mobile/auth/telegram/login", 200),
        ("/api/mobile/auth/telegram/login/", 307),
    ],
)
def test_telegram_login_state_is_redacted_before_uvicorn_access_logging(
    client, monkeypatch, path, expected_status
):
    monkeypatch.setattr(auth_routes, "TELEGRAM_LOGIN_BOT_USERNAME", "CartingTestBot")
    started = _start_telegram_login(client, monkeypatch)
    captured_scope = {}

    async def downstream(scope, receive, send):
        captured_scope.update(scope)
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        return None

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": f"state={started['state']}".encode(),
        "headers": [],
    }

    asyncio.run(
        api_main.RedactTelegramLoginStateMiddleware(downstream)(
            scope,
            receive,
            send,
        )
    )

    assert started["state"].encode() not in captured_scope["query_string"]
    assert captured_scope["query_string"] == b""
    assert client.get(
        path,
        params={"state": started["state"]},
        follow_redirects=False,
    ).status_code == expected_status


def test_reverse_proxies_skip_telegram_login_access_logs():
    root = Path(__file__).resolve().parent.parent

    caddyfile = (root / "deployment" / "Caddyfile").read_text()
    nginx_config = (root / "deployment" / "webapp" / "nginx.conf").read_text()

    assert "\n    log\n" not in caddyfile
    assert (
        "@telegram_login path /api/mobile/auth/telegram/login "
        "/api/mobile/auth/telegram/login/"
    ) in caddyfile
    assert "log_skip @telegram_login" in caddyfile
    assert "location = /api/mobile/auth/telegram/login" in nginx_config
    assert "location = /api/mobile/auth/telegram/login/" in nginx_config
    assert "access_log off;" in nginx_config


def test_telegram_callback_provisions_profile_and_redirects_with_opaque_code(
    client, monkeypatch, pairing_db
):
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch)
    payload = _telegram_payload(
        bot_token,
        user_id="4242",
        first_name="Alice",
        last_name="Smith",
        username="alice",
        photo_url="https://example.test/alice.jpg",
    )

    location = _callback_location(
        client,
        monkeypatch,
        state=started["state"],
        payload=payload,
        bot_token=bot_token,
    )

    redirect = urlsplit(location)
    query = parse_qs(redirect.query)
    assert (redirect.scheme, redirect.netloc, redirect.path) == (
        "carting",
        "auth",
        "/callback",
    )
    assert query["state"] == [started["state"]]
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", query["code"][0])
    assert "access_token" not in location
    assert "refresh_token" not in location
    with sqlite3.connect(pairing_db) as conn:
        assert conn.execute(
            """
            SELECT telegram_name, telegram_username, photo_url
            FROM user_profiles WHERE user_id = 4242
            """
        ).fetchone() == ("Alice Smith", "alice", "https://example.test/alice.jpg")


@pytest.mark.parametrize("mutation", ["altered", "missing"])
def test_telegram_callback_rejects_altered_or_missing_hash(
    client, monkeypatch, mutation
):
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch)
    payload = _telegram_payload(bot_token)
    if mutation == "altered":
        payload["first_name"] = "Mallory"
    else:
        payload.pop("hash")
    monkeypatch.setattr(auth_routes, "BOT_TOKEN", bot_token)

    response = client.post(
        "/api/mobile/auth/telegram/callback",
        data={"state": started["state"], **payload},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_telegram_callback_rejects_non_ascii_hash_without_server_error(
    client, monkeypatch
):
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch)
    payload = _telegram_payload(bot_token)
    payload["hash"] = "я" * 64
    monkeypatch.setattr(auth_routes, "BOT_TOKEN", bot_token)

    response = client.post(
        "/api/mobile/auth/telegram/callback",
        data={"state": started["state"], **payload},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


@pytest.mark.parametrize("telegram_id", ["not-a-number", "", "-42", "0"])
def test_telegram_callback_rejects_malformed_telegram_id(
    client, monkeypatch, telegram_id
):
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch)
    payload = _telegram_payload(bot_token, user_id=telegram_id)
    monkeypatch.setattr(auth_routes, "BOT_TOKEN", bot_token)

    response = client.post(
        "/api/mobile/auth/telegram/callback",
        data={"state": started["state"], **payload},
        follow_redirects=False,
    )

    assert response.status_code == 401


@pytest.mark.parametrize("offset_seconds", [-601, 61])
def test_telegram_callback_rejects_stale_or_far_future_auth_date(
    client, monkeypatch, offset_seconds
):
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch)
    auth_date = int(datetime.now(timezone.utc).timestamp()) + offset_seconds
    payload = _telegram_payload(bot_token, auth_date=auth_date)
    monkeypatch.setattr(auth_routes, "BOT_TOKEN", bot_token)

    response = client.post(
        "/api/mobile/auth/telegram/callback",
        data={"state": started["state"], **payload},
        follow_redirects=False,
    )

    assert response.status_code == 401


def test_telegram_callback_requires_live_transaction_before_accepting_payload(
    client, monkeypatch
):
    bot_token = "123456:test-token"
    monkeypatch.setattr(auth_routes, "BOT_TOKEN", bot_token)

    response = client.post(
        "/api/mobile/auth/telegram/callback",
        data={"state": "unknown-state", **_telegram_payload(bot_token)},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Не удалось подтвердить вход"}


def test_telegram_login_page_rejects_completed_transaction(client, monkeypatch):
    bot_token = "123456:test-token"
    monkeypatch.setattr(auth_routes, "TELEGRAM_LOGIN_BOT_USERNAME", "CartingTestBot")
    started = _start_telegram_login(client, monkeypatch)
    _callback_location(
        client,
        monkeypatch,
        state=started["state"],
        payload=_telegram_payload(bot_token),
        bot_token=bot_token,
    )

    response = client.get(
        "/api/mobile/auth/telegram/login", params={"state": started["state"]}
    )

    assert response.status_code == 401
    assert started["state"] not in response.text


def test_telegram_callback_rolls_back_completion_when_profile_provisioning_fails(
    client, monkeypatch, pairing_db
):
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch)
    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_telegram_profile_provisioning
            BEFORE INSERT ON user_profiles
            WHEN NEW.user_id = 42
            BEGIN
                SELECT RAISE(ABORT, 'forced profile failure');
            END
            """
        )

    monkeypatch.setattr(auth_routes, "BOT_TOKEN", bot_token)
    response = client.post(
        "/api/mobile/auth/telegram/callback",
        data={"state": started["state"], **_telegram_payload(bot_token)},
        follow_redirects=False,
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Не удалось завершить вход"}
    with sqlite3.connect(pairing_db) as conn:
        assert conn.execute(
            """
            SELECT completed_at, user_id
            FROM mobile_telegram_login_transactions
            WHERE state_hash = ?
            """,
            (hashlib.sha256(started["state"].encode()).hexdigest(),),
        ).fetchone() == (None, None)
        assert conn.execute(
            "SELECT COUNT(*) FROM mobile_telegram_authorization_codes"
        ).fetchone() == (0,)


def test_telegram_exchange_keeps_code_usable_when_refresh_session_creation_fails(
    client, monkeypatch, pairing_db
):
    verifier = "v" * 43
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch, verifier)
    location = _callback_location(
        client,
        monkeypatch,
        state=started["state"],
        payload=_telegram_payload(bot_token),
        bot_token=bot_token,
    )
    code = parse_qs(urlsplit(location).query)["code"][0]
    request = {"code": code, "state": started["state"], "code_verifier": verifier}
    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_refresh_session_creation
            BEFORE INSERT ON mobile_refresh_sessions
            BEGIN
                SELECT RAISE(ABORT, 'forced refresh failure');
            END
            """
        )

    failed = client.post("/api/mobile/auth/telegram/exchange", json=request)

    assert failed.status_code == 503
    assert failed.json() == {"detail": "Не удалось завершить вход"}
    with sqlite3.connect(pairing_db) as conn:
        conn.execute("DROP TRIGGER fail_refresh_session_creation")

    assert client.post("/api/mobile/auth/telegram/exchange", json=request).status_code == 200


def test_telegram_callback_missing_optional_fields_preserves_existing_profile(
    client, monkeypatch, pairing_db
):
    upsert_user_profile(42, "Stored Name", "stored_user", "https://stored/photo")
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch)
    payload = _telegram_payload(
        bot_token,
        user_id="42",
        first_name="Updated",
        username="",
        photo_url="",
    )

    _callback_location(
        client,
        monkeypatch,
        state=started["state"],
        payload=payload,
        bot_token=bot_token,
    )

    with sqlite3.connect(pairing_db) as conn:
        assert conn.execute(
            """
            SELECT telegram_name, telegram_username, photo_url
            FROM user_profiles WHERE user_id = 42
            """
        ).fetchone() == ("Updated", "stored_user", "https://stored/photo")


def test_telegram_exchange_returns_tokens_once_for_matching_state_and_verifier(
    client, monkeypatch
):
    verifier = "v" * 43
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch, verifier)
    location = _callback_location(
        client,
        monkeypatch,
        state=started["state"],
        payload=_telegram_payload(bot_token),
        bot_token=bot_token,
    )
    code = parse_qs(urlsplit(location).query)["code"][0]
    request = {"code": code, "state": started["state"], "code_verifier": verifier}

    response = client.post("/api/mobile/auth/telegram/exchange", json=request)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert decode_access_token(body["access_token"]) == 42
    assert len(body["refresh_token"]) >= 24
    assert client.post(
        "/api/mobile/auth/telegram/exchange", json=request
    ).status_code == 401


@pytest.mark.parametrize(
    ("state", "verifier"),
    [("other-state", "v" * 43), (None, "x" * 43)],
)
def test_telegram_exchange_rejects_state_or_verifier_mismatch(
    client, monkeypatch, state, verifier
):
    original_verifier = "v" * 43
    bot_token = "123456:test-token"
    started = _start_telegram_login(client, monkeypatch, original_verifier)
    location = _callback_location(
        client,
        monkeypatch,
        state=started["state"],
        payload=_telegram_payload(bot_token),
        bot_token=bot_token,
    )
    code = parse_qs(urlsplit(location).query)["code"][0]

    response = client.post(
        "/api/mobile/auth/telegram/exchange",
        json={
            "code": code,
            "state": state or started["state"],
            "code_verifier": verifier,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Недействительный или истёкший вход"}


def test_login_transaction_rejects_duplicate_state(pairing_db):
    state = "login-state"
    challenge = _s256_challenge("v" * 43)

    assert create_telegram_login_transaction(state, challenge, "S256")
    assert create_telegram_login_transaction(state, challenge, "S256") is False
    assert find_telegram_login_transaction(state) is not None


def test_login_transaction_uses_exact_ten_minute_ttl(pairing_db):
    state = "login-state"

    assert create_telegram_login_transaction(state, _s256_challenge("v" * 43), "S256")
    with sqlite3.connect(pairing_db) as conn:
        created_at, expires_at = conn.execute(
            """
            SELECT created_at, expires_at
            FROM mobile_telegram_login_transactions
            WHERE state_hash = ?
            """,
            (hashlib.sha256(state.encode()).hexdigest(),),
        ).fetchone()

    assert datetime.fromisoformat(expires_at) - datetime.fromisoformat(created_at) == timedelta(minutes=10)


@pytest.mark.parametrize(
    ("challenge", "method"),
    [
        (_s256_challenge("v" * 43), "plain"),
        ("not-a-valid-s256-challenge", "S256"),
    ],
)
def test_login_transaction_rejects_non_s256_or_malformed_challenge(
    pairing_db, challenge, method
):
    with pytest.raises(ValueError):
        create_telegram_login_transaction("login-state", challenge, method)


def test_login_transaction_expires_after_ten_minutes(pairing_db):
    state = "expired-login-state"
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    challenge = _s256_challenge("v" * 43)
    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            INSERT INTO mobile_telegram_login_transactions
                (state_hash, code_challenge_hash, created_at, expires_at, completed_at, user_id)
            VALUES (?, ?, ?, ?, NULL, NULL)
            """,
            (
                state_hash,
                hashlib.sha256(challenge.encode()).hexdigest(),
                (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat(),
                (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            ),
        )

    assert find_telegram_login_transaction(state) is None
    assert complete_telegram_login_transaction(state, 42) is False


def test_login_transaction_and_authorization_code_store_only_hashes(pairing_db):
    state = "raw-login-state"
    verifier = "v" * 43
    challenge = _s256_challenge(verifier)
    _create_completed_transaction(state, verifier)

    code = issue_telegram_authorization_code(state)

    assert code is not None
    with sqlite3.connect(pairing_db) as conn:
        transaction = conn.execute(
            "SELECT state_hash, code_challenge_hash FROM mobile_telegram_login_transactions"
        ).fetchone()
        authorization_code = conn.execute(
            "SELECT code_hash FROM mobile_telegram_authorization_codes"
        ).fetchone()

    assert transaction == (
        hashlib.sha256(state.encode()).hexdigest(),
        hashlib.sha256(challenge.encode()).hexdigest(),
    )
    assert authorization_code == (hashlib.sha256(code.encode()).hexdigest(),)
    assert state not in transaction
    assert verifier not in transaction
    assert code not in authorization_code


def test_authorization_code_expires_after_sixty_seconds(pairing_db):
    state = "login-state"
    verifier = "v" * 43
    _create_completed_transaction(state, verifier)
    code = issue_telegram_authorization_code(state)
    assert code is not None

    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            UPDATE mobile_telegram_authorization_codes
            SET expires_at = ?
            WHERE code_hash = ?
            """,
            (
                (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                hashlib.sha256(code.encode()).hexdigest(),
            ),
        )

    assert consume_telegram_authorization_code(code, state, verifier) is None


def test_authorization_code_uses_exact_sixty_second_ttl(pairing_db):
    state = "login-state"
    verifier = "v" * 43
    _create_completed_transaction(state, verifier)
    code = issue_telegram_authorization_code(state)
    assert code is not None

    with sqlite3.connect(pairing_db) as conn:
        created_at, expires_at = conn.execute(
            """
            SELECT created_at, expires_at
            FROM mobile_telegram_authorization_codes
            WHERE code_hash = ?
            """,
            (hashlib.sha256(code.encode()).hexdigest(),),
        ).fetchone()

    assert datetime.fromisoformat(expires_at) - datetime.fromisoformat(created_at) == timedelta(seconds=60)


def test_authorization_code_remains_valid_after_its_transaction_expires(pairing_db):
    state = "login-state"
    verifier = "v" * 43
    _create_completed_transaction(state, verifier)
    code = issue_telegram_authorization_code(state)
    assert code is not None

    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            UPDATE mobile_telegram_login_transactions
            SET expires_at = ?
            WHERE state_hash = ?
            """,
            (
                (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                hashlib.sha256(state.encode()).hexdigest(),
            ),
        )

    assert consume_telegram_authorization_code(code, state, verifier) == 42


def test_authorization_code_can_be_consumed_once(pairing_db):
    state = "login-state"
    verifier = "v" * 43
    _create_completed_transaction(state, verifier)
    code = issue_telegram_authorization_code(state)
    assert code is not None

    assert consume_telegram_authorization_code(code, state, verifier) == 42
    assert consume_telegram_authorization_code(code, state, verifier) is None


def test_authorization_code_rejects_state_mismatch(pairing_db):
    state = "login-state"
    verifier = "v" * 43
    _create_completed_transaction(state, verifier)
    code = issue_telegram_authorization_code(state)
    assert code is not None

    assert consume_telegram_authorization_code(code, "other-state", verifier) is None


def test_authorization_code_rejects_verifier_mismatch(pairing_db):
    state = "login-state"
    verifier = "v" * 43
    _create_completed_transaction(state, verifier)
    code = issue_telegram_authorization_code(state)
    assert code is not None

    assert consume_telegram_authorization_code(code, state, "x" * 43) is None


def test_refresh_rotation_invalidates_predecessor_and_replacement_is_usable(pairing_db):
    token = create_refresh_session(42)

    rotated = rotate_refresh_session(token)

    assert rotated is not None
    user_id, replacement = rotated
    assert user_id == 42
    assert replacement != token
    assert rotate_refresh_session(token) is None
    assert rotate_refresh_session(replacement) is not None


def test_expired_refresh_session_cannot_be_rotated(pairing_db):
    token = "expired-refresh-token"
    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            INSERT INTO mobile_refresh_sessions (token_hash, user_id, expires_at, revoked_at)
            VALUES (?, ?, ?, NULL)
            """,
            (
                hashlib.sha256(token.encode()).hexdigest(),
                42,
                (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            ),
        )

    assert rotate_refresh_session(token) is None


def test_refresh_session_can_be_revoked(pairing_db):
    token = create_refresh_session(42)

    assert revoke_refresh_session(token) is True
    assert rotate_refresh_session(token) is None
    assert revoke_refresh_session(token) is False


def test_access_token_round_trip_uses_mobile_user_id():
    token = issue_access_token(42)

    assert decode_access_token(token) == 42
    claims = jwt.decode(token, AUTH_SECRET, algorithms=['HS256'])
    assert claims['sub'] == '42'
    assert claims['type'] == 'access'
    assert claims['exp'] - claims['iat'] == 900


def test_access_token_lifetime_cannot_be_overridden(monkeypatch):
    monkeypatch.setenv('ACCESS_TOKEN_TTL_SECONDS', '1')

    token = issue_access_token(42)
    claims = jwt.decode(token, AUTH_SECRET, algorithms=['HS256'])

    assert claims['exp'] - claims['iat'] == 900


@pytest.mark.parametrize(
    'token',
    [
        'malformed',
        jwt.encode({'sub': '42', 'type': 'refresh'}, AUTH_SECRET, algorithm='HS256'),
        jwt.encode(
            {
                'sub': '42',
                'type': 'access',
                'exp': datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            AUTH_SECRET,
            algorithm='HS256',
        ),
    ],
)
def test_bearer_dependency_rejects_invalid_access_tokens(token):
    with pytest.raises(HTTPException) as error:
        require_mobile_user(HTTPAuthorizationCredentials(scheme='Bearer', credentials=token))

    assert error.value.status_code == 401


def test_bearer_dependency_rejects_missing_credentials():
    with pytest.raises(HTTPException) as error:
        require_mobile_user(None)

    assert error.value.status_code == 401


def test_refresh_rejects_reused_session(client):
    token = create_refresh_session(42)
    assert client.post(
        '/api/mobile/auth/refresh', json={'refresh_token': token}
    ).status_code == 200

    response = client.post('/api/mobile/auth/refresh', json={'refresh_token': token})

    assert response.status_code == 401
    assert response.json() == {'detail': 'Недействительная сессия'}


def test_logout_rejects_expired_refresh_session(client, pairing_db):
    token = 'expired-refresh-token-for-logout'
    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            INSERT INTO mobile_refresh_sessions (token_hash, user_id, expires_at, revoked_at)
            VALUES (?, ?, ?, NULL)
            """,
            (
                hashlib.sha256(token.encode()).hexdigest(),
                42,
                (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            ),
        )

    response = client.post(
        '/api/mobile/auth/logout', json={'refresh_token': token}
    )

    assert response.status_code == 401
    assert response.json() == {'detail': 'Недействительная сессия'}


@pytest.mark.parametrize(
    ('path', 'body'),
    [
        ('/api/mobile/auth/refresh', {'refresh_token': 'short'}),
        ('/api/mobile/auth/logout', {'refresh_token': 'short'}),
    ],
)
def test_auth_request_lengths_are_validated(client, path, body):
    assert client.post(path, json=body).status_code == 422


def test_non_test_startup_rejects_empty_auth_secret(monkeypatch):
    monkeypatch.setattr(api_main, 'AUTH_SECRET', '')
    monkeypatch.delenv('PYTEST_CURRENT_TEST')

    with pytest.raises(RuntimeError, match='AUTH_SECRET'):
        asyncio.run(api_main.startup())
