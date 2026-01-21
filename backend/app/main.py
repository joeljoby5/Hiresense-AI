import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.exports import router as exports_router
from app.api.jobs import router as jobs_router
from app.api.analyses import router as analyses_router
from app.api.readiness import router as readiness_router
from app.api.resumes import router as resumes_router
from app.api.errors import install_error_handlers
from app.core.request_context import RequestContextMiddleware
from app.database.session import build_engine, session_factory
from app.database.resume_scope import resume_scope
from app.core.config import Settings
from app.repositories.exports import ExportRepository
from app.repositories.jobs import JobRepository
from app.repositories.analyses import AnalysisRepository

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(
            level=logging.DEBUG if config.debug else logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        # Uvicorn's default access log includes raw query strings (private search).
        # Our request middleware records route templates without parameter values.
        logging.getLogger("uvicorn.access").disabled = True
        logger.info("Starting %s %s (%s)", config.app_name, config.app_version, config.environment)
        try:
            yield
        finally:
            application.state.database_engine.dispose()
            logger.info("Application stopped")

    application = FastAPI(
        title=config.app_name,
        description="Career workspace API for resumes, jobs and deterministic analysis.",
        version=config.app_version,
        debug=False,  # Debug settings may enable safe logs, never HTTP tracebacks.
        lifespan=lifespan,
    )
    application.state.settings = config
    application.state.database_engine = build_engine(config)
    factory = session_factory(application.state.database_engine)
    application.state.resume_scope = resume_scope(factory)
    application.state.export_scope = resume_scope(factory, ExportRepository)
    application.state.job_scope = resume_scope(factory, JobRepository)
    application.state.analysis_scope = resume_scope(factory, AnalysisRepository)

    install_error_handlers(application)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Accept", "Content-Type"],
        expose_headers=["X-Request-ID", "Location"],
    )
    application.include_router(health_router, prefix=config.api_prefix)
    application.include_router(readiness_router, prefix=config.api_prefix)
    application.include_router(resumes_router, prefix=config.api_prefix)
    application.include_router(exports_router, prefix=config.api_prefix)
    application.include_router(jobs_router, prefix=config.api_prefix)
    application.include_router(analyses_router, prefix=config.api_prefix)
    return application


app = create_app()
