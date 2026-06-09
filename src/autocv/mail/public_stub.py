from autocv.mail.contracts import MailDraft, MailDraftRequest


class PublicMailDraftStub:
    def create_draft(self, request: MailDraftRequest) -> MailDraft:
        return MailDraft(
            subject="",
            body="",
            source="public_stub",
            available=False,
        )

