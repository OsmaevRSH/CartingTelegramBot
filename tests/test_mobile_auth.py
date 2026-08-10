import hashlib
import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import core.database.db as db
import api.main as api_main
import core.auth.tokens as auth_tokens
from api.dependencies import require_mobile_user
from core.auth.tokens import decode_access_token, issue_access_token
from core.config.config import AUTH_SECRET
from core.database.db import (
    consume_pairing_code,
    create_pairing_code,
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
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


def test_pairing_code_can_be_consumed_once(pairing_db):
    code = create_pairing_code(42)
    assert consume_pairing_code(code) == 42
    assert consume_pairing_code(code) is None


def test_expired_pairing_code_cannot_be_consumed(pairing_db):
    code = "expired-pairing-code"
    with sqlite3.connect(pairing_db) as conn:
        conn.execute(
            """
            INSERT INTO mobile_pairing_codes (code_hash, user_id, expires_at, consumed_at)
            VALUES (?, ?, ?, NULL)
            """,
            (
                hashlib.sha256(code.encode()).hexdigest(),
                42,
                (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            ),
        )

    assert consume_pairing_code(code) is None


def test_raw_pairing_code_and_refresh_token_are_not_persisted(pairing_db):
    code = create_pairing_code(42)
    token = create_refresh_session(42)
    with sqlite3.connect(pairing_db) as conn:
        code_hash = conn.execute(
            "SELECT code_hash FROM mobile_pairing_codes"
        ).fetchone()[0]
        token_hash = conn.execute(
            "SELECT token_hash FROM mobile_refresh_sessions"
        ).fetchone()[0]

    assert code_hash == hashlib.sha256(code.encode()).hexdigest()
    assert token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert code_hash != code
    assert token_hash != token


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


def test_exchange_rejects_unknown_code(client):
    response = client.post('/api/mobile/auth/exchange', json={'code': '12345678'})

    assert response.status_code == 401
    assert response.json() == {'detail': 'Недействительный или истёкший код'}


def test_exchange_refresh_and_logout(client):
    code = create_pairing_code(42)

    exchange = client.post('/api/mobile/auth/exchange', json={'code': code})

    assert exchange.status_code == 200
    tokens = exchange.json()
    assert set(tokens) == {
        'access_token',
        'refresh_token',
        'token_type',
        'expires_in',
    }
    refreshed = client.post(
        '/api/mobile/auth/refresh',
        json={'refresh_token': tokens['refresh_token']},
    )
    assert refreshed.status_code == 200
    assert client.post(
        '/api/mobile/auth/logout',
        json={'refresh_token': refreshed.json()['refresh_token']},
    ).status_code == 204


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
        ('/api/mobile/auth/exchange', {'code': 'short'}),
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
