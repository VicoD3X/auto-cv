from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DocumentSource:
    directory: Path
    cv_filename: str
    cover_letter_filename: str
    cv_path_override: Path | None = None
    cover_letter_path_override: Path | None = None

    @property
    def cv_path(self) -> Path:
        if self.cv_path_override is not None:
            return self.cv_path_override
        return self.directory / self.cv_filename

    @property
    def cover_letter_path(self) -> Path:
        if self.cover_letter_path_override is not None:
            return self.cover_letter_path_override
        return self.directory / self.cover_letter_filename

    def exists(self) -> bool:
        return self.directory.exists() and self.cv_path.exists() and self.cover_letter_path.exists()

    @classmethod
    def from_selected_paths(
        cls,
        *,
        directory: Path,
        cv_path: Path | None,
        cover_letter_path: Path | None,
        fallback_cv_filename: str,
        fallback_cover_letter_filename: str,
    ) -> "DocumentSource":
        usable_cv_path = _usable_selected_path(cv_path, directory)
        usable_cover_letter_path = _usable_selected_path(cover_letter_path, directory)
        return cls(
            directory=directory,
            cv_filename=(usable_cv_path.name if usable_cv_path else fallback_cv_filename),
            cover_letter_filename=(
                usable_cover_letter_path.name
                if usable_cover_letter_path
                else fallback_cover_letter_filename
            ),
            cv_path_override=usable_cv_path,
            cover_letter_path_override=usable_cover_letter_path,
        )


def _usable_selected_path(path: Path | None, directory: Path) -> Path | None:
    if path is None or not path.exists():
        return None
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return None
    return path
