from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

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
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return [_project_from_json(item) for item in data]

    def _fetch_projects(self) -> list[GitHubProjectContext]:
        url = f"https://api.github.com/users/{self.owner}/repos"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Auto-CV",
        }
        repos: list[dict[str, Any]] = []
        with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as client:
            page = 1
            while True:
                response = client.get(
                    url,
                    params={
                        "type": "owner",
                        "sort": "updated",
                        "direction": "desc",
                        "per_page": "100",
                        "page": str(page),
                    },
                )
                response.raise_for_status()
                page_repos = response.json()
                if not page_repos:
                    break
                repos.extend(page_repos)
                if len(page_repos) < 100:
                    break
                page += 1

            projects: list[GitHubProjectContext] = []
            for repo in repos:
                if repo.get("fork"):
                    continue
                languages = _fetch_languages(client, repo)
                readme_summary = _fetch_readme_summary(client, self.owner, repo)
                topics = tuple(repo.get("topics") or [])
                projects.append(
                    GitHubProjectContext(
                        repository_name=repo.get("name", ""),
                        url=repo.get("html_url", ""),
                        description=repo.get("description") or "",
                        topics=topics,
                        languages=languages,
                        readme_summary=readme_summary,
                        project_tags=topics,
                        updated_at=repo.get("updated_at") or "",
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
        updated_at=data.get("updated_at", ""),
    )


def _fetch_languages(client: httpx.Client, repo: dict[str, Any]) -> tuple[str, ...]:
    url = repo.get("languages_url")
    if not url:
        language = repo.get("language")
        return tuple([language] if language else [])
    try:
        response = client.get(url)
        response.raise_for_status()
        languages = response.json()
    except Exception:
        language = repo.get("language")
        return tuple([language] if language else [])
    return tuple(languages.keys())


def _fetch_readme_summary(
    client: httpx.Client,
    owner: str,
    repo: dict[str, Any],
    *,
    max_chars: int = 1600,
) -> str:
    name = repo.get("name", "")
    if not name:
        return ""
    url = f"https://api.github.com/repos/{owner}/{name}/readme"
    try:
        response = client.get(url, headers={"Accept": "application/vnd.github.raw"})
        response.raise_for_status()
    except Exception:
        return ""
    text = response.text
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return normalized[:max_chars]
