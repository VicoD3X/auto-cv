from dataclasses import dataclass
from html import escape

from autocv.projects.github_context import GitHubProjectContext


@dataclass(frozen=True, slots=True)
class ProjectLinkClipboardPayload:
    plain_text: str
    plain_url: str
    html: str


class ProjectLinkClipboardService:
    def build_payload(self, project: GitHubProjectContext) -> ProjectLinkClipboardPayload:
        name = project.repository_name.strip() or project.url.strip()
        url = project.url.strip()
        html = f'<a href="{escape(url, quote=True)}">{escape(name)}</a>' if url else escape(name)
        return ProjectLinkClipboardPayload(
            plain_text=name,
            plain_url=url,
            html=html,
        )
