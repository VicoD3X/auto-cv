from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    app_name: str
    data_dir: Path
    default_mode: str
    primary_platform: str
    ipad_companion_enabled: bool
    repository_language: str
    user_interface_language: str
    generated_content_language: str
    document_source_dir: Path
    result_dir: Path
    generic_cv_filename: str
    generic_cover_letter_filename: str
    github_owner: str
    github_project_sync_enabled: bool
    project_context_cache_dir: Path
    local_ai_model_repo: str
    local_ai_model_name: str
    local_ai_default_quantization: str
    local_ai_quality_quantization: str
    local_ai_runner: str
    local_ai_base_url: str

    @classmethod
    def load(cls) -> "AppSettings":
        data_dir = Path.home() / ".autocv"
        return cls(
            app_name="Auto-CV",
            data_dir=data_dir,
            default_mode="offline",
            primary_platform="windows-pc",
            ipad_companion_enabled=False,
            repository_language="en-US",
            user_interface_language="fr-FR",
            generated_content_language="fr-FR",
            document_source_dir=Path.home() / "Desktop" / "GENERIQUE PRO",
            result_dir=Path.home() / "Desktop" / "GENERIQUE PRO" / "Auto-CV" / "Result",
            generic_cv_filename="CV_Victor_Aubry_Data_Scientist_pdf.pdf",
            generic_cover_letter_filename="Lettre_motivation_Victor_Aubry.docx",
            github_owner="VicoD3X",
            github_project_sync_enabled=False,
            project_context_cache_dir=data_dir / "project_context",
            local_ai_model_repo="Qwen/Qwen3-14B-GGUF",
            local_ai_model_name="Qwen3-14B",
            local_ai_default_quantization="Q4_K_M",
            local_ai_quality_quantization="Q5_K_M",
            local_ai_runner="llama.cpp",
            local_ai_base_url="http://127.0.0.1:8080/v1",
        )
