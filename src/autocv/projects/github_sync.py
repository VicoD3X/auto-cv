from dataclasses import asdict, dataclass
import json
from pathlib import Path

import httpx

from autocv.projects.github_context import GitHubProjectContext


@dataclass(frozen=True, slots=True)
class GitHubSyncResult:
    owner: str
    cache_path: Path
    projects: list[GitHubProjectContext]
    available: bool
    message: str


class GitHubProjectSync:
    def __init__(self, *, owner: str, cache_dir: Path) -> None:
        self.owner = owner
        self.cache_dir = cache_dir
        self.cache_path = cache_dir / f"{owner.lower()}_projects.json"

    def sync(self) -> GitHubSyncResult:
        try:
            projects = self._fetch_projects()
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps([asdict(project) for project in projects], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return GitHubSyncResult(
                owner=self.owner,
                cache_path=self.cache_path,
                projects=projects,
                available=True,
                message=f"{len(projects)} projet(s) synchronisé(s).",
            )
        except Exception as exc:
            cached = self.load_cached()
            return GitHubSyncResult(
                owner=self.owner,
                cache_path=self.cache_path,
                projects=cached,
                available=False,
                message=f"GitHub indisponible, cache chargé ({len(cached)} projet(s)): {exc}",
            )

    def load_cached(self) -> list[GitHubProjectContext]:
        if not self.cache_path.exists():
            return []
        data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        return [_project_from_json(item) for item in data]

    def _fetch_projects(self) -> list[GitHubProjectContext]:
        url = f"https://api.github.com/users/{self.owner}/repos"
        params = {"type": "owner", "sort": "updated", "per_page": "100"}
        with httpx.Client(timeout=20, headers={"Accept": "application/vnd.github+json"}) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            repos = response.json()

        projects: list[GitHubProjectContext] = []
        for repo in repos:
            if repo.get("fork"):
                continue
            languages = tuple([repo.get("language")] if repo.get("language") else [])
            projects.append(
                GitHubProjectContext(
                    repository_name=repo.get("name", ""),
                    url=repo.get("html_url", ""),
                    description=repo.get("description") or "",
                    topics=tuple(repo.get("topics") or []),
                    languages=languages,
                    readme_summary="",
                    project_tags=tuple(repo.get("topics") or []),
                )
            )
        return projects


def _project_from_json(data: dict) -> GitHubProjectContext:
    return GitHubProjectContext(
        repository_name=data.get("repository_name", ""),
        url=data.get("url", ""),
        description=data.get("description", ""),
        topics=tuple(data.get("topics", [])),
        languages=tuple(data.get("languages", [])),
        readme_summary=data.get("readme_summary", ""),
        project_tags=tuple(data.get("project_tags", [])),
    )
