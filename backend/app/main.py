import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import Settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(
            level=logging.DEBUG if config.debug else logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        logger.info("Starting %s %s (%s)", config.app_name, config.app_version, config.environment)
        yield
        logger.info("Application stopped")

    application = FastAPI(
        title=config.app_name,
        description="HireSense AI career intelligence platform API. Task 001: application health only.",
        version=config.app_version,
        debug=config.debug,
        lifespan=lifespan,
    )
    application.state.settings = config
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.include_router(health_router, prefix=config.api_prefix)
    return application


app = create_app()
