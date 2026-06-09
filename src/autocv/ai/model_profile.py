from dataclasses import dataclass
from enum import StrEnum


class LocalModelQuantization(StrEnum):
    Q4_K_M = "Q4_K_M"
    Q5_K_M = "Q5_K_M"


class LocalAiRunner(StrEnum):
    LLAMA_CPP = "llama.cpp"


@dataclass(frozen=True, slots=True)
class LocalModelProfile:
    name: str
    repo_id: str
    default_quantization: LocalModelQuantization
    quality_quantization: LocalModelQuantization
    runner: LocalAiRunner
    base_url: str
    context_window_tokens: int
    thinking_enabled_by_default: bool

    @property
    def default_model_ref(self) -> str:
        return f"{self.repo_id}:{self.default_quantization.value}"

    @property
    def quality_model_ref(self) -> str:
        return f"{self.repo_id}:{self.quality_quantization.value}"


QWEN3_14B_Q4_PROFILE = LocalModelProfile(
    name="Qwen3-14B",
    repo_id="Qwen/Qwen3-14B-GGUF",
    default_quantization=LocalModelQuantization.Q4_K_M,
    quality_quantization=LocalModelQuantization.Q5_K_M,
    runner=LocalAiRunner.LLAMA_CPP,
    base_url="http://127.0.0.1:8080/v1",
    context_window_tokens=32768,
    thinking_enabled_by_default=False,
)

