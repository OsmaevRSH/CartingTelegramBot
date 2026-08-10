import pytest
from fastapi.testclient import TestClient

import core.database.db as db
from api.main import app


@pytest.fixture
def client(tmp_path):
    original_db_file = db.DB_FILE
    db.DB_FILE = tmp_path / 'races.db'
    try:
        db.init_db()

        with TestClient(app) as test_client:
            yield test_client
    finally:
        db.DB_FILE = original_db_file
