from dataclasses import dataclass

from autocv.domain.status import OpportunityType


@dataclass(frozen=True, slots=True)
class MailDraftRequest:
    opportunity_type: OpportunityType
    target_name: str
    role_or_mission: str
    context: str
    attachment_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MailDraft:
    subject: str
    body: str
    source: str
    available: bool

