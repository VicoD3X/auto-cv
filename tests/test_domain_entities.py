from autocv.domain import ApplicationRecord, ApplicationStatus, JobOffer, OpportunityType


def test_job_offer_creation_uses_draft_independent_identity() -> None:
    offer = JobOffer.create(company="Airbus", title="Data Scientist")

    assert offer.company == "Airbus"
    assert offer.title == "Data Scientist"
    assert offer.id
    assert offer.created_at


def test_application_record_links_to_opportunity_and_source_documents() -> None:
    record = ApplicationRecord.create(
        opportunity_type=OpportunityType.JOB,
        opportunity_id="offer-1",
        cv_path="cv.pdf",
        cv_output_path="result/cv.pdf",
        cover_letter_source_path="lettre.docx",
    )

    assert record.opportunity_type == OpportunityType.JOB
    assert record.status == ApplicationStatus.DRAFT
    assert record.cv_path == "cv.pdf"
    assert record.cv_output_path == "result/cv.pdf"
    assert record.cover_letter_source_path == "lettre.docx"
