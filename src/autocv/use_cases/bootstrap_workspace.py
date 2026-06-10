from dataclasses import dataclass
from pathlib import Path

from autocv.documents.source import DocumentSource
from autocv.infrastructure import LocalDatabase
from autocv.settings.app_settings import AppSettings


@dataclass(frozen=True, slots=True)
class WorkspaceBootstrapResult:
    data_dir: Path
    database_path: Path
    project_context_cache_dir: Path
    result_dir: Path
    document_source: DocumentSource
    document_source_ready: bool


class BootstrapWorkspace:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def run(self) -> WorkspaceBootstrapResult:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.project_context_cache_dir.mkdir(parents=True, exist_ok=True)
        self.settings.result_dir.mkdir(parents=True, exist_ok=True)

        database_path = self.settings.data_dir / "autocv.sqlite"
        database = LocalDatabase(database_path)
        database.initialize()

        document_source = DocumentSource.from_selected_paths(
            directory=self.settings.document_source_dir,
            cv_path=self.settings.selected_cv_path,
            cover_letter_path=self.settings.selected_cover_letter_path,
            fallback_cv_filename=self.settings.generic_cv_filename,
            fallback_cover_letter_filename=self.settings.generic_cover_letter_filename,
        )

        return WorkspaceBootstrapResult(
            data_dir=self.settings.data_dir,
            database_path=database_path,
            project_context_cache_dir=self.settings.project_context_cache_dir,
            result_dir=self.settings.result_dir,
            document_source=document_source,
            document_source_ready=document_source.exists(),
        )
