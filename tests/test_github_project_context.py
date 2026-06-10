from pathlib import Path

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
