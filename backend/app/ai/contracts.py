from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderUnavailable(Exception):
    pass


class ProviderTimeout(Exception):
    pass


class ProviderRateLimited(Exception):
    pass


class InvalidProviderResponse(Exception):
    pass


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    model: str | None
    mock: bool
    available: bool
    local: bool


class Rewrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    proposed: str = Field(min_length=1, max_length=10_000)
    explanation: str = Field(min_length=1, max_length=500)


class WritingProvider(Protocol):
    def status(self) -> ProviderStatus: ...
    def rewrite_summary(self, text: str) -> Rewrite: ...


class EmbeddingProvider(Protocol):
    def status(self) -> ProviderStatus: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...
