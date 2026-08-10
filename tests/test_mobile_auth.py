import pytest

import core.database.db as db
from core.database.db import consume_pairing_code, create_pairing_code


@pytest.fixture
def pairing_db(tmp_path):
    original_db_file = db.DB_FILE
    db.DB_FILE = tmp_path / "races.db"
    try:
        db.init_db()
        yield
    finally:
        db.DB_FILE = original_db_file


def test_pairing_code_can_be_consumed_once(pairing_db):
    code = create_pairing_code(42)
    assert consume_pairing_code(code) == 42
    assert consume_pairing_code(code) is None


def test_exchange_rejects_unknown_code(client):
    response = client.post('/api/mobile/auth/exchange', json={'code': '12345678'})

    assert response.status_code == 401
    assert response.json() == {'detail': 'Недействительный или истёкший код'}
