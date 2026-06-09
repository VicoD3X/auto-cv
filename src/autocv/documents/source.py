from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DocumentSource:
    directory: Path
    cv_filename: str
    cover_letter_filename: str

    @property
    def cv_path(self) -> Path:
        return self.directory / self.cv_filename

    @property
    def cover_letter_path(self) -> Path:
        return self.directory / self.cover_letter_filename

    def exists(self) -> bool:
        return self.directory.exists() and self.cv_path.exists() and self.cover_letter_path.exists()

