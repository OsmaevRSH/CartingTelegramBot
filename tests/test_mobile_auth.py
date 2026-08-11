import hashlib
import hmac
import asyncio
import re
import sqlite3
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qs, urlsplit

import pytest
import jwt
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
