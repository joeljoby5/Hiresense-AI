from fastapi import APIRouter, Request

from app.core.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def get_health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
