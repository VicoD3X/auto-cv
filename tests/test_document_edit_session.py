from datetime import UTC, datetime, timedelta

import pytest

from autocv.documents import (
    DocumentEditSessionService,
    DocumentEditSessionStatus,
    DocumentTrashService,
    DocumentKind,
    TrashEntry,
    TrashReason,
)


def test_create_working_copy_uses_target_folder_and_template_name(tmp_path) -> None:
    source = tmp_path / "source" / "lettre.docx"
    source.parent.mkdir()
    source.write_text("Lettre source", encoding="utf-8")
    result_dir = tmp_path / "Result"

    session = DocumentEditSessionService().create_working_copy(
        source_path=source,
        result_dir=result_dir,
        kind=DocumentKind.COVER_LETTER,
        target_name="Airbus Defence",
        role_or_mission="Data Scientist",
        date="2026-06-11",
    )

    assert session.status == DocumentEditSessionStatus.OPEN
    assert session.source_path == source
    assert session.target_folder == result_dir / "Airbus_Defence_Data_Scientist_2026_06_11"
    assert session.working_copy_path == (
        session.target_folder / "Lettre_Motivation_Airbus_Defence_Data_Scientist_2026_06_11.docx"
    )
    assert source.read_text(encoding="utf-8") == "Lettre source"
    assert session.working_copy_path.read_text(encoding="utf-8") == "Lettre source"


def test_finalize_session_keeps_modified_copy_and_preserves_source(tmp_path) -> None:
    source = tmp_path / "cv.pdf"
    source.write_text("CV source", encoding="utf-8")
    service = DocumentEditSessionService()
    session = service.create_working_copy(
        source_path=source,
        result_dir=tmp_path / "Result",
        kind=DocumentKind.CV,
        target_name="Safran",
        role_or_mission="Data Analyst",
        date="2026-06-11",
    )

    session.working_copy_path.write_text("CV modifie", encoding="utf-8")
    finalized = service.finalize_session(session)

    assert finalized.status == DocumentEditSessionStatus.KEPT
    assert finalized.working_copy_path.exists()
    assert finalized.working_copy_path.read_text(encoding="utf-8") == "CV modifie"
    assert source.read_text(encoding="utf-8") == "CV source"


def test_finalize_session_deletes_unchanged_copy(tmp_path) -> None:
    source = tmp_path / "lettre.docx"
    source.write_text("Lettre", encoding="utf-8")
    service = DocumentEditSessionService()
    result_dir = tmp_path / "Result"
    session = service.create_working_copy(
        source_path=source,
        result_dir=result_dir,
        kind=DocumentKind.COVER_LETTER,
        target_name="Dassault",
        role_or_mission="Junior Data Scientist",
        date="2026-06-11",
    )

    finalized = service.finalize_session(session)

    assert finalized.status == DocumentEditSessionStatus.UNCHANGED_DELETED
    assert not session.working_copy_path.exists()
    trash_entries = service.trash_service.list_entries(result_dir)
    assert len(trash_entries) == 1
    assert trash_entries[0].reason.value == "unchanged_edit"
    assert trash_entries[0].trash_path.read_text(encoding="utf-8") == "Lettre"
    assert source.read_text(encoding="utf-8") == "Lettre"


def test_cancel_session_deletes_copy_and_preserves_source(tmp_path) -> None:
    source = tmp_path / "lettre.docx"
    source.write_text("Lettre", encoding="utf-8")
    service = DocumentEditSessionService()
    result_dir = tmp_path / "Result"
    session = service.create_working_copy(
        source_path=source,
        result_dir=result_dir,
        kind=DocumentKind.COVER_LETTER,
        target_name="Thales",
        role_or_mission="ML Engineer",
        date="2026-06-11",
    )

    cancelled = service.cancel_session(session)

    assert cancelled.status == DocumentEditSessionStatus.DELETED
    assert not session.working_copy_path.exists()
    trash_entries = service.trash_service.list_entries(result_dir)
    assert len(trash_entries) == 1
    assert trash_entries[0].reason.value == "canceled_edit"
    assert trash_entries[0].trash_path.read_text(encoding="utf-8") == "Lettre"
    assert source.read_text(encoding="utf-8") == "Lettre"


def test_create_working_copy_rejects_unsupported_extensions(tmp_path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("notes", encoding="utf-8")

    with pytest.raises(ValueError):
        DocumentEditSessionService().create_working_copy(
            source_path=source,
            result_dir=tmp_path / "Result",
            kind=DocumentKind.NOTES,
            target_name="Target",
            role_or_mission="Role",
            date="2026-06-11",
        )


def test_trash_service_restores_and_deletes_entries(tmp_path) -> None:
    result_dir = tmp_path / "Result"
    original = result_dir / "Airbus_Data_2026_06_11" / "lettre.docx"
    original.parent.mkdir(parents=True)
    original.write_text("Lettre", encoding="utf-8")
    service = DocumentTrashService()

    entry = service.move_to_trash(
        path=original,
        result_dir=result_dir,
        reason=TrashReason.OBSOLETE,
    )

    assert not original.exists()
    assert entry.trash_path.exists()
    assert service.list_entries(result_dir) == [entry]

    restored = service.restore(result_dir=result_dir, entry_id=entry.entry_id)

    assert restored == original
    assert restored.read_text(encoding="utf-8") == "Lettre"
    assert service.list_entries(result_dir) == []

    second_entry = service.move_to_trash(
        path=restored,
        result_dir=result_dir,
        reason=TrashReason.CANCELED_EDIT,
    )
    service.delete_permanently(result_dir=result_dir, entry_id=second_entry.entry_id)

    assert service.list_entries(result_dir) == []
    assert not second_entry.trash_path.exists()


def test_trash_service_purges_entries_after_30_days(tmp_path) -> None:
    result_dir = tmp_path / "Result"
    service = DocumentTrashService()
    old_file = result_dir / "old.docx"
    fresh_file = result_dir / "fresh.docx"
    result_dir.mkdir()
    old_file.write_text("old", encoding="utf-8")
    fresh_file.write_text("fresh", encoding="utf-8")
    old_entry = service.move_to_trash(
        path=old_file,
        result_dir=result_dir,
        reason=TrashReason.OBSOLETE,
    )
    fresh_entry = service.move_to_trash(
        path=fresh_file,
        result_dir=result_dir,
        reason=TrashReason.CANCELED_EDIT,
    )
    now = datetime.now(UTC)
    old_entry = _with_deleted_at(old_entry, now - timedelta(days=31))
    fresh_entry = _with_deleted_at(fresh_entry, now - timedelta(days=2))
    service._save_manifest(result_dir, [old_entry, fresh_entry])

    expired = service.purge_expired(result_dir, now=now)

    assert expired == [old_entry]
    assert not old_entry.trash_path.exists()
    assert fresh_entry.trash_path.exists()
    assert service.list_entries(result_dir) == [fresh_entry]


def test_cancel_session_reports_blocked_when_file_is_locked(tmp_path, monkeypatch) -> None:
    source = tmp_path / "lettre.docx"
    source.write_text("Lettre", encoding="utf-8")
    service = DocumentEditSessionService()
    session = service.create_working_copy(
        source_path=source,
        result_dir=tmp_path / "Result",
        kind=DocumentKind.COVER_LETTER,
        target_name="Target",
        role_or_mission="Role",
        date="2026-06-11",
    )

    def raise_permission_error(**kwargs) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr(service.trash_service, "move_to_trash", raise_permission_error)

    cancelled = service.cancel_session(session)

    assert cancelled.status == DocumentEditSessionStatus.BLOCKED
    assert session.working_copy_path.exists()


def _with_deleted_at(entry: TrashEntry, deleted_at: datetime) -> TrashEntry:
    return TrashEntry(
        entry_id=entry.entry_id,
        original_path=entry.original_path,
        trash_path=entry.trash_path,
        reason=entry.reason,
        deleted_at=deleted_at.isoformat(timespec="seconds"),
        size=entry.size,
    )
