from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.database.session import build_engine, session_factory

BACKEND = Path(__file__).resolve().parents[1]

def migration_config(settings):
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["settings"] = settings
    return config

@pytest.fixture
def database(tmp_path):
    settings = Settings(_env_file=None, database_url="sqlite:///" + (tmp_path / "test.sqlite3").as_posix())
    command.upgrade(migration_config(settings), "head")
    engine = build_engine(settings)
    try:
        yield settings, engine, session_factory(engine)
    finally:
        engine.dispose()
