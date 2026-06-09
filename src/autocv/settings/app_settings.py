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
    generic_cv_filename: str
    generic_cover_letter_filename: str
    github_owner: str
    github_project_sync_enabled: bool
    project_context_cache_dir: Path

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
            generic_cv_filename="CV_Victor_Aubry_Data_Scientist_pdf.pdf",
            generic_cover_letter_filename="Lettre_motivation_Victor_Aubry.docx",
            github_owner="VicoD3X",
            github_project_sync_enabled=False,
            project_context_cache_dir=data_dir / "project_context",
        )
