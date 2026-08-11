import hashlib
import asyncio
import sqlite3
from base64 import urlsafe_b64encode
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
    complete_telegram_login_transaction,
    create_refresh_session,
    create_telegram_login_transaction,
    consume_telegram_authorization_code,
    find_telegram_login_transaction,
    issue_telegram_authorization_code,
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


def _s256_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode()


def _create_completed_transaction(state: str, verifier: str, user_id: int = 42) -> None:
    assert create_telegram_login_transaction(state, _s256_challenge(verifier), "S256")
    assert complete_telegram_login_transaction(state, user_id)


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
