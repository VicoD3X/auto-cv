from dataclasses import replace

from PySide6.QtWidgets import QApplication

from autocv.settings.app_settings import AppSettings
from autocv.ui import MainWindow


def test_main_window_can_be_created_offscreen(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    (source_dir / "cv.pdf").write_text("CV")
    (source_dir / "lettre.docx").write_text("Lettre")

    settings = replace(
        AppSettings.load(),
        data_dir=tmp_path / "data",
        project_context_cache_dir=tmp_path / "data" / "project_context",
        document_source_dir=source_dir,
        result_dir=tmp_path / "GENERIQUE PRO" / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)

    assert window.windowTitle() == "Auto-CV"
    assert window.table.columnCount() == 7
    assert window.bootstrap.document_source_ready is True

    window.close()
    app.processEvents()
