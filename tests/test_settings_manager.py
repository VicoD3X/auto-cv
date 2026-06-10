from autocv.settings import SettingsManager


def test_settings_manager_loads_defaults_without_json(tmp_path) -> None:
    manager = SettingsManager(tmp_path / "settings.json")

    settings = manager.load()

    assert settings.document_source_dir.name == "GENERIQUE PRO"
    assert settings.result_dir == settings.document_source_dir / "Auto-CV" / "Result"
    assert settings.github_owner == "VicoD3X"


def test_settings_manager_saves_and_loads_local_settings(tmp_path) -> None:
    manager = SettingsManager(tmp_path / "settings.json")
    source_dir = tmp_path / "source"
    cv_path = source_dir / "cv.pdf"
    letter_path = source_dir / "letter.docx"

    settings = manager.update_document_source_dir(manager.load(), source_dir)
    settings = manager.update_selected_documents(
        settings,
        selected_cv_path=cv_path,
        selected_cover_letter_path=letter_path,
    )
    settings = manager.update_github_owner(settings, "VicoD3X-test")
    settings = manager.update_local_ai_base_url(settings, "http://127.0.0.1:8081/v1")

    loaded = manager.load()

    assert loaded.document_source_dir == source_dir
    assert loaded.result_dir == source_dir / "Auto-CV" / "Result"
    assert loaded.selected_cv_path == cv_path
    assert loaded.selected_cover_letter_path == letter_path
    assert loaded.github_owner == "VicoD3X-test"
    assert loaded.local_ai_base_url == "http://127.0.0.1:8081/v1"


def test_settings_manager_derives_result_dir_when_source_changes(tmp_path) -> None:
    manager = SettingsManager(tmp_path / "settings.json")
    new_source = tmp_path / "custom"

    updated = manager.update_document_source_dir(manager.load(), new_source)

    assert updated.document_source_dir == new_source
    assert updated.result_dir == new_source / "Auto-CV" / "Result"
