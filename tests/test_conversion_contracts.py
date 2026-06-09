from pathlib import Path

from autocv.conversion import (
    ConversionRequest,
    DocumentFormat,
    PublicConversionStub,
)


def test_conversion_contract_supports_v1_formats() -> None:
    assert DocumentFormat.DOCX == "docx"
    assert DocumentFormat.PDF == "pdf"
    assert DocumentFormat.XLSX == "xlsx"


def test_public_conversion_stub_is_unavailable_without_private_engine() -> None:
    request = ConversionRequest(
        source_path=Path("source.docx"),
        output_path=Path("output.pdf"),
        source_format=DocumentFormat.DOCX,
        target_format=DocumentFormat.PDF,
    )

    response = PublicConversionStub().convert(request)

    assert response.available is False
    assert response.source == "public_stub"
    assert response.output_path == Path("output.pdf")
