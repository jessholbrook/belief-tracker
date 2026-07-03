import pytest

from app import db
from app.config import settings


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Point the app at a fresh SQLite file and initialize the schema."""
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    db.init_db()
    return settings.db_path
