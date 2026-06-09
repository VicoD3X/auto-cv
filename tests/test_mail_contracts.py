from autocv.domain import OpportunityType
from autocv.mail import MailDraftRequest, PublicMailDraftStub


def test_public_mail_draft_stub_is_unavailable_without_private_engine() -> None:
    request = MailDraftRequest(
        opportunity_type=OpportunityType.JOB,
        target_name="Airbus",
        role_or_mission="Data Scientist",
        context="Candidature avec CV et lettre.",
        attachment_paths=("CV.pdf", "Lettre.docx"),
    )

    draft = PublicMailDraftStub().create_draft(request)

    assert draft.available is False
    assert draft.source == "public_stub"
    assert draft.subject == ""
    assert draft.body == ""
