from autocv.domain import (
    ApplicationRecord,
    ApplicationStatus,
    FreelanceOpportunity,
    JobOffer,
    OpportunityType,
)
from autocv.infrastructure.database import LocalDatabase


class JobOfferRepository:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database

    def add(self, offer: JobOffer) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO job_offers (
                    id, company, title, url, location, description, notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    offer.id,
                    offer.company,
                    offer.title,
                    offer.url,
                    offer.location,
                    offer.description,
                    offer.notes,
                    offer.created_at,
                ),
            )

    def get(self, offer_id: str) -> JobOffer | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM job_offers WHERE id = ?",
                (offer_id,),
            ).fetchone()
        return _job_offer_from_row(row) if row else None

    def list_all(self) -> list[JobOffer]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM job_offers ORDER BY created_at DESC",
            ).fetchall()
        return [_job_offer_from_row(row) for row in rows]


class FreelanceOpportunityRepository:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database

    def add(self, opportunity: FreelanceOpportunity) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO freelance_opportunities (
                    id, client, mission_type, need, url, budget, notes, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity.id,
                    opportunity.client,
                    opportunity.mission_type,
                    opportunity.need,
                    opportunity.url,
                    opportunity.budget,
                    opportunity.notes,
                    opportunity.status.value,
                    opportunity.created_at,
                ),
            )

    def get(self, opportunity_id: str) -> FreelanceOpportunity | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM freelance_opportunities WHERE id = ?",
                (opportunity_id,),
            ).fetchone()
        return _freelance_opportunity_from_row(row) if row else None

    def list_all(self) -> list[FreelanceOpportunity]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM freelance_opportunities ORDER BY created_at DESC",
            ).fetchall()
        return [_freelance_opportunity_from_row(row) for row in rows]


class ApplicationRecordRepository:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database

    def add(self, record: ApplicationRecord) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO application_records (
                    id, opportunity_type, opportunity_id, status, cv_path,
                    cv_output_path, cover_letter_source_path, cover_letter_output_path, export_dir,
                    email_subject, email_body, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.opportunity_type.value,
                    record.opportunity_id,
                    record.status.value,
                    record.cv_path,
                    record.cv_output_path,
                    record.cover_letter_source_path,
                    record.cover_letter_output_path,
                    record.export_dir,
                    record.email_subject,
                    record.email_body,
                    record.notes,
                    record.created_at,
                    record.updated_at,
                ),
            )

    def get(self, record_id: str) -> ApplicationRecord | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM application_records WHERE id = ?",
                (record_id,),
            ).fetchone()
        return _application_record_from_row(row) if row else None

    def list_all(self) -> list[ApplicationRecord]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM application_records ORDER BY created_at DESC",
            ).fetchall()
        return [_application_record_from_row(row) for row in rows]


def _job_offer_from_row(row) -> JobOffer:
    return JobOffer(
        id=row["id"],
        company=row["company"],
        title=row["title"],
        url=row["url"],
        location=row["location"],
        description=row["description"],
        notes=row["notes"],
        created_at=row["created_at"],
    )


def _freelance_opportunity_from_row(row) -> FreelanceOpportunity:
    return FreelanceOpportunity(
        id=row["id"],
        client=row["client"],
        mission_type=row["mission_type"],
        need=row["need"],
        url=row["url"],
        budget=row["budget"],
        notes=row["notes"],
        status=ApplicationStatus(row["status"]),
        created_at=row["created_at"],
    )


def _application_record_from_row(row) -> ApplicationRecord:
    return ApplicationRecord(
        id=row["id"],
        opportunity_type=OpportunityType(row["opportunity_type"]),
        opportunity_id=row["opportunity_id"],
        status=ApplicationStatus(row["status"]),
        cv_path=row["cv_path"],
        cv_output_path=row["cv_output_path"],
        cover_letter_source_path=row["cover_letter_source_path"],
        cover_letter_output_path=row["cover_letter_output_path"],
        export_dir=row["export_dir"],
        email_subject=row["email_subject"],
        email_body=row["email_body"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
