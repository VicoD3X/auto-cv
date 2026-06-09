from autocv.app.runtime import create_runtime


def test_runtime_starts_offline_by_default() -> None:
    runtime = create_runtime()

    assert runtime.settings.default_mode == "offline"
    assert runtime.settings.primary_platform == "windows-pc"
    assert runtime.settings.ipad_companion_enabled is False
    assert runtime.settings.repository_language == "en-US"
    assert runtime.settings.user_interface_language == "fr-FR"
    assert runtime.settings.generated_content_language == "fr-FR"
    assert runtime.settings.document_source_dir.name == "GENERIQUE PRO"
    assert runtime.settings.generic_cv_filename == "CV_Victor_Aubry_Data_Scientist_pdf.pdf"
    assert runtime.settings.generic_cover_letter_filename == "Lettre_motivation_Victor_Aubry.docx"
    assert runtime.settings.github_owner == "VicoD3X"
    assert runtime.settings.github_project_sync_enabled is False
