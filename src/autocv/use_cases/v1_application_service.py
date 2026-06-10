from dataclasses import dataclass
from pathlib import Path

from autocv.documents.naming import (
    DocumentKind,
    build_document_filename,
    build_result_path,
    build_target_folder_path,
)
from autocv.documents.result_workspace import copy_to_result
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
    def __init__(
        self,
        database: LocalDatabase,
        document_source: DocumentSource,
        result_dir: Path | None = None,
    ) -> None:
        self.document_source = document_source
        self.result_dir = result_dir
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
        export_dir = self._build_target_folder(
            target_name=company,
            role_or_mission=title,
            date=offer.created_at[:10],
        )
        cv_output_path = self._build_output_path(
            kind=DocumentKind.CV,
            target_name=company,
            role_or_mission=title,
            date=offer.created_at[:10],
            extension=self.document_source.cv_path.suffix or "pdf",
            output_dir=export_dir,
        )
        cover_letter_output_path = self._build_output_path(
            kind=DocumentKind.COVER_LETTER,
            target_name=company,
            role_or_mission=title,
            date=offer.created_at[:10],
            extension=self.document_source.cover_letter_path.suffix or "docx",
            output_dir=export_dir,
        )
        self._copy_source_documents(cv_output_path, cover_letter_output_path)

        application = ApplicationRecord.create(
            opportunity_type=OpportunityType.JOB,
            opportunity_id=offer.id,
            cv_path=str(self.document_source.cv_path),
            cv_output_path=cv_output_path,
            cover_letter_source_path=str(self.document_source.cover_letter_path),
            cover_letter_output_path=cover_letter_output_path,
            export_dir=str(export_dir) if export_dir else "",
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
        export_dir = self._build_target_folder(
            target_name=client,
            role_or_mission=mission_type,
            date=opportunity.created_at[:10],
        )
        cv_output_path = self._build_output_path(
            kind=DocumentKind.CV,
            target_name=client,
            role_or_mission=mission_type,
            date=opportunity.created_at[:10],
            extension=self.document_source.cv_path.suffix or "pdf",
            output_dir=export_dir,
        )
        proposal_output_path = self._build_output_path(
            kind=DocumentKind.FREELANCE_PROPOSAL,
            target_name=client,
            role_or_mission=mission_type,
            date=opportunity.created_at[:10],
            extension=self.document_source.cover_letter_path.suffix or "docx",
            output_dir=export_dir,
        )
        self._copy_source_documents(cv_output_path, proposal_output_path)

        application = ApplicationRecord.create(
            opportunity_type=OpportunityType.FREELANCE,
            opportunity_id=opportunity.id,
            cv_path=str(self.document_source.cv_path),
            cv_output_path=cv_output_path,
            cover_letter_source_path=str(self.document_source.cover_letter_path),
            cover_letter_output_path=proposal_output_path,
            export_dir=str(export_dir) if export_dir else "",
        )

        self.freelance_opportunities.add(opportunity)
        self.applications.add(application)

        return FreelanceOpportunityDraft(opportunity=opportunity, application=application)

    def _ensure_document_source_ready(self) -> None:
        if not self.document_source.exists():
            raise MissingDocumentSourceError(
                "Le dossier GENERIQUE PRO doit contenir le CV et la lettre générique."
            )

    def _copy_source_documents(self, cv_output_path: str, cover_letter_output_path: str) -> None:
        if not self.result_dir:
            return
        if cv_output_path:
            copy_to_result(self.document_source.cv_path, Path(cv_output_path))
        if cover_letter_output_path:
            copy_to_result(self.document_source.cover_letter_path, Path(cover_letter_output_path))

    def _build_output_path(
        self,
        *,
        kind: DocumentKind,
        target_name: str,
        role_or_mission: str,
        date: str,
        extension: str,
        output_dir: Path | None = None,
    ) -> str:
        target_dir = output_dir or self.result_dir
        if target_dir is None:
            return ""

        clean_extension = extension.lstrip(".") or "txt"
        filename = build_document_filename(
            kind=kind,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date,
            extension=clean_extension,
        )
        return str(build_result_path(target_dir, filename))

    def _build_target_folder(
        self,
        *,
        target_name: str,
        role_or_mission: str,
        date: str,
    ) -> Path | None:
        if self.result_dir is None:
            return None
        folder = build_target_folder_path(
            self.result_dir,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date,
        )
        folder.mkdir(parents=True, exist_ok=True)
        return folder
