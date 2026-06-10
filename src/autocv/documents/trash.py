from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import json
from pathlib import Path
import shutil
from uuid import uuid4


class TrashReason(StrEnum):
    CANCELED_EDIT = "canceled_edit"
    UNCHANGED_EDIT = "unchanged_edit"
    OBSOLETE = "obsolete"


@dataclass(frozen=True, slots=True)
class TrashEntry:
    entry_id: str
    original_path: Path
    trash_path: Path
    reason: TrashReason
    deleted_at: str
    size: int


class DocumentTrashService:
    folder_name = "_PreSuppression"
    manifest_name = "manifest.json"
    retention_days = 30

    def list_entries(self, result_dir: Path) -> list[TrashEntry]:
        self.purge_expired(result_dir)
        entries = self._load_manifest(result_dir)
        return [entry for entry in entries if entry.trash_path.exists()]

    def purge_expired(self, result_dir: Path, *, now: datetime | None = None) -> list[TrashEntry]:
        entries = self._load_manifest(result_dir)
        if not entries:
            return []

        current_time = now or datetime.now(UTC)
        threshold = current_time - timedelta(days=self.retention_days)
        expired: list[TrashEntry] = []
        kept: list[TrashEntry] = []
        for entry in entries:
            deleted_at = _parse_datetime(entry.deleted_at)
            if deleted_at < threshold:
                expired.append(entry)
                if entry.trash_path.exists():
                    entry.trash_path.unlink()
            else:
                kept.append(entry)
        self._save_manifest(result_dir, kept)
        return expired

    def move_to_trash(
        self,
        *,
        path: Path,
        result_dir: Path,
        reason: TrashReason,
    ) -> TrashEntry:
        if not path.exists():
            raise FileNotFoundError(path)

        trash_dir = self.trash_dir(result_dir)
        trash_dir.mkdir(parents=True, exist_ok=True)
        entry_id = uuid4().hex
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        trash_path = _unique_path(trash_dir / f"{timestamp}_{entry_id[:8]}_{path.name}")
        size = path.stat().st_size
        shutil.move(str(path), str(trash_path))

        entry = TrashEntry(
            entry_id=entry_id,
            original_path=path,
            trash_path=trash_path,
            reason=reason,
            deleted_at=datetime.now(UTC).isoformat(timespec="seconds"),
            size=size,
        )
        entries = self._load_manifest(result_dir)
        entries.append(entry)
        self._save_manifest(result_dir, entries)
        return entry

    def restore(self, *, result_dir: Path, entry_id: str) -> Path:
        entries = self._load_manifest(result_dir)
        entry = _find_entry(entries, entry_id)
        if entry is None:
            raise FileNotFoundError(entry_id)
        if not entry.trash_path.exists():
            self._save_manifest(result_dir, [item for item in entries if item.entry_id != entry_id])
            raise FileNotFoundError(entry.trash_path)

        entry.original_path.parent.mkdir(parents=True, exist_ok=True)
        target_path = _unique_path(entry.original_path)
        shutil.move(str(entry.trash_path), str(target_path))
        self._save_manifest(result_dir, [item for item in entries if item.entry_id != entry_id])
        return target_path

    def delete_permanently(self, *, result_dir: Path, entry_id: str) -> None:
        entries = self._load_manifest(result_dir)
        entry = _find_entry(entries, entry_id)
        if entry is not None and entry.trash_path.exists():
            entry.trash_path.unlink()
        self._save_manifest(result_dir, [item for item in entries if item.entry_id != entry_id])

    def trash_dir(self, result_dir: Path) -> Path:
        return result_dir / self.folder_name

    def _manifest_path(self, result_dir: Path) -> Path:
        return self.trash_dir(result_dir) / self.manifest_name

    def _load_manifest(self, result_dir: Path) -> list[TrashEntry]:
        manifest_path = self._manifest_path(result_dir)
        if not manifest_path.exists():
            return []
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return [
            TrashEntry(
                entry_id=item["entry_id"],
                original_path=Path(item["original_path"]),
                trash_path=Path(item["trash_path"]),
                reason=TrashReason(item["reason"]),
                deleted_at=item["deleted_at"],
                size=int(item["size"]),
            )
            for item in data
        ]

    def _save_manifest(self, result_dir: Path, entries: list[TrashEntry]) -> None:
        trash_dir = self.trash_dir(result_dir)
        trash_dir.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "entry_id": entry.entry_id,
                "original_path": str(entry.original_path),
                "trash_path": str(entry.trash_path),
                "reason": entry.reason.value,
                "deleted_at": entry.deleted_at,
                "size": entry.size,
            }
            for entry in entries
        ]
        self._manifest_path(result_dir).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _find_entry(entries: list[TrashEntry], entry_id: str) -> TrashEntry | None:
    return next((entry for entry in entries if entry.entry_id == entry_id), None)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
