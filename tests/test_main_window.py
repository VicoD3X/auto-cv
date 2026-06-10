from dataclasses import replace
from pathlib import Path
from time import monotonic

from PySide6.QtWidgets import QApplication

from autocv.ai import LocalAiServerResult
from autocv.domain import ApplicationStatus
from autocv.projects import GitHubProjectContext
from autocv.settings.app_settings import AppSettings
from autocv.ui.main_window import _project_payload
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
    assert window.stack.count() == 7
    assert window.chat_input.isVisible() is False
    assert "Atelier pret" in window.activity_log.toPlainText()
    window.show_view("Documents")
    assert window.documents_table.rowCount() == 2
    assert window.duplicate_document_button.text() == "Dupliquer & ouvrir"
    assert window.finalize_document_button.text() == "Finaliser modification"
    assert window.cancel_document_button.text() == "Annuler et supprimer"
    assert window.open_target_folder_button.text() == "Ouvrir dossier cible"
    window.show_view("Pre-suppression")
    assert window.trash_table.columnCount() == 7
    assert window.restore_trash_button.text() == "Restaurer"
    assert window.delete_trash_button.text() == "Supprimer definitivement"
    window.show_view("Projets publics")
    assert window.projects_table.columnCount() == 6
    assert window.copy_project_name_button.text() == "Copier nom"
    assert window.copy_project_url_button.text() == "Copier URL"
    assert window.copy_project_link_button.text() == "Copier hyperlien Word"
    assert window.open_project_button.text() == "Ouvrir projet"
    window.show_view("Parametres")
    assert window.stack.currentIndex() == window.view_indexes["Parametres"]
    assert window.bootstrap.document_source_ready is True

    window.close()
    app.processEvents()


def test_main_window_uses_public_project_library_actions(tmp_path, monkeypatch) -> None:
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
        result_dir=source_dir / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
    )
    project = GitHubProjectContext(
        repository_name="spark-vision",
        url="https://github.com/VicoD3X/spark-vision",
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)
    window.projects = [project]
    window._populate_projects_table()
    window.show_view("Projets publics")
    window.projects_table.selectRow(0)
    opened_urls: list[str] = []
    monkeypatch.setattr(window, "_open_url", opened_urls.append)

    class FakeClipboard:
        def __init__(self) -> None:
            self.text_value = ""
            self.mime_value = None

        def setText(self, value: str) -> None:
            self.text_value = value

        def text(self) -> str:
            return self.text_value

        def setMimeData(self, mime) -> None:
            self.mime_value = mime

        def mimeData(self):
            return self.mime_value

    fake_clipboard = FakeClipboard()
    monkeypatch.setattr("autocv.ui.main_window.QApplication.clipboard", lambda: fake_clipboard)

    window.copy_selected_project_name()

    assert fake_clipboard.text() == "spark-vision"

    window.copy_selected_project_hyperlink()

    assert fake_clipboard.mimeData().text() == "spark-vision"
    assert "https://github.com/VicoD3X/spark-vision" in fake_clipboard.mimeData().html()

    window.open_selected_project()

    assert opened_urls == ["https://github.com/VicoD3X/spark-vision"]

    window.use_project_payload(_project_payload(project))

    assert window.selected_projects["__global__"] == project
    assert "Projet public selectionne: spark-vision" in window.project_chip.text()
    assert "Projet public selectionne: spark-vision" in window.activity_log.toPlainText()

    window.close()
    app.processEvents()


def test_main_window_project_clipboard_falls_back_to_plain_text(tmp_path, monkeypatch) -> None:
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
        result_dir=source_dir / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
    )

    class FakeClipboard:
        def __init__(self) -> None:
            self.text = ""

        def setMimeData(self, mime) -> None:
            raise RuntimeError("rich clipboard unavailable")

        def setText(self, value: str) -> None:
            self.text = value

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)
    fake_clipboard = FakeClipboard()
    monkeypatch.setattr("autocv.ui.main_window.QApplication.clipboard", lambda: fake_clipboard)

    mode = window._copy_project_payload_to_clipboard("spark-vision", "<a>spark-vision</a>")

    assert mode == "plain"
    assert fake_clipboard.text == "spark-vision"
    assert (settings.data_dir / "logs" / "autocv.log").exists()

    window.close()
    app.processEvents()


def test_main_window_updates_status_offscreen(tmp_path, monkeypatch) -> None:
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


def test_main_window_prepares_deterministic_mail_without_ai(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    captured = {}

    class FakePreviewDialog:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        def exec(self) -> int:
            return 0

    monkeypatch.setattr("autocv.ui.main_window.PreviewDialog", FakePreviewDialog)
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
    window.service.create_job_application(company="Airbus", title="Data Scientist")
    window.refresh()
    window.table.selectRow(0)

    window.prepare_selected_mail()

    output_path = captured["output_path"]
    content = output_path.read_text(encoding="utf-8")
    assert "Candidature - Data Scientist - Victor Aubry" in content
    assert "Bonjour," in content
    assert "Airbus" in content
    assert "Data Scientist" in content
    assert output_path.parent == Path(window.current_records[0].export_dir)
    assert window.ai_server is None

    window.close()
    app.processEvents()


def test_main_window_document_edit_session_deletes_unchanged_copy(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr("autocv.ui.main_window.QMessageBox.information", lambda *args, **kwargs: None)
    monkeypatch.setattr("autocv.ui.main_window.QMessageBox.warning", lambda *args, **kwargs: None)
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    cv_source = source_dir / "cv.pdf"
    letter_source = source_dir / "lettre.docx"
    cv_source.write_text("CV", encoding="utf-8")
    letter_source.write_text("Lettre", encoding="utf-8")
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
    opened: list[Path] = []
    monkeypatch.setattr(window, "_open_path", lambda path: opened.append(Path(path)))
    window.show_view("Documents")
    letter_row = next(
        index for index, document in enumerate(window.scanned_documents) if document.path == letter_source
    )
    window.documents_table.selectRow(letter_row)

    window.duplicate_selected_document_for_edit()
    session = window.current_edit_session
    assert session is not None
    assert opened == [session.working_copy_path]
    assert session.working_copy_path.exists()
    assert session.working_copy_path.parent.is_relative_to(settings.result_dir)

    window.finalize_current_edit_session()

    assert window.current_edit_session is None
    assert not session.working_copy_path.exists()
    assert len(window.trash_entries) == 1
    assert window.trash_entries[0].trash_path.exists()
    assert letter_source.read_text(encoding="utf-8") == "Lettre"

    window.show_view("Pre-suppression")
    window.trash_table.selectRow(0)
    window.restore_selected_trash_entry()

    assert session.working_copy_path.exists()
    assert window.trash_entries == []
    assert letter_source.read_text(encoding="utf-8") == "Lettre"

    window.close()
    app.processEvents()


def test_main_window_document_edit_session_keeps_modified_copy_and_can_cancel(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr("autocv.ui.main_window.QMessageBox.information", lambda *args, **kwargs: None)
    monkeypatch.setattr("autocv.ui.main_window.QMessageBox.warning", lambda *args, **kwargs: None)
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    cv_source = source_dir / "cv.pdf"
    letter_source = source_dir / "lettre.docx"
    cv_source.write_text("CV", encoding="utf-8")
    letter_source.write_text("Lettre", encoding="utf-8")
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
    monkeypatch.setattr(window, "_open_path", lambda path: None)
    window.show_view("Documents")
    letter_row = next(
        index for index, document in enumerate(window.scanned_documents) if document.path == letter_source
    )
    window.documents_table.selectRow(letter_row)

    window.duplicate_selected_document_for_edit()
    kept_session = window.current_edit_session
    assert kept_session is not None
    kept_session.working_copy_path.write_text("Lettre modifiee", encoding="utf-8")

    window.finalize_current_edit_session()

    assert window.current_edit_session is None
    assert kept_session.working_copy_path.exists()
    assert kept_session.working_copy_path.read_text(encoding="utf-8") == "Lettre modifiee"

    window.duplicate_selected_document_for_edit()
    cancelled_session = window.current_edit_session
    assert cancelled_session is not None

    window.cancel_current_edit_session()

    assert window.current_edit_session is None
    assert not cancelled_session.working_copy_path.exists()
    assert len(window.trash_entries) == 1
    assert window.trash_entries[0].reason.value == "canceled_edit"
    assert letter_source.read_text(encoding="utf-8") == "Lettre"

    window.close()
    app.processEvents()


def test_main_window_creates_document_pack_without_ai(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr("autocv.ui.main_window.QMessageBox.information", lambda *args, **kwargs: None)
    monkeypatch.setattr("autocv.ui.main_window.QMessageBox.warning", lambda *args, **kwargs: None)
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    cv_source = source_dir / "cv.pdf"
    letter_source = source_dir / "lettre.docx"
    cv_source.write_text("CV", encoding="utf-8")
    letter_source.write_text("Lettre", encoding="utf-8")
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
    opened: list[Path] = []
    monkeypatch.setattr(window, "_open_path", lambda path: opened.append(Path(path)))
    draft = window.service.create_job_application(company="Airbus", title="Data Scientist")
    window.refresh()
    window.show_view("Candidatures")
    window.jobs_table.selectRow(0)

    window.create_selected_document_pack()

    target_folder = Path(draft.application.export_dir)
    assert opened[-1] == target_folder
    assert list(target_folder.glob("CV_Airbus_Data_Scientist_*.pdf"))
    assert list(target_folder.glob("Lettre_Motivation_Airbus_Data_Scientist_*.docx"))
    mail_files = list(target_folder.glob("Mail_Airbus_Data_Scientist_*.txt"))
    assert len(mail_files) == 1
    assert "Objet: Candidature - Data Scientist - Victor Aubry" in mail_files[0].read_text(
        encoding="utf-8"
    )
    assert cv_source.read_text(encoding="utf-8") == "CV"
    assert letter_source.read_text(encoding="utf-8") == "Lettre"
    assert window.ai_server is None

    window.open_selected_generated_cv()
    window.open_selected_generated_letter()
    window.open_selected_mail_file()

    assert Path(draft.application.cv_output_path) in opened
    assert Path(draft.application.cover_letter_output_path) in opened
    assert mail_files[0] in opened

    window.close()
    app.processEvents()


def test_main_window_does_not_start_ai_on_launch(tmp_path, monkeypatch) -> None:
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
        result_dir=source_dir / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
    )
    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)

    assert window.ai_server is None
    assert "V1 sans IA" in window.local_ai_status.text()

    window.close()
    app.processEvents()


def test_main_window_keeps_ai_disabled_even_if_setting_is_enabled(tmp_path, monkeypatch) -> None:
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
        result_dir=source_dir / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
        local_ai_enabled=True,
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)
    fake_server = FakeAiServer()
    window.ai_server = fake_server
    window.chat_input.setText("Tu es pret ?")

    window.send_chat_message()

    assert fake_server.ensure_calls == 0
    assert window.ai_idle_timer.isActive() is False
    assert "Victor\nTu es pret ?" not in window.chat_transcript.toPlainText()
    assert "V1 sans IA" in window.local_ai_status.text()

    window.close()
    app.processEvents()


def test_main_window_stops_ai_after_idle_timeout(tmp_path, monkeypatch) -> None:
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
        result_dir=source_dir / "Auto-CV" / "Result",
        generic_cv_filename="cv.pdf",
        generic_cover_letter_filename="lettre.docx",
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)
    fake_server = FakeAiServer()
    fake_server.online = True
    window.ai_server = fake_server
    window.ai_last_activity = monotonic() - (window.ai_idle_timeout_ms / 1000) - 1

    window.stop_ai_after_idle()

    assert fake_server.stop_calls == 1

    window.close()
    app.processEvents()


class FakeAiServer:
    def __init__(self) -> None:
        self.ensure_calls = 0
        self.stop_calls = 0
        self.online = False

    def ensure_running(self) -> LocalAiServerResult:
        self.ensure_calls += 1
        self.online = True
        return LocalAiServerResult(available=True, message="started")

    def is_online(self) -> bool:
        return self.online

    def stop(self) -> LocalAiServerResult:
        self.stop_calls += 1
        self.online = False
        return LocalAiServerResult(available=True, message="stopped")
