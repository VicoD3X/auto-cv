from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
import unicodedata


class DocumentKind(StrEnum):
    CV = "CV"
    COVER_LETTER = "Lettre_Motivation"
    FREELANCE_PROPOSAL = "Proposition_Freelance"
    EMAIL_DRAFT = "Mail"
    NOTES = "Notes"


@dataclass(frozen=True, slots=True)
class SmartDocumentName:
    kind: DocumentKind
    target_name: str
    role_or_mission: str
    date: str
    extension: str

    def filename(self) -> str:
        parts = [
            self.kind.value,
            _slug(self.target_name),
            _slug(self.role_or_mission),
            _slug(self.date),
        ]
        clean_parts = [part for part in parts if part]
        extension = self.extension.lstrip(".").lower()
        return f"{'_'.join(clean_parts)}.{extension}"


def build_document_filename(
    *,
    kind: DocumentKind,
    target_name: str,
    role_or_mission: str,
    date: str,
    extension: str,
) -> str:
    return SmartDocumentName(
        kind=kind,
        target_name=target_name,
        role_or_mission=role_or_mission,
        date=date,
        extension=extension,
    ).filename()


def build_result_path(result_dir: Path, filename: str) -> Path:
    return result_dir / filename


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    clean_value = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value)
    return clean_value.strip("_")

