from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import blake2b
from pathlib import Path
import shutil
from uuid import uuid4

from autocv.documents.naming import (
    DocumentKind,
    build_document_filename,
    build_target_folder_path,
)
from autocv.documents.trash import DocumentTrashService, TrashReason


EDITABLE_EXTENSIONS = {".docx", ".pdf"}


class DocumentEditSessionStatus(StrEnum):
    OPEN = "open"
    KEPT = "kept"
    DELETED = "deleted"
    UNCHANGED_DELETED = "unchanged_deleted"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class DocumentEditSession:
    session_id: str
    source_path: Path
    working_copy_path: Path
    initial_hash: str
    initial_size: int
    initial_modified_ns: int
    target_folder: Path
    status: DocumentEditSessionStatus


class DocumentEditSessionService:
    def __init__(self, trash_service: DocumentTrashService | None = None) -> None:
        self.trash_service = trash_service or DocumentTrashService()

    def create_target_folder(
        self,
        *,
        result_dir: Path,
        target_name: str,
        role_or_mission: str,
        date: str,
    ) -> Path:
        target_folder = build_target_folder_path(
            result_dir,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date,
        )
        target_folder.mkdir(parents=True, exist_ok=True)
        return target_folder

    def create_working_copy(
        self,
        *,
        source_path: Path,
        result_dir: Path,
        kind: DocumentKind,
        target_name: str,
        role_or_mission: str,
        date: str,
    ) -> DocumentEditSession:
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        if source_path.suffix.lower() not in EDITABLE_EXTENSIONS:
            raise ValueError("Seuls les fichiers DOCX et PDF sont modifiables en V1.")

        target_folder = self.create_target_folder(
            result_dir=result_dir,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date,
        )
        filename = build_document_filename(
            kind=kind,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date,
            extension=source_path.suffix,
        )
        working_copy_path = _unique_path(target_folder / filename)
        shutil.copy2(source_path, working_copy_path)
        signature = _signature(working_copy_path)
        return DocumentEditSession(
            session_id=uuid4().hex,
            source_path=source_path,
            working_copy_path=working_copy_path,
            initial_hash=signature.file_hash,
            initial_size=signature.size,
            initial_modified_ns=signature.modified_ns,
            target_folder=target_folder,
            status=DocumentEditSessionStatus.OPEN,
        )

    def finalize_session(self, session: DocumentEditSession) -> DocumentEditSession:
        if not session.working_copy_path.exists():
            return replace(session, status=DocumentEditSessionStatus.DELETED)
        current = _signature(session.working_copy_path)
        if current.file_hash != session.initial_hash or current.size != session.initial_size:
            return replace(session, status=DocumentEditSessionStatus.KEPT)
        try:
            self._move_to_trash(session, TrashReason.UNCHANGED_EDIT)
        except OSError:
            return replace(session, status=DocumentEditSessionStatus.BLOCKED)
        return replace(session, status=DocumentEditSessionStatus.UNCHANGED_DELETED)

    def cancel_session(self, session: DocumentEditSession) -> DocumentEditSession:
        if not session.working_copy_path.exists():
            return replace(session, status=DocumentEditSessionStatus.DELETED)
        try:
            self._move_to_trash(session, TrashReason.CANCELED_EDIT)
        except OSError:
            return replace(session, status=DocumentEditSessionStatus.BLOCKED)
        return replace(session, status=DocumentEditSessionStatus.DELETED)

    def _move_to_trash(self, session: DocumentEditSession, reason: TrashReason) -> None:
        self.trash_service.move_to_trash(
            path=session.working_copy_path,
            result_dir=session.target_folder.parent,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class _FileSignature:
    file_hash: str
    size: int
    modified_ns: int


def _signature(path: Path) -> _FileSignature:
    stat = path.stat()
    hasher = blake2b(digest_size=16)
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return _FileSignature(
        file_hash=hasher.hexdigest(),
        size=stat.st_size,
        modified_ns=stat.st_mtime_ns,
    )


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
