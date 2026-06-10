from pathlib import Path

from autocv.documents.naming import (
    DocumentKind,
    build_document_filename,
    build_result_path,
    build_target_folder_name,
    build_target_folder_path,
)


def test_smart_document_filename_contains_kind_target_role_and_date() -> None:
    filename = build_document_filename(
        kind=DocumentKind.COVER_LETTER,
        target_name="Airbus Defence & Space",
        role_or_mission="Data Scientist Junior",
        date="2026-06-09",
        extension=".docx",
    )

    assert filename == "Lettre_Motivation_Airbus_Defence_Space_Data_Scientist_Junior_2026_06_09.docx"


def test_result_path_targets_configured_result_directory() -> None:
    path = build_result_path(Path("Result"), "CV_Airbus.pdf")

    assert path == Path("Result") / "CV_Airbus.pdf"


def test_target_folder_name_uses_target_role_and_date() -> None:
    folder_name = build_target_folder_name(
        target_name="Airbus Defence & Space",
        role_or_mission="Data Scientist Junior",
        date="2026-06-09",
    )
    path = build_target_folder_path(
        Path("Result"),
        target_name="Airbus Defence & Space",
        role_or_mission="Data Scientist Junior",
        date="2026-06-09",
    )

    assert folder_name == "Airbus_Defence_Space_Data_Scientist_Junior_2026_06_09"
    assert path == Path("Result") / folder_name
