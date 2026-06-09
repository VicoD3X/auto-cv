from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EngineRequest:
    task: str
    content: str
    context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineResponse:
    text: str
    source: str
    available: bool


class AutoCvEngine(Protocol):
    def generate(self, request: EngineRequest) -> EngineResponse:
        """Generate a response for an Auto-CV task."""

