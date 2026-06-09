from dataclasses import dataclass, field
from typing import Protocol

from autocv.ai.model_profile import LocalModelProfile, QWEN3_14B_Q4_PROFILE


@dataclass(frozen=True, slots=True)
class LocalAiRequest:
    system_prompt: str
    user_prompt: str
    task: str
    context: dict[str, str] = field(default_factory=dict)
    max_tokens: int = 1400
    temperature: float = 0.7
    top_p: float = 0.8
    thinking_enabled: bool = False


@dataclass(frozen=True, slots=True)
class LocalAiResponse:
    text: str
    model: str
    source: str
    available: bool


class LocalAiRunnerClient(Protocol):
    profile: LocalModelProfile

    def generate(self, request: LocalAiRequest) -> LocalAiResponse:
        """Generate text from the configured local model."""


class PublicLocalAiStub:
    profile = QWEN3_14B_Q4_PROFILE

    def generate(self, request: LocalAiRequest) -> LocalAiResponse:
        return LocalAiResponse(
            text="",
            model=self.profile.default_model_ref,
            source="public_stub",
            available=False,
        )

