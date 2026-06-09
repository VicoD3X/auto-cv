from pathlib import Path

from autocv.documents.source import DocumentSource


def test_document_source_resolves_expected_files() -> None:
    source = DocumentSource(
        directory=Path("GENERIQUE PRO"),
        cv_filename="cv.pdf",
        cover_letter_filename="lettre.docx",
    )

    assert source.cv_path == Path("GENERIQUE PRO") / "cv.pdf"
    assert source.cover_letter_path == Path("GENERIQUE PRO") / "lettre.docx"

