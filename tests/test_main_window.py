from dataclasses import replace

from PySide6.QtWidgets import QApplication

from autocv.ai.status import LocalAiStatus
from autocv.domain import ApplicationStatus
from autocv.settings.app_settings import AppSettings
from autocv.ui import MainWindow


def test_main_window_can_be_created_offscreen(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(
        "autocv.ui.main_window.check_local_ai_status",
        lambda base_url: LocalAiStatus(online=False, message="offline"),
    )
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
    assert window.stack.count() == 6
    window.show_view("Documents")
    assert window.documents_table.rowCount() == 2
    window.show_view("Parametres")
    assert window.stack.currentIndex() == window.view_indexes["Parametres"]
    assert window.bootstrap.document_source_ready is True

    window.close()
    app.processEvents()


def test_main_window_updates_status_offscreen(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(
        "autocv.ui.main_window.check_local_ai_status",
        lambda base_url: LocalAiStatus(online=False, message="offline"),
    )
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    (source_dir / "cv.pdf").write_text("CV")
    (source_dir / "lettre.docx").write_text("Lettre")

    settings = replace(
        AppSettings.load(),
        data_dir=tmp_path / "data",
        project_context_cache_dir=tmp_path / "data" / "project_context",
        document_source_dir=source_dir,
        result_dir=source_dir / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)
    draft = window.service.create_job_application(company="Airbus", title="Data Scientist")
    window.refresh()
    window.show_view("Candidatures")
    window.jobs_table.selectRow(0)
    window.jobs_status_combo.setCurrentIndex(
        window.jobs_status_combo.findData(ApplicationStatus.SENT.value)
    )

    window.update_selected_status(window.jobs_table, window.job_records, window.jobs_status_combo)

    assert window.applications.get(draft.application.id).status == ApplicationStatus.SENT

    window.close()
    app.processEvents()
