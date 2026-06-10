from pathlib import Path

import autocv.projects.github_sync as github_sync
from autocv.projects import GitHubProjectContext, GitHubProjectSync, GitHubProjectSyncSettings


def test_github_project_sync_settings_default_to_disabled() -> None:
    settings = GitHubProjectSyncSettings(owner="VicoD3X", cache_dir=Path(".cache"))

    assert settings.owner == "VicoD3X"
    assert settings.enabled is False


def test_github_project_context_stores_safe_public_context() -> None:
    context = GitHubProjectContext(
        repository_name="auto-cv",
        url="https://github.com/VicoD3X/auto-cv",
        languages=("Python",),
        topics=("local-first",),
    )

    assert context.repository_name == "auto-cv"
    assert context.languages == ("Python",)


def test_github_project_sync_writes_and_loads_cache(tmp_path, monkeypatch) -> None:
    project = GitHubProjectContext(
        repository_name="auto-cv",
        url="https://github.com/VicoD3X/auto-cv",
        description="Auto-CV",
        topics=("desktop", "local-first"),
        languages=("Python",),
    )
    sync = GitHubProjectSync(owner="VicoD3X", cache_dir=tmp_path)
    monkeypatch.setattr(sync, "_fetch_projects", lambda: [project])

    result = sync.sync()

    assert result.available is True
    assert result.cache_path.exists()
    assert sync.load_cached() == [project]


def test_github_project_sync_fetches_paginated_public_repos(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict | None]] = []

    class FakeResponse:
        def __init__(self, payload, text: str = "") -> None:
            self.payload = payload
            self.text = text

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url, params=None, headers=None):
            calls.append((url, params))
            if url.endswith("/repos"):
                page = int(params["page"])
                if page == 1:
                    return FakeResponse(
                        [
                            {
                                "name": "spark-vision",
                                "html_url": "https://github.com/VicoD3X/spark-vision",
                                "description": "Computer vision pipeline",
                                "topics": ["spark"],
                                "language": "Python",
                                "languages_url": "https://api.github.test/languages",
                                "updated_at": "2026-06-10T10:00:00Z",
                                "fork": False,
                            }
                        ]
                        * 100
                    )
                return FakeResponse([])
            if url.endswith("/languages"):
                return FakeResponse({"Python": 1000, "Jupyter Notebook": 200})
            if url.endswith("/readme"):
                return FakeResponse({}, "# Spark Vision\nDistributed pipeline")
            return FakeResponse({})

    monkeypatch.setattr(github_sync.httpx, "Client", FakeClient)

    result = GitHubProjectSync(owner="VicoD3X", cache_dir=tmp_path).sync()

    assert result.available is True
    assert len(result.projects) == 100
    assert result.projects[0].languages == ("Python", "Jupyter Notebook")
    assert result.projects[0].readme_summary == "# Spark Vision Distributed pipeline"
    assert any(params and params.get("page") == "2" for _, params in calls)
