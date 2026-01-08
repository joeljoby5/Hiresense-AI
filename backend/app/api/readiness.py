from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from app.database.base import Base
from app import models  # register metadata

router = APIRouter()
INITIAL_REVISION = "0001_resume_foundation"

@router.get("/ready", tags=["System"], responses={503: {"description": "Database unavailable"}})
def get_readiness(request: Request) -> JSONResponse:
    ready = False
    try:
        with request.app.state.database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            ready = set(Base.metadata.tables) <= tables and "alembic_version" in tables
            if ready:
                ready = all(
                    set(table.columns.keys()) <= {column["name"] for column in inspector.get_columns(name)}
                    for name, table in Base.metadata.tables.items()
                )
            if ready:
                ready = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all() == [INITIAL_REVISION]
    except (SQLAlchemyError, OSError):
        ready = False
    return JSONResponse({"status": "ready" if ready else "unavailable"}, status_code=200 if ready else 503)
