from dataclasses import dataclass

from autocv.documents.source import DocumentSource
from autocv.domain import ApplicationRecord, FreelanceOpportunity, JobOffer, OpportunityType
from autocv.infrastructure import (
    ApplicationRecordRepository,
    FreelanceOpportunityRepository,
    JobOfferRepository,
    LocalDatabase,
)


class MissingDocumentSourceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class JobApplicationDraft:
    offer: JobOffer
    application: ApplicationRecord


@dataclass(frozen=True, slots=True)
class FreelanceOpportunityDraft:
    opportunity: FreelanceOpportunity
    application: ApplicationRecord


class V1ApplicationService:
    def __init__(self, database: LocalDatabase, document_source: DocumentSource) -> None:
        self.document_source = document_source
        self.job_offers = JobOfferRepository(database)
        self.freelance_opportunities = FreelanceOpportunityRepository(database)
        self.applications = ApplicationRecordRepository(database)

    def create_job_application(
        self,
        *,
        company: str,
        title: str,
        url: str = "",
        location: str = "",
        description: str = "",
        notes: str = "",
    ) -> JobApplicationDraft:
        self._ensure_document_source_ready()

        offer = JobOffer.create(
            company=company,
            title=title,
            url=url,
            location=location,
            description=description,
            notes=notes,
        )
        application = ApplicationRecord.create(
            opportunity_type=OpportunityType.JOB,
            opportunity_id=offer.id,
            cv_path=str(self.document_source.cv_path),
            cover_letter_source_path=str(self.document_source.cover_letter_path),
        )

        self.job_offers.add(offer)
        self.applications.add(application)

        return JobApplicationDraft(offer=offer, application=application)

    def create_freelance_opportunity(
        self,
        *,
        client: str,
        mission_type: str,
        need: str,
        url: str = "",
        budget: str = "",
        notes: str = "",
    ) -> FreelanceOpportunityDraft:
        self._ensure_document_source_ready()

        opportunity = FreelanceOpportunity.create(
            client=client,
            mission_type=mission_type,
            need=need,
            url=url,
            budget=budget,
            notes=notes,
        )
        application = ApplicationRecord.create(
            opportunity_type=OpportunityType.FREELANCE,
            opportunity_id=opportunity.id,
            cv_path=str(self.document_source.cv_path),
            cover_letter_source_path=str(self.document_source.cover_letter_path),
        )

        self.freelance_opportunities.add(opportunity)
        self.applications.add(application)

        return FreelanceOpportunityDraft(opportunity=opportunity, application=application)

    def _ensure_document_source_ready(self) -> None:
        if not self.document_source.exists():
            raise MissingDocumentSourceError(
                "Le dossier GENERIQUE PRO doit contenir le CV et la lettre générique."
            )

