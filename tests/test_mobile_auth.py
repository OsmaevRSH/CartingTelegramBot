import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import core.database.db as db
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
