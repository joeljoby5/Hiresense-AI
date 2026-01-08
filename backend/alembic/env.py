from alembic import context
from app.core.config import Settings
from app.database.base import Base
from app.database.session import build_engine
from app import models  # register every implemented table

config = context.config
target_metadata = Base.metadata
# Programmatic tests may inject Settings without touching process environment.
settings = config.attributes.get("settings") or Settings()

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(settings, initialize_directory=True)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata,
                              render_as_batch=engine.dialect.name == "sqlite", compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
