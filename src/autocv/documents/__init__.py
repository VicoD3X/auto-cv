"""Document import, export, and attachment bundle helpers."""

from autocv.documents.naming import DocumentKind, SmartDocumentName, build_document_filename
from autocv.documents.cover_letter_writer import CoverLetterDocxWriter, CoverLetterWriteRequest
from autocv.documents.edit_session import (
    DocumentEditSession,
    DocumentEditSessionService,
    DocumentEditSessionStatus,
)
from autocv.documents.result_workspace import copy_to_result
from autocv.documents.scanner import DocumentScanner, ScannedDocument
from autocv.documents.source import DocumentSource
from autocv.documents.trash import DocumentTrashService, TrashEntry, TrashReason

__all__ = [
    "CoverLetterDocxWriter",
    "CoverLetterWriteRequest",
    "DocumentEditSession",
    "DocumentEditSessionService",
    "DocumentEditSessionStatus",
    "DocumentScanner",
    "DocumentTrashService",
    "DocumentKind",
    "DocumentSource",
    "ScannedDocument",
    "SmartDocumentName",
    "TrashEntry",
    "TrashReason",
    "build_document_filename",
    "copy_to_result",
]
