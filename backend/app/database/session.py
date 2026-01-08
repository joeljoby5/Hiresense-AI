from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import logging
from uuid import uuid4

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import BACKEND_ROOT, Settings


def build_engine(settings: Settings, *, initialize_directory: bool = False) -> Engine:
    url = make_url(settings.database_url)
    log_name = "hiresense_" + uuid4().hex
    # Cap engine logging at INFO even when application DEBUG is enabled.
    # SQLAlchemy DEBUG logs result rows, which may contain private document data.
    logging.getLogger("sqlalchemy.engine.Engine." + log_name).setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )
    options = {"echo": settings.database_echo, "hide_parameters": True, "logging_name": log_name}
    if url.get_backend_name() == "sqlite":
        if url.query:
            raise ValueError("SQLite URL query parameters are not supported")
        if url.database and url.database != ":memory:":
            path = Path(url.database)
            if not path.is_absolute():
                path = BACKEND_ROOT / path
            path = path.resolve()
            if initialize_directory:
                path.parent.mkdir(parents=True, exist_ok=True)
            url = url.set(database=path.as_posix())
        else:
            options["poolclass"] = StaticPool
        options["connect_args"] = {"check_same_thread": False, "timeout": 5}
    engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, record):
            # Explicit BEGIN restores transactional DDL/savepoints on Python sqlite3.
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        @event.listens_for(engine, "begin")
        def begin_sqlite(connection):
            connection.exec_driver_sql(
                "BEGIN IMMEDIATE" if connection.get_execution_options().get("sqlite_write") else "BEGIN"
            )
    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Caller owns one transaction; repositories flush but never commit."""
    with factory() as session:
        with session.begin():
            yield session
