from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any


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
    selected_cv_path: Path | None
    selected_cover_letter_path: Path | None
    generic_cv_filename: str
    generic_cover_letter_filename: str
    github_owner: str
    github_project_sync_enabled: bool
    project_context_cache_dir: Path
    local_ai_enabled: bool
    local_ai_model_repo: str
    local_ai_model_name: str
    local_ai_default_quantization: str
    local_ai_quality_quantization: str
    local_ai_runner: str
    local_ai_base_url: str

    @classmethod
    def defaults(cls) -> "AppSettings":
        data_dir = default_data_dir()
        document_source_dir = Path.home() / "Desktop" / "GENERIQUE PRO"
        return cls(
            app_name="Auto-CV",
            data_dir=data_dir,
            default_mode="offline",
            primary_platform="windows-pc",
            ipad_companion_enabled=False,
            repository_language="en-US",
            user_interface_language="fr-FR",
            generated_content_language="fr-FR",
            document_source_dir=document_source_dir,
            result_dir=result_dir_for(document_source_dir),
            selected_cv_path=document_source_dir / "CV_Victor_Aubry_Data_Scientist_pdf.pdf",
            selected_cover_letter_path=document_source_dir / "Lettre_motivation_Victor_Aubry.docx",
            generic_cv_filename="CV_Victor_Aubry_Data_Scientist_pdf.pdf",
            generic_cover_letter_filename="Lettre_motivation_Victor_Aubry.docx",
            github_owner="VicoD3X",
            github_project_sync_enabled=False,
            project_context_cache_dir=data_dir / "project_context",
            local_ai_enabled=False,
            local_ai_model_repo="Qwen/Qwen3-14B-GGUF",
            local_ai_model_name="Qwen3-14B",
            local_ai_default_quantization="Q4_K_M",
            local_ai_quality_quantization="Q5_K_M",
            local_ai_runner="llama.cpp",
            local_ai_base_url="http://127.0.0.1:8080/v1",
        )

    @classmethod
    def load(cls) -> "AppSettings":
        return SettingsManager().load()


def default_data_dir() -> Path:
    return Path.home() / ".autocv"


def result_dir_for(document_source_dir: Path) -> Path:
    return document_source_dir / "Auto-CV" / "Result"


class SettingsManager:
    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path or default_data_dir() / "settings.json"

    def load(self) -> AppSettings:
        defaults = _defaults_for_settings_path(self.settings_path)
        if not self.settings_path.exists():
            return defaults

        data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        document_source_dir = Path(data.get("document_source_dir", defaults.document_source_dir))
        selected_cv_path = _optional_path(data.get("selected_cv_path"))
        selected_cover_letter_path = _optional_path(data.get("selected_cover_letter_path"))

        return AppSettings(
            app_name=defaults.app_name,
            data_dir=defaults.data_dir,
            default_mode=defaults.default_mode,
            primary_platform=defaults.primary_platform,
            ipad_companion_enabled=defaults.ipad_companion_enabled,
            repository_language=defaults.repository_language,
            user_interface_language=defaults.user_interface_language,
            generated_content_language=defaults.generated_content_language,
            document_source_dir=document_source_dir,
            result_dir=result_dir_for(document_source_dir),
            selected_cv_path=selected_cv_path or document_source_dir / defaults.generic_cv_filename,
            selected_cover_letter_path=(
                selected_cover_letter_path
                or document_source_dir / defaults.generic_cover_letter_filename
            ),
            generic_cv_filename=defaults.generic_cv_filename,
            generic_cover_letter_filename=defaults.generic_cover_letter_filename,
            github_owner=data.get("github_owner", defaults.github_owner),
            github_project_sync_enabled=bool(
                data.get("github_project_sync_enabled", defaults.github_project_sync_enabled)
            ),
            project_context_cache_dir=defaults.project_context_cache_dir,
            local_ai_enabled=bool(data.get("local_ai_enabled", defaults.local_ai_enabled)),
            local_ai_model_repo=defaults.local_ai_model_repo,
            local_ai_model_name=defaults.local_ai_model_name,
            local_ai_default_quantization=defaults.local_ai_default_quantization,
            local_ai_quality_quantization=defaults.local_ai_quality_quantization,
            local_ai_runner=defaults.local_ai_runner,
            local_ai_base_url=data.get("local_ai_base_url", defaults.local_ai_base_url),
        )

    def save(self, settings: AppSettings) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "document_source_dir": str(settings.document_source_dir),
            "selected_cv_path": _path_to_json(settings.selected_cv_path),
            "selected_cover_letter_path": _path_to_json(settings.selected_cover_letter_path),
            "github_owner": settings.github_owner,
            "github_project_sync_enabled": settings.github_project_sync_enabled,
            "local_ai_enabled": settings.local_ai_enabled,
            "local_ai_base_url": settings.local_ai_base_url,
        }
        self.settings_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def update_document_source_dir(self, settings: AppSettings, path: Path) -> AppSettings:
        updated = replace(
            settings,
            document_source_dir=path,
            result_dir=result_dir_for(path),
            selected_cv_path=None,
            selected_cover_letter_path=None,
        )
        self.save(updated)
        return self.load()

    def update_selected_documents(
        self,
        settings: AppSettings,
        *,
        selected_cv_path: Path | None = None,
        selected_cover_letter_path: Path | None = None,
    ) -> AppSettings:
        updated = replace(
            settings,
            selected_cv_path=selected_cv_path or settings.selected_cv_path,
            selected_cover_letter_path=(
                selected_cover_letter_path or settings.selected_cover_letter_path
            ),
            result_dir=result_dir_for(settings.document_source_dir),
        )
        self.save(updated)
        return self.load()

    def update_github_owner(self, settings: AppSettings, owner: str) -> AppSettings:
        updated = replace(settings, github_owner=owner)
        self.save(updated)
        return self.load()

    def update_local_ai_base_url(self, settings: AppSettings, base_url: str) -> AppSettings:
        updated = replace(settings, local_ai_base_url=base_url)
        self.save(updated)
        return self.load()


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _path_to_json(path: Path | None) -> str:
    return str(path) if path else ""


def _defaults_for_settings_path(settings_path: Path) -> AppSettings:
    defaults = AppSettings.defaults()
    data_dir = settings_path.parent
    return replace(
        defaults,
        data_dir=data_dir,
        project_context_cache_dir=data_dir / "project_context",
    )
