from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitHubProjectSyncSettings:
    owner: str
    cache_dir: Path
    enabled: bool = False


@dataclass(frozen=True, slots=True)
class GitHubProjectContext:
    repository_name: str
    url: str
    description: str = ""
    topics: tuple[str, ...] = field(default_factory=tuple)
    languages: tuple[str, ...] = field(default_factory=tuple)
    readme_summary: str = ""
    project_tags: tuple[str, ...] = field(default_factory=tuple)

