from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HIRESENSE_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="HireSense AI", min_length=1)
    app_version: str = Field(default="0.1.0", min_length=1)
    environment: str = Field(default="development", min_length=1)
    database_url: str = "sqlite:///" + (BACKEND_ROOT / ".local/data/hiresense.sqlite3").as_posix()
    database_echo: bool = False
    debug: bool = False
    development_identity_enabled: bool = False
    development_owner_id: UUID | None = None
    ai_provider: Literal["disabled", "mock", "ollama", "openai-compatible"] = "mock"
    local_ai_origin: str | None = None
    local_ai_model: str | None = Field(default=None, min_length=1, max_length=150, pattern=r"^[A-Za-z0-9][A-Za-z0-9_./:-]*$")
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @model_validator(mode="after")
    def validate_ai(self):
        if self.ai_provider in {"ollama", "openai-compatible"}:
            if self.local_ai_origin is None or self.local_ai_model is None:
                raise ValueError("Local AI requires an origin and a model.")
            from app.ai.local import validate_local_origin
            validate_local_origin(self.local_ai_origin)
        return self

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/") or any(
            char in value for char in ("?", "#", " ")
        ):
            raise ValueError("API prefix must start with / and have no trailing /, query or fragment")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        from urllib.parse import urlsplit

        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
        return origins
