from autocv.documents.scanner import DocumentScanner, ScannedDocumentKind


def test_document_scanner_finds_supported_documents_and_excludes_result(tmp_path) -> None:
    source_dir = tmp_path / "GENERIQUE PRO"
    result_dir = source_dir / "Auto-CV" / "Result"
    nested = source_dir / "nested"
    nested.mkdir(parents=True)
    result_dir.mkdir(parents=True)

    cv_path = source_dir / "cv.pdf"
    letter_path = nested / "lettre.docx"
    sheet_path = source_dir / "tracking.xlsx"
    ignored_result = result_dir / "generated.pdf"
    ignored_txt = source_dir / "notes.txt"
    cv_path.write_text("CV")
    letter_path.write_text("Lettre")
    sheet_path.write_text("xlsx")
    ignored_result.write_text("generated")
    ignored_txt.write_text("ignore")

    documents = DocumentScanner(
        source_dir=source_dir,
        result_dir=result_dir,
        selected_cv_path=cv_path,
        selected_cover_letter_path=letter_path,
    ).scan()

    paths = {document.path for document in documents}
    assert paths == {cv_path, letter_path, sheet_path}
    assert any(document.selected_as_cv for document in documents)
    assert any(document.selected_as_cover_letter for document in documents)
    assert next(document for document in documents if document.path == sheet_path).kind == ScannedDocumentKind.EXCEL
