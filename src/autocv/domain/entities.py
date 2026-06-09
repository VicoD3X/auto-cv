from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from autocv.domain.status import ApplicationStatus, OpportunityType


def new_id() -> str:
    return uuid4().hex


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class JobOffer:
    id: str
    company: str
    title: str
    url: str
    location: str
    description: str
    notes: str
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        company: str,
        title: str,
        url: str = "",
        location: str = "",
        description: str = "",
        notes: str = "",
    ) -> "JobOffer":
        return cls(
            id=new_id(),
            company=company,
            title=title,
            url=url,
            location=location,
            description=description,
            notes=notes,
            created_at=now_utc_iso(),
        )


@dataclass(frozen=True, slots=True)
class FreelanceOpportunity:
    id: str
    client: str
    mission_type: str
    need: str
    url: str
    budget: str
    notes: str
    status: ApplicationStatus
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        client: str,
        mission_type: str,
        need: str,
        url: str = "",
        budget: str = "",
        notes: str = "",
        status: ApplicationStatus = ApplicationStatus.DRAFT,
    ) -> "FreelanceOpportunity":
        return cls(
            id=new_id(),
            client=client,
            mission_type=mission_type,
            need=need,
            url=url,
            budget=budget,
            notes=notes,
            status=status,
            created_at=now_utc_iso(),
        )


@dataclass(frozen=True, slots=True)
class ApplicationRecord:
    id: str
    opportunity_type: OpportunityType
    opportunity_id: str
    status: ApplicationStatus
    cv_path: str
    cover_letter_source_path: str
    cover_letter_output_path: str
    export_dir: str
    email_subject: str
    email_body: str
    notes: str
    created_at: str
    updated_at: str

    @classmethod
    def create(
        cls,
        *,
        opportunity_type: OpportunityType,
        opportunity_id: str,
        cv_path: str,
        cover_letter_source_path: str,
        cover_letter_output_path: str = "",
        export_dir: str = "",
        email_subject: str = "",
        email_body: str = "",
        notes: str = "",
        status: ApplicationStatus = ApplicationStatus.DRAFT,
    ) -> "ApplicationRecord":
        timestamp = now_utc_iso()
        return cls(
            id=new_id(),
            opportunity_type=opportunity_type,
            opportunity_id=opportunity_id,
            status=status,
            cv_path=cv_path,
            cover_letter_source_path=cover_letter_source_path,
            cover_letter_output_path=cover_letter_output_path,
            export_dir=export_dir,
            email_subject=email_subject,
            email_body=email_body,
            notes=notes,
            created_at=timestamp,
            updated_at=timestamp,
        )

