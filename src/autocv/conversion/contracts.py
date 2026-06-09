from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DocumentFormat(StrEnum):
    DOCX = "docx"
    PDF = "pdf"
    XLSX = "xlsx"


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    source_path: Path
    output_path: Path
    source_format: DocumentFormat
    target_format: DocumentFormat


@dataclass(frozen=True, slots=True)
class ConversionResponse:
    output_path: Path
    source: str
    available: bool
    message: str

