"""Technical adapters for storage, network, files, and AI services."""

from autocv.infrastructure.database import LocalDatabase
from autocv.infrastructure.repositories import (
    ApplicationRecordRepository,
    FreelanceOpportunityRepository,
    JobOfferRepository,
)

__all__ = [
    "ApplicationRecordRepository",
    "FreelanceOpportunityRepository",
    "JobOfferRepository",
    "LocalDatabase",
]

