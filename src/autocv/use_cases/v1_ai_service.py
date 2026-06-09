from pathlib import Path

from autocv.documents.naming import DocumentKind, build_document_filename, build_result_path
from autocv.domain import ApplicationRecord, OpportunityType
from autocv.engine import AutoCvEngine, EngineRequest, EngineResponse, load_engine
from autocv.mail import MailDraft, MailDraftRequest


class V1AiService:
    def __init__(self, engine: AutoCvEngine | None = None) -> None:
        self.engine = engine or load_engine()

    def adapt_application_text(
        self,
        *,
        record: ApplicationRecord,
        target_name: str,
        role_or_mission: str,
        context: str,
    ) -> EngineResponse:
        task = (
            "freelance_proposal"
            if record.opportunity_type == OpportunityType.FREELANCE
            else "cover_letter_adaptation"
        )
        return self.engine.generate(
            EngineRequest(
                task=task,
                content=context,
                context={
                    "target_name": target_name,
                    "role_or_mission": role_or_mission,
                    "opportunity_type": record.opportunity_type.value,
                    "cv_path": record.cv_path,
                    "cover_letter_source_path": record.cover_letter_source_path,
                    "cover_letter_output_path": record.cover_letter_output_path,
                    "cv_output_path": record.cv_output_path,
                },
            )
        )

    def draft_mail(
        self,
        *,
        request: MailDraftRequest,
    ) -> MailDraft:
        response = self.engine.generate(
            EngineRequest(
                task="mail_draft",
                content=request.context,
                context={
                    "opportunity_type": request.opportunity_type.value,
                    "target_name": request.target_name,
                    "role_or_mission": request.role_or_mission,
                    "attachment_paths": "\n".join(request.attachment_paths),
                },
            )
        )
        if not response.available:
            return MailDraft(subject="", body=response.text, source=response.source, available=False)

        subject, body = _parse_mail_response(response.text)
        return MailDraft(subject=subject, body=body, source=response.source, available=True)

    def save_preview(
        self,
        *,
        result_dir: Path,
        kind: DocumentKind,
        target_name: str,
        role_or_mission: str,
        date: str,
        content: str,
    ) -> Path:
        result_dir.mkdir(parents=True, exist_ok=True)
        filename = build_document_filename(
            kind=kind,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date,
            extension="txt",
        )
        path = build_result_path(result_dir, filename)
        path.write_text(content, encoding="utf-8")
        return path


def _parse_mail_response(text: str) -> tuple[str, str]:
    subject = ""
    body_lines: list[str] = []
    in_body = False

    for line in text.splitlines():
        normalized = line.strip()
        lower = normalized.lower()
        if lower.startswith("objet:"):
            subject = normalized.split(":", 1)[1].strip()
            continue
        if lower.startswith("corps:"):
            in_body = True
            remainder = normalized.split(":", 1)[1].strip()
            if remainder:
                body_lines.append(remainder)
            continue
        if in_body:
            body_lines.append(line)

    if not subject:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        subject = first_line[:120]
    body = "\n".join(body_lines).strip() if body_lines else text.strip()
    return subject, body

