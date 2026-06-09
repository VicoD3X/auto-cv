"""Pure business concepts live here."""

from autocv.domain.entities import ApplicationRecord, FreelanceOpportunity, JobOffer
from autocv.domain.status import ApplicationStatus, OpportunityType

__all__ = [
    "ApplicationRecord",
    "ApplicationStatus",
    "FreelanceOpportunity",
    "JobOffer",
    "OpportunityType",
]

