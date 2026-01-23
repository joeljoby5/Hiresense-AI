import re

from app.ai.contracts import ProviderStatus, ProviderUnavailable, Rewrite


class DisabledProvider:
    def status(self) -> ProviderStatus:
        return ProviderStatus("disabled", None, False, False, True)

    def rewrite_summary(self, text: str) -> Rewrite:
        raise ProviderUnavailable()


class MockAIProvider:
    def status(self) -> ProviderStatus:
        return ProviderStatus("mock", "whitespace-1", True, True, True)

    def rewrite_summary(self, text: str) -> Rewrite:
        proposed = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines()).strip()
        return Rewrite(proposed=proposed, explanation="Deterministic formatting pass that preserves the original words.")
