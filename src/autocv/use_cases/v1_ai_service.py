from dataclasses import dataclass
from pathlib import Path

from autocv.documents import CoverLetterDocxWriter, CoverLetterWriteRequest
from autocv.documents.naming import DocumentKind, build_document_filename, build_result_path
from autocv.domain import ApplicationRecord, OpportunityType
from autocv.engine import AutoCvEngine, EngineRequest, EngineResponse, load_engine
from autocv.mail import MailDraft, MailDraftRequest
from autocv.projects import GitHubProjectContext


@dataclass(frozen=True, slots=True)
class CoverLetterGenerationResult:
    output_path: Path | None
    text: str
    source: str
    available: bool
    model: str = ""


class V1AiService:
    def __init__(
        self,
        engine: AutoCvEngine | None = None,
        cover_letter_writer: CoverLetterDocxWriter | None = None,
    ) -> None:
        self.engine = engine or load_engine()
        self.cover_letter_writer = cover_letter_writer or CoverLetterDocxWriter()

    def chat(
        self,
        *,
        message: str,
        record: ApplicationRecord | None,
        target_name: str,
        role_or_mission: str,
        context: str,
        selected_project: GitHubProjectContext | None = None,
        chat_history: str = "",
    ) -> EngineResponse:
        return self.engine.generate(
            EngineRequest(
                task="chat",
                content=message,
                context={
                    **_record_context(record),
                    **_project_context(selected_project),
                    "target_name": target_name,
                    "role_or_mission": role_or_mission,
                    "opportunity_context": context,
                    "chat_history": chat_history,
                },
            )
        )

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

    def generate_cover_letter_docx(
        self,
        *,
        record: ApplicationRecord,
        target_name: str,
        role_or_mission: str,
        context: str,
        result_dir: Path,
        selected_project: GitHubProjectContext | None = None,
        chat_history: str = "",
    ) -> CoverLetterGenerationResult:
        source_path = Path(record.cover_letter_source_path)
        if source_path.suffix.lower() != ".docx":
            return CoverLetterGenerationResult(
                output_path=None,
                text="La génération DOCX nécessite une lettre source au format .docx.",
                source="v1_ai_service",
                available=False,
            )

        response = self.engine.generate(
            EngineRequest(
                task="cover_letter_adaptation",
                content=context,
                context={
                    **_record_context(record),
                    **_project_context(selected_project),
                    "target_name": target_name,
                    "role_or_mission": role_or_mission,
                    "chat_history": chat_history,
                    "output_contract": (
                        "Retourne uniquement les paragraphes du corps de lettre. "
                        "Ne retourne ni coordonnées, ni date, ni objet, ni salutation, "
                        "ni formule finale, ni signature."
                    ),
                },
            )
        )
        if not response.available:
            return CoverLetterGenerationResult(
                output_path=None,
                text=response.text,
                source=response.source,
                available=False,
                model=response.model,
            )

        output_path = _cover_letter_output_path(record, result_dir, target_name, role_or_mission)
        self.cover_letter_writer.write(
            CoverLetterWriteRequest(
                template_path=source_path,
                output_path=output_path,
                body_text=response.text,
                project_name=selected_project.repository_name if selected_project else "",
                project_url=selected_project.url if selected_project else "",
            )
        )
        return CoverLetterGenerationResult(
            output_path=output_path,
            text=response.text,
            source=response.source,
            available=True,
            model=response.model,
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


def _record_context(record: ApplicationRecord | None) -> dict[str, str]:
    if record is None:
        return {}
    return {
        "opportunity_type": record.opportunity_type.value,
        "cv_path": record.cv_path,
        "cover_letter_source_path": record.cover_letter_source_path,
        "cover_letter_output_path": record.cover_letter_output_path,
        "cv_output_path": record.cv_output_path,
    }


def _project_context(project: GitHubProjectContext | None) -> dict[str, str]:
    if project is None:
        return {}
    return {
        "selected_project_name": project.repository_name,
        "selected_project_url": project.url,
        "selected_project_summary": "\n".join(
            part
            for part in [
                project.description,
                f"Langages: {', '.join(project.languages)}" if project.languages else "",
                f"Topics: {', '.join(project.topics)}" if project.topics else "",
                project.readme_summary,
            ]
            if part
        ),
    }


def _cover_letter_output_path(
    record: ApplicationRecord,
    result_dir: Path,
    target_name: str,
    role_or_mission: str,
) -> Path:
    if record.cover_letter_output_path:
        return Path(record.cover_letter_output_path)

    filename = build_document_filename(
        kind=DocumentKind.COVER_LETTER,
        target_name=target_name,
        role_or_mission=role_or_mission,
        date=record.created_at[:10],
        extension="docx",
    )
    return build_result_path(result_dir, filename)
