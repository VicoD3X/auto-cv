from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls"}


class DocumentLocation(StrEnum):
    SOURCE = "source"
    RESULT = "result"


class ScannedDocumentKind(StrEnum):
    CV = "cv"
    COVER_LETTER = "cover_letter"
    PDF = "pdf"
    DOCX = "docx"
    EXCEL = "excel"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ScannedDocument:
    path: Path
    relative_path: str
    extension: str
    location: DocumentLocation
    kind: ScannedDocumentKind
    selected_as_cv: bool = False
    selected_as_cover_letter: bool = False


class DocumentScanner:
    def __init__(
        self,
        *,
        source_dir: Path,
        result_dir: Path,
        selected_cv_path: Path | None = None,
        selected_cover_letter_path: Path | None = None,
    ) -> None:
        self.source_dir = source_dir
        self.result_dir = result_dir
        self.selected_cv_path = selected_cv_path
        self.selected_cover_letter_path = selected_cover_letter_path

    def scan(self) -> list[ScannedDocument]:
        if not self.source_dir.exists():
            return []

        documents: list[ScannedDocument] = []
        for path in sorted(self.source_dir.rglob("*"), key=lambda item: str(item).lower()):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
                continue
            if _is_relative_to(path, self.result_dir):
                continue

            documents.append(
                ScannedDocument(
                    path=path,
                    relative_path=_relative_display(path, self.source_dir),
                    extension=path.suffix.lower(),
                    location=DocumentLocation.SOURCE,
                    kind=_guess_kind(path),
                    selected_as_cv=_same_path(path, self.selected_cv_path),
                    selected_as_cover_letter=_same_path(path, self.selected_cover_letter_path),
                )
            )
        return documents


def _guess_kind(path: Path) -> ScannedDocumentKind:
    name = path.stem.lower()
    extension = path.suffix.lower()
    if "cv" in name:
        return ScannedDocumentKind.CV
    if "lettre" in name or "motivation" in name:
        return ScannedDocumentKind.COVER_LETTER
    if extension == ".pdf":
        return ScannedDocumentKind.PDF
    if extension == ".docx":
        return ScannedDocumentKind.DOCX
    if extension in {".xlsx", ".xls"}:
        return ScannedDocumentKind.EXCEL
    return ScannedDocumentKind.UNKNOWN


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _relative_display(path: Path, parent: Path) -> str:
    try:
        return str(path.relative_to(parent))
    except ValueError:
        return str(path)


def _same_path(left: Path, right: Path | None) -> bool:
    if right is None:
        return False
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right

