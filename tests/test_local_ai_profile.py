from autocv.ai import (
    LocalAiRequest,
    LocalAiRunner,
    LocalModelQuantization,
    PublicLocalAiStub,
    QWEN3_14B_Q4_PROFILE,
)


def test_qwen3_14b_profile_defaults_to_q4_with_q5_quality_option() -> None:
    profile = QWEN3_14B_Q4_PROFILE

    assert profile.name == "Qwen3-14B"
    assert profile.repo_id == "Qwen/Qwen3-14B-GGUF"
    assert profile.default_quantization == LocalModelQuantization.Q4_K_M
    assert profile.quality_quantization == LocalModelQuantization.Q5_K_M
    assert profile.runner == LocalAiRunner.LLAMA_CPP
    assert profile.default_model_ref == "Qwen/Qwen3-14B-GGUF:Q4_K_M"
    assert profile.quality_model_ref == "Qwen/Qwen3-14B-GGUF:Q5_K_M"
    assert profile.thinking_enabled_by_default is False


def test_public_local_ai_stub_keeps_private_runner_absent() -> None:
    request = LocalAiRequest(
        system_prompt="Tu adaptes une lettre.",
        user_prompt="Offre Data Scientist",
        task="cover_letter_adaptation",
    )

    response = PublicLocalAiStub().generate(request)

    assert response.available is False
    assert response.model == "Qwen/Qwen3-14B-GGUF:Q4_K_M"
    assert response.source == "public_stub"
