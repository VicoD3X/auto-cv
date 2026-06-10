from autocv.domain import (
    ApplicationRecord,
    ApplicationStatus,
    FreelanceOpportunity,
    JobOffer,
    OpportunityType,
)
from autocv.infrastructure import (
    ApplicationRecordRepository,
    FreelanceOpportunityRepository,
    JobOfferRepository,
    LocalDatabase,
)


def test_repositories_persist_v1_entities(tmp_path) -> None:
    database = LocalDatabase(tmp_path / "autocv.sqlite")
    database.initialize()

    job_offers = JobOfferRepository(database)
    freelance_opportunities = FreelanceOpportunityRepository(database)
    applications = ApplicationRecordRepository(database)

    offer = JobOffer.create(company="Airbus", title="Data Scientist")
    mission = FreelanceOpportunity.create(
        client="Client test",
        mission_type="Dashboard",
        need="Créer un suivi KPI",
    )
    record = ApplicationRecord.create(
        opportunity_type=OpportunityType.JOB,
        opportunity_id=offer.id,
        cv_path="cv.pdf",
        cv_output_path="result/cv.pdf",
        cover_letter_source_path="lettre.docx",
    )
    freelance_record = ApplicationRecord.create(
        opportunity_type=OpportunityType.FREELANCE,
        opportunity_id=mission.id,
        cv_path="cv.pdf",
        cv_output_path="result/cv-freelance.pdf",
        cover_letter_source_path="lettre.docx",
    )

    job_offers.add(offer)
    freelance_opportunities.add(mission)
    applications.add(record)
    applications.add(freelance_record)

    assert job_offers.get(offer.id) == offer
    assert freelance_opportunities.get(mission.id) == mission
    assert applications.get(record.id) == record
    assert job_offers.list_all() == [offer]
    assert freelance_opportunities.list_all() == [mission]
    assert applications.list_jobs() == [record]
    assert applications.list_freelance() == [freelance_record]

    applications.update_status(record.id, ApplicationStatus.SENT)
    assert applications.get(record.id).status == ApplicationStatus.SENT

    applications.delete(record.id)
    assert applications.get(record.id) is None
