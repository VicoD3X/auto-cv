from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS job_offers (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS freelance_opportunities (
    id TEXT PRIMARY KEY,
    client TEXT NOT NULL,
    mission_type TEXT NOT NULL,
    need TEXT NOT NULL,
    url TEXT NOT NULL,
    budget TEXT NOT NULL,
    notes TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS application_records (
    id TEXT PRIMARY KEY,
    opportunity_type TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    status TEXT NOT NULL,
    cv_path TEXT NOT NULL,
    cv_output_path TEXT NOT NULL,
    cover_letter_source_path TEXT NOT NULL,
    cover_letter_output_path TEXT NOT NULL,
    export_dir TEXT NOT NULL,
    email_subject TEXT NOT NULL,
    email_body TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_job_offers_created_at
    ON job_offers(created_at);

CREATE INDEX IF NOT EXISTS idx_freelance_opportunities_created_at
    ON freelance_opportunities(created_at);

CREATE INDEX IF NOT EXISTS idx_application_records_opportunity
    ON application_records(opportunity_type, opportunity_id);
"""


class LocalDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(SCHEMA)
            self._ensure_application_record_columns(connection)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _ensure_application_record_columns(connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(application_records)").fetchall()
        }
        if "cv_output_path" not in columns:
            connection.execute(
                "ALTER TABLE application_records ADD COLUMN cv_output_path TEXT NOT NULL DEFAULT ''"
            )
