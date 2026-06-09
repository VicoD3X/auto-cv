from dataclasses import replace

import pytest

from autocv.documents.source import DocumentSource
from autocv.domain import OpportunityType
from autocv.infrastructure import ApplicationRecordRepository, LocalDatabase
from autocv.settings.app_settings import AppSettings
from autocv.use_cases import BootstrapWorkspace, MissingDocumentSourceError, V1ApplicationService


def test_bootstrap_workspace_initializes_database_and_checks_document_source(tmp_path) -> None:
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    (source_dir / "cv.pdf").write_text("CV")
    (source_dir / "lettre.docx").write_text("Lettre")

    settings = replace(
        AppSettings.load(),
        data_dir=tmp_path / "data",
        project_context_cache_dir=tmp_path / "data" / "project_context",
        document_source_dir=source_dir,
        result_dir=tmp_path / "GENERIQUE PRO" / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
    )

    result = BootstrapWorkspace(settings).run()

    assert result.database_path.exists()
    assert result.project_context_cache_dir.exists()
    assert result.result_dir.exists()
    assert result.document_source_ready is True


def test_v1_service_creates_job_application_from_generic_documents(tmp_path) -> None:
    source = _ready_document_source(tmp_path)
    database = LocalDatabase(tmp_path / "autocv.sqlite")
    database.initialize()

    result_dir = tmp_path / "Result"
    service = V1ApplicationService(database, source, result_dir)
    draft = service.create_job_application(
        company="Airbus",
        title="Data Scientist",
        description="Python, ML, analyse de données",
    )

    applications = ApplicationRecordRepository(database).list_all()

    assert draft.offer.company == "Airbus"
    assert draft.application.opportunity_type == OpportunityType.JOB
    assert draft.application.cv_path == str(source.cv_path)
    date_slug = draft.offer.created_at[:10].replace("-", "_")
    assert draft.application.cv_output_path.endswith(f"CV_Airbus_Data_Scientist_{date_slug}.pdf")
    assert draft.application.cover_letter_output_path.endswith(
        f"Lettre_Motivation_Airbus_Data_Scientist_{date_slug}.docx"
    )
    assert draft.application.export_dir == str(result_dir)
    assert applications == [draft.application]


def test_v1_service_creates_freelance_opportunity_from_generic_documents(tmp_path) -> None:
    source = _ready_document_source(tmp_path)
    database = LocalDatabase(tmp_path / "autocv.sqlite")
    database.initialize()

    result_dir = tmp_path / "Result"
    service = V1ApplicationService(database, source, result_dir)
    draft = service.create_freelance_opportunity(
        client="Client test",
        mission_type="Dashboard",
        need="Suivi KPI pour activité commerciale",
    )

    assert draft.opportunity.client == "Client test"
    assert draft.application.opportunity_type == OpportunityType.FREELANCE
    assert draft.application.cover_letter_source_path == str(source.cover_letter_path)
    date_slug = draft.opportunity.created_at[:10].replace("-", "_")
    assert draft.application.cv_output_path.endswith(f"CV_Client_test_Dashboard_{date_slug}.pdf")
    assert draft.application.cover_letter_output_path.endswith(
        f"Proposition_Freelance_Client_test_Dashboard_{date_slug}.docx"
    )


def test_v1_service_requires_generic_documents(tmp_path) -> None:
    missing_source = DocumentSource(
        directory=tmp_path / "GENERIQUE PRO",
        cv_filename="cv.pdf",
        cover_letter_filename="lettre.docx",
    )
    database = LocalDatabase(tmp_path / "autocv.sqlite")
    database.initialize()

    service = V1ApplicationService(database, missing_source)

    with pytest.raises(MissingDocumentSourceError):
        service.create_job_application(company="Airbus", title="Data Scientist")


def _ready_document_source(tmp_path) -> DocumentSource:
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    (source_dir / "cv.pdf").write_text("CV")
    (source_dir / "lettre.docx").write_text("Lettre")
    return DocumentSource(
        directory=source_dir,
        cv_filename="cv.pdf",
        cover_letter_filename="lettre.docx",
    )
