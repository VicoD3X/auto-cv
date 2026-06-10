from pathlib import Path

from autocv.conversion import ConversionRequest, DocumentFormat, LocalDocumentConverter
import autocv.conversion.local_converter as local_converter


def test_local_converter_uses_docx_to_pdf_adapter(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.docx"
    output = tmp_path / "output.pdf"
    source.write_text("docx")

    def fake_docx_to_pdf(source_path: Path, output_path: Path) -> None:
        assert source_path == source
        output_path.write_text("pdf")

    monkeypatch.setattr(local_converter, "_docx_to_pdf", fake_docx_to_pdf)

    response = LocalDocumentConverter().convert(
        ConversionRequest(
            source_path=source,
            output_path=output,
            source_format=DocumentFormat.DOCX,
            target_format=DocumentFormat.PDF,
        )
    )

    assert response.available is True
    assert output.read_text() == "pdf"


def test_local_converter_reports_unsupported_conversion(tmp_path) -> None:
    response = LocalDocumentConverter().convert(
        ConversionRequest(
            source_path=tmp_path / "source.xlsx",
            output_path=tmp_path / "output.docx",
            source_format=DocumentFormat.XLSX,
            target_format=DocumentFormat.DOCX,
        )
    )

    assert response.available is False
    assert response.source == "local_converter"


def test_local_converter_reports_word_unavailable_cleanly(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.docx"
    output = tmp_path / "output.pdf"
    source.write_text("docx")

    def fake_docx_to_pdf(source_path: Path, output_path: Path) -> None:
        raise ModuleNotFoundError("No module named 'win32com'")

    monkeypatch.setattr(local_converter, "_docx_to_pdf", fake_docx_to_pdf)

    response = LocalDocumentConverter().convert(
        ConversionRequest(
            source_path=source,
            output_path=output,
            source_format=DocumentFormat.DOCX,
            target_format=DocumentFormat.PDF,
        )
    )

    assert response.available is False
    assert "pywin32 ou Microsoft Word/Excel est indisponible" in response.message
