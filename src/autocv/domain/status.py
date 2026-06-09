from enum import StrEnum


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SENT = "sent"
    FOLLOW_UP = "follow_up"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    ARCHIVED = "archived"


class OpportunityType(StrEnum):
    JOB = "job"
    FREELANCE = "freelance"

