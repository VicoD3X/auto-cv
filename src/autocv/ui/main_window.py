from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
import webbrowser

from PySide6.QtCore import QMimeData, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QDrag, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from autocv.conversion import ConversionRequest, DocumentFormat, LocalDocumentConverter
from autocv.documents import (
    DocumentEditSession,
    DocumentEditSessionService,
    DocumentEditSessionStatus,
    DocumentScanner,
    TrashEntry,
    ScannedDocument,
    copy_to_result,
)
from autocv.documents.naming import (
    DocumentKind,
    build_document_filename,
    build_result_path,
    build_target_folder_path,
)
from autocv.domain import ApplicationRecord, ApplicationStatus, OpportunityType
from autocv.i18n.fr_fr import APPLICATION_STATUS_LABELS
from autocv.infrastructure import (
    ApplicationRecordRepository,
    FreelanceOpportunityRepository,
    JobOfferRepository,
    LocalDatabase,
)
from autocv.mail import MailDraft
from autocv.app.user_log import UserActionLogger
from autocv.projects import GitHubProjectContext, GitHubProjectSync, ProjectLinkClipboardService
from autocv.settings.app_settings import AppSettings, SettingsManager, result_dir_for
from autocv.use_cases import BootstrapWorkspace, MissingDocumentSourceError, V1ApplicationService


PROJECT_MIME_TYPE = "application/x-autocv-github-project"

VIEW_NAMES = [
    "Tableau de bord",
    "Candidatures",
    "Freelance",
    "Documents",
    "Pre-suppression",
    "Projets publics",
    "Parametres",
]


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        if QApplication.instance() is not None:
            QApplication.instance().setFont(QFont("Segoe UI", 9))

        self.settings_manager = SettingsManager(settings.data_dir / "settings.json")
        self.ai_server = None
        self.converter = LocalDocumentConverter()
        self.edit_session_service = DocumentEditSessionService()
        self.trash_service = self.edit_session_service.trash_service
        self.project_clipboard = ProjectLinkClipboardService()
        self.user_logger = UserActionLogger(settings.data_dir / "logs" / "autocv.log")
        self.ai_service = None

        self.current_records: list[ApplicationRecord] = []
        self.job_records: list[ApplicationRecord] = []
        self.freelance_records: list[ApplicationRecord] = []
        self.scanned_documents: list[ScannedDocument] = []
        self.trash_entries: list[TrashEntry] = []
        self.projects: list[GitHubProjectContext] = []
        self.current_edit_session: DocumentEditSession | None = None
        self.nav_buttons: dict[str, QPushButton] = {}
        self.chat_histories: dict[str, list[tuple[str, str]]] = {}
        self.selected_projects: dict[str, GitHubProjectContext] = {}
        self.ai_last_activity = 0.0
        self.ai_idle_timeout_ms = 10 * 60 * 1000
        self.ai_idle_timer = QTimer(self)
        self.ai_idle_timer.setSingleShot(True)
        self.ai_idle_timer.timeout.connect(self.stop_ai_after_idle)

        self._bind_runtime(settings)

        self.setWindowTitle("Auto-CV")
        self.resize(1500, 840)
        self.setMinimumSize(1280, 720)

        self._build_actions()
        self._build_ui()
        self._apply_style()
        self.refresh()

    def _bind_runtime(self, settings: AppSettings) -> None:
        self.settings = settings
        self.user_logger = UserActionLogger(settings.data_dir / "logs" / "autocv.log")
        self.bootstrap = BootstrapWorkspace(settings).run()
        self.database = LocalDatabase(self.bootstrap.database_path)
        self.document_source = self.bootstrap.document_source
        self.service = V1ApplicationService(
            database=self.database,
            document_source=self.document_source,
            result_dir=self.bootstrap.result_dir,
        )
        self.job_offers = JobOfferRepository(self.database)
        self.freelance_opportunities = FreelanceOpportunityRepository(self.database)
        self.applications = ApplicationRecordRepository(self.database)
        self.ai_server = None
        self.ai_service = None

    def _reload_runtime(self, settings: AppSettings) -> None:
        self.current_edit_session = None
        self._bind_runtime(settings)
        self.refresh()

    def _build_actions(self) -> None:
        refresh_action = QAction("Actualiser", self)
        refresh_action.triggered.connect(self.refresh)
        self.addAction(refresh_action)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_main_stack(), stretch=1)

        self.setCentralWidget(root)
        self.detail_dock = QDockWidget("", self)
        self.detail_dock.setObjectName("DetailDock")
        self.detail_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.detail_dock.setTitleBarWidget(QWidget())
        self.detail_dock.setWidget(self._build_detail_panel())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.detail_dock)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(10)

        title = QLabel("Auto-CV")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Assistant personnel")
        subtitle.setObjectName("AppSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        for index, item in enumerate(VIEW_NAMES):
            button = QPushButton(item)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.clicked.connect(lambda checked=False, view_name=item: self.show_view(view_name))
            self.nav_buttons[item] = button
            layout.addWidget(button)

        layout.addStretch()

        self.source_status = QLabel()
        self.source_status.setObjectName("SourceStatus")
        self.source_status.setWordWrap(True)
        layout.addWidget(self.source_status)

        return sidebar

    def _build_main_stack(self) -> QWidget:
        container = QWidget()
        container.setMinimumWidth(0)
        container.setMaximumWidth(980)
        container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setMinimumWidth(0)
        self.stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.view_indexes: dict[str, int] = {}
        builders = [
            self._build_dashboard_view,
            self._build_jobs_view,
            self._build_freelance_view,
            self._build_documents_view,
            self._build_trash_view,
            self._build_projects_view,
            self._build_settings_view,
        ]
        for name, builder in zip(VIEW_NAMES, builders, strict=True):
            self.view_indexes[name] = self.stack.addWidget(builder())
        layout.addWidget(self.stack)
        return container

    def _new_page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout, QHBoxLayout]:
        page = QWidget()
        page.setMinimumWidth(0)
        page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        heading_box = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        subtitle_label.setWordWrap(True)
        heading_box.addWidget(title_label)
        heading_box.addWidget(subtitle_label)
        header.addLayout(heading_box)
        header.addStretch()
        layout.addLayout(header)
        return page, layout, header

    def _build_dashboard_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Tableau de bord",
            "Vue rapide des candidatures, missions et sorties pretes dans Result",
        )

        new_job = QPushButton("+ Candidature")
        new_job.setObjectName("PrimaryButton")
        new_job.clicked.connect(self.create_job_application)
        new_freelance = QPushButton("+ Mission freelance")
        new_freelance.setObjectName("SecondaryButton")
        new_freelance.clicked.connect(self.create_freelance_opportunity)
        header.addWidget(new_job)
        header.addWidget(new_freelance)

        metrics = QHBoxLayout()
        self.metric_total = MetricBox("Total", "0")
        self.metric_ready = MetricBox("Pret", "0")
        self.metric_sent = MetricBox("Envoye", "0")
        self.metric_freelance = MetricBox("Freelance", "0")
        for metric in [self.metric_total, self.metric_ready, self.metric_sent, self.metric_freelance]:
            metrics.addWidget(metric)
        layout.addLayout(metrics)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("ApplicationTable")
        self.table.setHorizontalHeaderLabels(
            ["Type", "Cible", "Poste / mission", "Statut", "CV", "Lettre / prop.", "Sortie"]
        )
        self._configure_table(self.table)
        self.table.itemSelectionChanged.connect(self.update_detail_from_selection)
        layout.addWidget(self.table, stretch=1)
        return page

    def _build_jobs_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Candidatures",
            "Suivi des candidatures salariees avec statut modifiable",
        )

        new_job = QPushButton("+ Candidature")
        new_job.setObjectName("PrimaryButton")
        new_job.clicked.connect(self.create_job_application)
        header.addWidget(new_job)

        self.jobs_table = QTableWidget(0, 5)
        self.jobs_table.setObjectName("ApplicationTable")
        self.jobs_table.setHorizontalHeaderLabels(["Entreprise", "Poste", "Statut", "CV", "Lettre"])
        self._configure_table(self.jobs_table)
        self.jobs_table.itemSelectionChanged.connect(self.update_detail_from_jobs_selection)
        layout.addWidget(self.jobs_table, stretch=1)

        actions = QHBoxLayout()
        self.jobs_status_combo = self._new_status_combo()
        apply_status = QPushButton("Appliquer statut")
        apply_status.setObjectName("ActionButton")
        apply_status.clicked.connect(lambda: self.update_selected_status(self.jobs_table, self.job_records, self.jobs_status_combo))
        delete_button = QPushButton("Supprimer")
        delete_button.setObjectName("DangerButton")
        delete_button.clicked.connect(lambda: self.delete_selected_record(self.jobs_table, self.job_records))
        actions.addWidget(QLabel("Statut"))
        actions.addWidget(self.jobs_status_combo)
        actions.addWidget(apply_status)
        actions.addWidget(delete_button)
        actions.addStretch()
        layout.addLayout(actions)
        return page

    def _build_freelance_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Freelance",
            "Prefiguration legere du suivi mission et prospection freelance",
        )

        new_freelance = QPushButton("+ Mission freelance")
        new_freelance.setObjectName("PrimaryButton")
        new_freelance.clicked.connect(self.create_freelance_opportunity)
        header.addWidget(new_freelance)

        self.freelance_table = QTableWidget(0, 5)
        self.freelance_table.setObjectName("ApplicationTable")
        self.freelance_table.setHorizontalHeaderLabels(["Client", "Mission", "Statut", "CV", "Proposition"])
        self._configure_table(self.freelance_table)
        self.freelance_table.itemSelectionChanged.connect(self.update_detail_from_freelance_selection)
        layout.addWidget(self.freelance_table, stretch=1)

        actions = QHBoxLayout()
        self.freelance_status_combo = self._new_status_combo()
        apply_status = QPushButton("Appliquer statut")
        apply_status.setObjectName("ActionButton")
        apply_status.clicked.connect(
            lambda: self.update_selected_status(
                self.freelance_table,
                self.freelance_records,
                self.freelance_status_combo,
            )
        )
        delete_button = QPushButton("Supprimer")
        delete_button.setObjectName("DangerButton")
        delete_button.clicked.connect(lambda: self.delete_selected_record(self.freelance_table, self.freelance_records))
        actions.addWidget(QLabel("Statut"))
        actions.addWidget(self.freelance_status_combo)
        actions.addWidget(apply_status)
        actions.addWidget(delete_button)
        actions.addStretch()
        layout.addLayout(actions)
        return page

    def _build_documents_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Documents",
            "Scan du dossier source, selection du CV et de la lettre, conversions locales vers Result",
        )

        refresh_button = QPushButton("Rafraichir")
        refresh_button.setObjectName("SecondaryButton")
        refresh_button.clicked.connect(self.refresh)
        choose_source = QPushButton("Changer dossier")
        choose_source.setObjectName("SecondaryButton")
        choose_source.clicked.connect(self.choose_source_directory)
        header.addWidget(choose_source)
        header.addWidget(refresh_button)

        self.documents_table = QTableWidget(0, 5)
        self.documents_table.setObjectName("ApplicationTable")
        self.documents_table.setHorizontalHeaderLabels(["Role", "Fichier", "Type", "Chemin", "Emplacement"])
        self._configure_table(self.documents_table)
        layout.addWidget(self.documents_table, stretch=1)

        selection_actions = QHBoxLayout()
        self.set_cv_button = QPushButton("Definir comme CV")
        self.set_cv_button.setObjectName("ActionButton")
        self.set_cv_button.clicked.connect(lambda: self.set_selected_document("cv"))
        self.set_letter_button = QPushButton("Definir comme lettre")
        self.set_letter_button.setObjectName("ActionButton")
        self.set_letter_button.clicked.connect(lambda: self.set_selected_document("letter"))
        self.duplicate_document_button = QPushButton("Dupliquer & ouvrir")
        self.duplicate_document_button.setObjectName("PrimaryButton")
        self.duplicate_document_button.clicked.connect(self.duplicate_selected_document_for_edit)
        self.finalize_document_button = QPushButton("Finaliser modification")
        self.finalize_document_button.setObjectName("ActionButton")
        self.finalize_document_button.clicked.connect(self.finalize_current_edit_session)
        self.cancel_document_button = QPushButton("Annuler et supprimer")
        self.cancel_document_button.setObjectName("DangerButton")
        self.cancel_document_button.clicked.connect(self.cancel_current_edit_session)
        for button in [
            self.set_cv_button,
            self.set_letter_button,
            self.duplicate_document_button,
            self.finalize_document_button,
            self.cancel_document_button,
        ]:
            selection_actions.addWidget(button)
        selection_actions.addStretch()
        layout.addLayout(selection_actions)

        conversion_actions = QHBoxLayout()
        self.open_target_folder_button = QPushButton("Ouvrir dossier cible")
        self.open_target_folder_button.setObjectName("ActionButton")
        self.open_target_folder_button.clicked.connect(self.open_current_target_folder)
        self.open_result_button_documents = QPushButton("Ouvrir Result")
        self.open_result_button_documents.setObjectName("ActionButton")
        self.open_result_button_documents.clicked.connect(self.open_result_directory)
        self.to_pdf_button = QPushButton("Convertir DOCX -> PDF")
        self.to_pdf_button.setObjectName("ActionButton")
        self.to_pdf_button.clicked.connect(self.convert_selected_to_pdf)
        self.to_docx_button = QPushButton("PDF -> DOCX")
        self.to_docx_button.setObjectName("ActionButton")
        self.to_docx_button.clicked.connect(lambda: self.convert_selected_pdf(DocumentFormat.DOCX))
        for button in [
            self.open_target_folder_button,
            self.open_result_button_documents,
            self.to_pdf_button,
            self.to_docx_button,
        ]:
            conversion_actions.addWidget(button)
        conversion_actions.addStretch()
        layout.addLayout(conversion_actions)
        return page

    def _build_trash_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Pre-suppression",
            "Copies annulees ou obsoletes conservees avant suppression definitive",
        )

        refresh_button = QPushButton("Rafraichir")
        refresh_button.setObjectName("SecondaryButton")
        refresh_button.clicked.connect(self.refresh)
        open_trash = QPushButton("Ouvrir dossier")
        open_trash.setObjectName("SecondaryButton")
        open_trash.clicked.connect(self.open_trash_directory)
        header.addWidget(open_trash)
        header.addWidget(refresh_button)

        self.trash_table = QTableWidget(0, 7)
        self.trash_table.setObjectName("ApplicationTable")
        self.trash_table.setHorizontalHeaderLabels(
            ["Raison", "Fichier", "Date", "Suppression auto", "Taille", "Chemin original", "Pre-suppression"]
        )
        self._configure_table(self.trash_table)
        layout.addWidget(self.trash_table, stretch=1)

        actions = QHBoxLayout()
        self.restore_trash_button = QPushButton("Restaurer")
        self.restore_trash_button.setObjectName("PrimaryButton")
        self.restore_trash_button.clicked.connect(self.restore_selected_trash_entry)
        self.delete_trash_button = QPushButton("Supprimer definitivement")
        self.delete_trash_button.setObjectName("DangerButton")
        self.delete_trash_button.clicked.connect(self.delete_selected_trash_entry)
        actions.addWidget(self.restore_trash_button)
        actions.addWidget(self.delete_trash_button)
        actions.addStretch()
        layout.addLayout(actions)
        return page

    def _build_projects_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Projets publics",
            "Bibliotheque GitHub publique pour citer rapidement un projet dans Word",
        )

        self.github_owner_input = QLineEdit()
        self.github_owner_input.setFixedWidth(160)
        sync_button = QPushButton("Synchroniser")
        sync_button.setObjectName("PrimaryButton")
        sync_button.clicked.connect(self.sync_github_projects)
        header.addWidget(QLabel("Owner"))
        header.addWidget(self.github_owner_input)
        header.addWidget(sync_button)

        self.projects_table = ProjectTableWidget(0, 6)
        self.projects_table.setObjectName("ApplicationTable")
        self.projects_table.setHorizontalHeaderLabels(
            ["Projet", "Langage", "Topics", "Description", "URL", "MAJ"]
        )
        self._configure_table(self.projects_table)
        self.projects_table.setDragEnabled(True)
        layout.addWidget(self.projects_table, stretch=1)

        actions = QHBoxLayout()
        self.copy_project_name_button = QPushButton("Copier nom")
        self.copy_project_name_button.setObjectName("ActionButton")
        self.copy_project_name_button.clicked.connect(self.copy_selected_project_name)
        self.copy_project_url_button = QPushButton("Copier URL")
        self.copy_project_url_button.setObjectName("ActionButton")
        self.copy_project_url_button.clicked.connect(self.copy_selected_project_url)
        self.copy_project_link_button = QPushButton("Copier hyperlien Word")
        self.copy_project_link_button.setObjectName("PrimaryButton")
        self.copy_project_link_button.clicked.connect(self.copy_selected_project_hyperlink)
        self.open_project_button = QPushButton("Ouvrir projet")
        self.open_project_button.setObjectName("ActionButton")
        self.open_project_button.clicked.connect(self.open_selected_project)
        for button in [
            self.copy_project_name_button,
            self.copy_project_url_button,
            self.copy_project_link_button,
            self.open_project_button,
        ]:
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        return page

    def _build_settings_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Parametres",
            "Configuration locale persistee dans ~/.autocv/settings.json",
        )

        choose_source = QPushButton("Changer dossier source")
        choose_source.setObjectName("PrimaryButton")
        choose_source.clicked.connect(self.choose_source_directory)
        save_button = QPushButton("Sauvegarder")
        save_button.setObjectName("SecondaryButton")
        save_button.clicked.connect(self.save_settings_from_form)
        header.addWidget(choose_source)
        header.addWidget(save_button)

        form_panel = QFrame()
        form_panel.setObjectName("FormPanel")
        form = QFormLayout(form_panel)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        self.settings_source_dir = QLineEdit()
        self.settings_source_dir.setReadOnly(True)
        self.settings_result_dir = QLineEdit()
        self.settings_result_dir.setReadOnly(True)
        self.settings_cv_path = QLineEdit()
        self.settings_cv_path.setReadOnly(True)
        self.settings_letter_path = QLineEdit()
        self.settings_letter_path.setReadOnly(True)
        self.settings_github_owner_input = QLineEdit()
        self.settings_ai_mode_input = QLineEdit()
        self.settings_ai_mode_input.setReadOnly(True)
        self.settings_ai_url_input = QLineEdit()
        self.settings_ai_url_input.setEnabled(False)

        form.addRow("Dossier source", self.settings_source_dir)
        form.addRow("Dossier Result", self.settings_result_dir)
        form.addRow("CV source", self.settings_cv_path)
        form.addRow("Lettre source", self.settings_letter_path)
        form.addRow("GitHub owner", self.settings_github_owner_input)
        form.addRow("Mode IA", self.settings_ai_mode_input)
        form.addRow("IA locale URL", self.settings_ai_url_input)
        layout.addWidget(form_panel)
        layout.addStretch()
        return page

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("DetailPanel")
        panel.setFixedWidth(340)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)

        title = QLabel("Detail")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        self.detail_title = QLabel("Aucune selection")
        self.detail_title.setObjectName("DetailTitle")
        self.detail_title.setWordWrap(True)
        layout.addWidget(self.detail_title)

        self.detail_meta = QLabel("")
        self.detail_meta.setObjectName("DetailMeta")
        self.detail_meta.setWordWrap(True)
        layout.addWidget(self.detail_meta)

        self.detail_paths = QTextEdit()
        self.detail_paths.setObjectName("PathBox")
        self.detail_paths.setReadOnly(True)
        self.detail_paths.setMinimumHeight(130)
        layout.addWidget(self.detail_paths)

        self.project_chip = QLabel("Projet public selectionne: aucun")
        self.project_chip.setObjectName("ProjectChip")
        self.project_chip.setWordWrap(True)
        layout.addWidget(self.project_chip)

        journal_title = QLabel("Journal atelier")
        journal_title.setObjectName("ActionTitle")
        layout.addWidget(journal_title)

        self.activity_log = AssistantTranscript()
        self.activity_log.setObjectName("ChatTranscript")
        self.activity_log.setReadOnly(True)
        self.activity_log.setMinimumHeight(220)
        self.activity_log.projectDropped.connect(self.use_project_payload)
        layout.addWidget(self.activity_log, stretch=1)
        self.chat_transcript = self.activity_log

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("")
        self.chat_input.setEnabled(False)
        self.chat_send_button = QPushButton("Envoyer")
        self.chat_send_button.setEnabled(False)

        actions = QFrame()
        actions.setObjectName("ActionsPanel")
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(12, 12, 12, 12)
        actions_layout.setSpacing(8)
        actions_title = QLabel("Atelier documentaire")
        actions_title.setObjectName("ActionTitle")
        actions_layout.addWidget(actions_title)
        self.create_pack_button = QPushButton("Creer pack candidature")
        self.create_pack_button.setObjectName("PrimaryButton")
        self.create_pack_button.clicked.connect(self.create_selected_document_pack)
        self.prepare_mail_button = QPushButton("Preparer le mail")
        self.prepare_mail_button.setObjectName("ActionButton")
        self.prepare_mail_button.clicked.connect(self.prepare_selected_mail)
        self.open_cv_button = QPushButton("Ouvrir CV")
        self.open_cv_button.setObjectName("ActionButton")
        self.open_cv_button.clicked.connect(self.open_selected_generated_cv)
        self.open_letter_button = QPushButton("Ouvrir lettre")
        self.open_letter_button.setObjectName("ActionButton")
        self.open_letter_button.clicked.connect(self.open_selected_generated_letter)
        self.open_mail_button = QPushButton("Ouvrir mail")
        self.open_mail_button.setObjectName("ActionButton")
        self.open_mail_button.clicked.connect(self.open_selected_mail_file)
        self.open_target_button = QPushButton("Ouvrir dossier cible")
        self.open_target_button.setObjectName("ActionButton")
        self.open_target_button.clicked.connect(self.open_current_target_folder)
        self.open_result_button = QPushButton("Ouvrir Result")
        self.open_result_button.setObjectName("ActionButton")
        self.open_result_button.clicked.connect(self.open_result_directory)
        for button in [
            self.create_pack_button,
            self.prepare_mail_button,
            self.open_cv_button,
            self.open_letter_button,
            self.open_mail_button,
            self.open_target_button,
            self.open_result_button,
        ]:
            button.setMinimumHeight(36)
            actions_layout.addWidget(button)
        layout.addWidget(actions)

        self.local_ai_status = QLabel("V1 sans IA: aucun modele local ne demarre")
        self.local_ai_status.setObjectName("AiStatus")
        self.local_ai_status.setWordWrap(True)
        layout.addWidget(self.local_ai_status)

        return panel

    def _configure_table(self, table: QTableWidget) -> None:
        table.setMinimumWidth(0)
        table.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setMinimumSectionSize(58)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

    def _new_status_combo(self) -> QComboBox:
        combo = QComboBox()
        for status in ApplicationStatus:
            combo.addItem(APPLICATION_STATUS_LABELS.get(status.value, status.value), status.value)
        return combo

    def show_view(self, view_name: str) -> None:
        self.stack.setCurrentIndex(self.view_indexes[view_name])
        for name, button in self.nav_buttons.items():
            button.setChecked(name == view_name)
        if view_name == "Candidatures":
            self.update_detail_from_jobs_selection()
        elif view_name == "Freelance":
            self.update_detail_from_freelance_selection()
        elif view_name == "Tableau de bord":
            self.update_detail_from_selection()

    def refresh(self) -> None:
        records = self.applications.list_all()
        self.current_records = records
        self.job_records = self.applications.list_jobs()
        self.freelance_records = self.applications.list_freelance()
        self.scanned_documents = self._scan_documents()
        self.trash_entries = self.trash_service.list_entries(self.settings.result_dir)
        self.projects = GitHubProjectSync(
            owner=self.settings.github_owner,
            cache_dir=self.settings.project_context_cache_dir,
        ).load_cached()

        self._populate_dashboard_table(records)
        self._populate_records_table(self.jobs_table, self.job_records)
        self._populate_records_table(self.freelance_table, self.freelance_records)
        self._populate_documents_table()
        self._populate_trash_table()
        self._populate_projects_table()
        self._update_metrics(records)
        self._update_source_status()
        self._update_settings_form()
        self._update_ai_status()

        current_view = VIEW_NAMES[self.stack.currentIndex()]
        if current_view == "Candidatures":
            self.update_detail_from_jobs_selection()
        elif current_view == "Freelance":
            self.update_detail_from_freelance_selection()
        else:
            self.update_detail_from_selection()

    def _scan_documents(self) -> list[ScannedDocument]:
        scanner = DocumentScanner(
            source_dir=self.settings.document_source_dir,
            result_dir=self.settings.result_dir,
            selected_cv_path=self.document_source.cv_path,
            selected_cover_letter_path=self.document_source.cover_letter_path,
        )
        return scanner.scan()

    def _populate_dashboard_table(self, records: list[ApplicationRecord]) -> None:
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            target_name, role = self._target_for_record(record)
            cells = [
                "Salariat" if record.opportunity_type == OpportunityType.JOB else "Freelance",
                target_name,
                role,
                self._status_label(record.status),
                "OK" if record.cv_output_path else "-",
                "OK" if record.cover_letter_output_path else "-",
                "Result" if record.export_dir else "-",
            ]
            self._set_table_row(self.table, row, cells, record.id)
        self.table.resizeRowsToContents()
        if records:
            self.table.selectRow(0)

    def _populate_records_table(self, table: QTableWidget, records: list[ApplicationRecord]) -> None:
        table.setRowCount(len(records))
        for row, record in enumerate(records):
            target_name, role = self._target_for_record(record)
            cells = [
                target_name,
                role,
                self._status_label(record.status),
                "OK" if record.cv_output_path else "-",
                "OK" if record.cover_letter_output_path else "-",
            ]
            self._set_table_row(table, row, cells, record.id)
        table.resizeRowsToContents()
        if records:
            table.selectRow(0)

    def _populate_documents_table(self) -> None:
        self.documents_table.setRowCount(len(self.scanned_documents))
        for row, document in enumerate(self.scanned_documents):
            role = "-"
            if document.selected_as_cv:
                role = "CV"
            elif document.selected_as_cover_letter:
                role = "Lettre"
            cells = [
                role,
                document.path.name,
                document.kind.value,
                document.relative_path,
                document.location.value,
            ]
            self._set_table_row(self.documents_table, row, cells, str(document.path))
        self.documents_table.resizeRowsToContents()
        if self.scanned_documents:
            self.documents_table.selectRow(0)

    def _populate_trash_table(self) -> None:
        self.trash_table.setRowCount(len(self.trash_entries))
        for row, entry in enumerate(self.trash_entries):
            cells = [
                self._trash_reason_label(entry),
                entry.original_path.name,
                entry.deleted_at,
                self._trash_expiration_label(entry),
                f"{entry.size} o",
                str(entry.original_path),
                str(entry.trash_path),
            ]
            self._set_table_row(self.trash_table, row, cells, entry.entry_id)
        self.trash_table.resizeRowsToContents()
        if self.trash_entries:
            self.trash_table.selectRow(0)

    def _populate_projects_table(self) -> None:
        self.projects_table.setRowCount(len(self.projects))
        for row, project in enumerate(self.projects):
            cells = [
                project.repository_name,
                ", ".join(project.languages) or "-",
                ", ".join(project.topics) or "-",
                project.description,
                project.url,
                project.updated_at[:10] if project.updated_at else "-",
            ]
            self._set_table_row(self.projects_table, row, cells, _project_payload(project))
        self.projects_table.resizeRowsToContents()

    def _set_table_row(
        self,
        table: QTableWidget,
        row: int,
        cells: list[str],
        user_data: str,
    ) -> None:
        for column, value in enumerate(cells):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.UserRole, user_data)
            item.setForeground(QColor("#d9e7f5"))
            if "statut" in (table.horizontalHeaderItem(column).text().lower()):
                item.setForeground(QColor("#5eead4"))
            table.setItem(row, column, item)

    def _update_metrics(self, records: list[ApplicationRecord]) -> None:
        ready = sum(1 for record in records if record.status == ApplicationStatus.READY)
        sent = sum(1 for record in records if record.status == ApplicationStatus.SENT)
        freelance = sum(1 for record in records if record.opportunity_type == OpportunityType.FREELANCE)
        self.metric_total.set_value(str(len(records)))
        self.metric_ready.set_value(str(ready))
        self.metric_sent.set_value(str(sent))
        self.metric_freelance.set_value(str(freelance))

    def _update_source_status(self) -> None:
        source = "pret" if self.bootstrap.document_source_ready else "documents manquants"
        self.source_status.setText(
            f"Source: {source}\n"
            f"Result: pret\n"
            f"{self.settings.document_source_dir}"
        )

    def _update_settings_form(self) -> None:
        self.settings_source_dir.setText(str(self.settings.document_source_dir))
        self.settings_result_dir.setText(str(self.settings.result_dir))
        self.settings_cv_path.setText(str(self.document_source.cv_path))
        self.settings_letter_path.setText(str(self.document_source.cover_letter_path))
        self.settings_github_owner_input.setText(self.settings.github_owner)
        self.settings_ai_mode_input.setText(
            "Desactivee - V1 sans LLM" if not self.settings.local_ai_enabled else "Activee"
        )
        self.settings_ai_url_input.setText(self.settings.local_ai_base_url)
        self.github_owner_input.setText(self.settings.github_owner)

    def _update_ai_status(self) -> None:
        self.local_ai_status.setText("V1 sans IA: aucun modele local ne demarre")
        self.chat_input.setEnabled(False)
        self.chat_send_button.setEnabled(False)
        self.create_pack_button.setEnabled(True)
        self.prepare_mail_button.setEnabled(True)

    def update_detail_from_selection(self) -> None:
        record = self._selected_record_from_table(self.table, self.current_records)
        self._update_detail(record)

    def update_detail_from_jobs_selection(self) -> None:
        record = self._selected_record_from_table(self.jobs_table, self.job_records)
        self._update_detail(record)
        if record is not None:
            self._set_combo_status(self.jobs_status_combo, record.status)

    def update_detail_from_freelance_selection(self) -> None:
        record = self._selected_record_from_table(self.freelance_table, self.freelance_records)
        self._update_detail(record)
        if record is not None:
            self._set_combo_status(self.freelance_status_combo, record.status)

    def _update_detail(self, record: ApplicationRecord | None) -> None:
        if record is None:
            self.detail_title.setText("Aucune selection")
            self.detail_meta.setText("")
            self.detail_paths.setPlainText("")
            self._render_chat()
            return

        target_name, role = self._target_for_record(record)
        self.detail_title.setText(f"{target_name}\n{role}")
        self.detail_meta.setText(
            f"{self._status_label(record.status)} - "
            f"{'Salariat' if record.opportunity_type == OpportunityType.JOB else 'Freelance'}"
        )
        self.detail_paths.setPlainText(
            "\n".join(
                [
                    "Etat du pack:",
                    f"CV genere: {self._exists_label(record.cv_output_path)}",
                    f"Lettre / proposition: {self._exists_label(record.cover_letter_output_path)}",
                    f"Mail: {self._exists_label(self._mail_output_path_for_record(record))}",
                    f"PDF final: {'OK' if self._record_pdf_final_exists(record) else 'Absent'}",
                    "",
                    f"CV source:\n{record.cv_path}",
                    "",
                    f"CV renomme:\n{record.cv_output_path or '-'}",
                    "",
                    f"Lettre source:\n{record.cover_letter_source_path}",
                    "",
                    f"Sortie prevue:\n{record.cover_letter_output_path or '-'}",
                    "",
                    f"Dossier:\n{record.export_dir or '-'}",
                ]
            )
        )
        self._render_chat()

    def create_job_application(self) -> None:
        dialog = JobApplicationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.values()
        try:
            self.service.create_job_application(**data)
        except MissingDocumentSourceError as exc:
            QMessageBox.warning(self, "Source manquante", str(exc))
            return
        self.refresh()

    def create_freelance_opportunity(self) -> None:
        dialog = FreelanceOpportunityDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.values()
        try:
            self.service.create_freelance_opportunity(**data)
        except MissingDocumentSourceError as exc:
            QMessageBox.warning(self, "Source manquante", str(exc))
            return
        self.refresh()

    def update_selected_status(
        self,
        table: QTableWidget,
        records: list[ApplicationRecord],
        combo: QComboBox,
    ) -> None:
        record = self._selected_record_from_table(table, records)
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une ligne.")
            return
        status = ApplicationStatus(combo.currentData())
        self.applications.update_status(record.id, status)
        self.refresh()

    def delete_selected_record(self, table: QTableWidget, records: list[ApplicationRecord]) -> None:
        record = self._selected_record_from_table(table, records)
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une ligne.")
            return
        target_name, role = self._target_for_record(record)
        answer = QMessageBox.question(
            self,
            "Supprimer",
            f"Supprimer l'entree {target_name} - {role} ?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.applications.delete(record.id)
        self.refresh()

    def choose_source_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier source",
            str(self.settings.document_source_dir),
        )
        if not selected:
            return
        updated = self.settings_manager.update_document_source_dir(self.settings, Path(selected))
        self._reload_runtime(updated)

    def set_selected_document(self, role: str) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Selection", "Selectionne un document.")
            return
        if role == "cv":
            updated = self.settings_manager.update_selected_documents(
                self.settings,
                selected_cv_path=document.path,
            )
        else:
            updated = self.settings_manager.update_selected_documents(
                self.settings,
                selected_cover_letter_path=document.path,
            )
        self._reload_runtime(updated)

    def open_selected_document(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Selection", "Selectionne un document.")
            return
        self._safe_open_path(document.path, "open_document")

    def open_result_directory(self) -> None:
        self.settings.result_dir.mkdir(parents=True, exist_ok=True)
        self._safe_open_path(self.settings.result_dir, "open_result")

    def open_selected_generated_cv(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return
        self._open_existing_path(record.cv_output_path or record.cv_path, "CV")

    def open_selected_generated_letter(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return
        self._open_existing_path(
            record.cover_letter_output_path or record.cover_letter_source_path,
            "Lettre / proposition",
        )

    def open_selected_mail_file(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return
        mail_path = self._mail_output_path_for_record(record)
        self._open_existing_path(str(mail_path), "Mail")

    def open_trash_directory(self) -> None:
        trash_dir = self.trash_service.trash_dir(self.settings.result_dir)
        trash_dir.mkdir(parents=True, exist_ok=True)
        self._safe_open_path(trash_dir, "open_trash")

    def restore_selected_trash_entry(self) -> None:
        entry = self._selected_trash_entry()
        if entry is None:
            QMessageBox.information(self, "Selection", "Selectionne un fichier en pre-suppression.")
            return
        try:
            restored_path = self.trash_service.restore(
                result_dir=self.settings.result_dir,
                entry_id=entry.entry_id,
            )
        except OSError as exc:
            self.user_logger.error("restore_trash_entry", exc, context=entry.entry_id)
            QMessageBox.warning(self, "Restauration impossible", str(exc))
            return
        QMessageBox.information(self, "Fichier restaure", f"Restaure dans:\n{restored_path}")
        self.refresh()

    def delete_selected_trash_entry(self) -> None:
        entry = self._selected_trash_entry()
        if entry is None:
            QMessageBox.information(self, "Selection", "Selectionne un fichier en pre-suppression.")
            return
        answer = QMessageBox.question(
            self,
            "Suppression definitive",
            f"Supprimer definitivement {entry.original_path.name} ?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.trash_service.delete_permanently(
                result_dir=self.settings.result_dir,
                entry_id=entry.entry_id,
            )
        except OSError as exc:
            self.user_logger.error("delete_trash_entry", exc, context=entry.entry_id)
            QMessageBox.warning(self, "Suppression impossible", str(exc))
            return
        QMessageBox.information(self, "Suppression", "Fichier supprime definitivement.")
        self.refresh()

    def duplicate_selected_document_for_edit(self) -> None:
        if (
            self.current_edit_session is not None
            and self.current_edit_session.status == DocumentEditSessionStatus.OPEN
            and self.current_edit_session.working_copy_path.exists()
        ):
            QMessageBox.information(
                self,
                "Session en cours",
                "Finalise ou annule la modification en cours avant d'ouvrir une nouvelle copie.",
            )
            return

        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Selection", "Selectionne un document.")
            return
        if document.path.suffix.lower() not in {".docx", ".pdf"}:
            QMessageBox.warning(
                self,
                "Document non modifiable",
                "La V1 de modification directe prend en charge DOCX et PDF.",
            )
            return

        target_name, role, action_date = self._document_action_context(document)
        try:
            session = self.edit_session_service.create_working_copy(
                source_path=document.path,
                result_dir=self.settings.result_dir,
                kind=self._document_kind_for_working_copy(document),
                target_name=target_name,
                role_or_mission=role,
                date=action_date,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Copie impossible", str(exc))
            return

        self.current_edit_session = session
        self._append_chat_message("system", f"Copie de travail creee:\n{session.working_copy_path}")
        try:
            self._safe_open_path(session.working_copy_path, "open_working_copy")
        except OSError:
            return
        self.refresh()

    def finalize_current_edit_session(self) -> None:
        if self.current_edit_session is None:
            QMessageBox.information(self, "Session", "Aucune copie de travail active.")
            return

        session = self.edit_session_service.finalize_session(self.current_edit_session)
        self.current_edit_session = session if session.status == DocumentEditSessionStatus.BLOCKED else None
        if session.status == DocumentEditSessionStatus.KEPT:
            QMessageBox.information(
                self,
                "Modification finalisee",
                f"Copie conservee dans:\n{session.working_copy_path}",
            )
        elif session.status == DocumentEditSessionStatus.UNCHANGED_DELETED:
            QMessageBox.information(
                self,
                "Aucune modification",
                "La copie etait inchangee et a ete placee en pre-suppression.",
            )
        elif session.status == DocumentEditSessionStatus.DELETED:
            QMessageBox.information(self, "Session", "La copie de travail n'existe deja plus.")
        else:
            QMessageBox.warning(
                self,
                "Fichier verrouille",
                "Ferme Word ou le lecteur PDF, puis relance la finalisation.",
            )
        self.refresh()

    def cancel_current_edit_session(self) -> None:
        if self.current_edit_session is None:
            QMessageBox.information(self, "Session", "Aucune copie de travail active.")
            return

        session = self.edit_session_service.cancel_session(self.current_edit_session)
        self.current_edit_session = session if session.status == DocumentEditSessionStatus.BLOCKED else None
        if session.status == DocumentEditSessionStatus.BLOCKED:
            QMessageBox.warning(
                self,
                "Fichier verrouille",
                "Ferme Word ou le lecteur PDF, puis relance l'annulation.",
            )
        else:
            QMessageBox.information(
                self,
                "Session annulee",
                "La copie de travail a ete placee en pre-suppression.",
            )
        self.refresh()

    def open_current_target_folder(self) -> None:
        record = self._selected_visible_record()
        if record is not None:
            target_folder = self._target_folder_for_record(record)
        elif self.current_edit_session is not None:
            target_folder = self.current_edit_session.target_folder
        else:
            document = self._selected_document()
            target_name, role, action_date = self._document_action_context(document)
            target_folder = build_target_folder_path(
                self.settings.result_dir,
                target_name=target_name,
                role_or_mission=role,
                date=action_date,
            )
            target_folder.mkdir(parents=True, exist_ok=True)
        self._safe_open_path(target_folder, "open_target_folder")

    def convert_selected_to_pdf(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Selection", "Selectionne un document.")
            return
        extension = document.path.suffix.lower()
        if extension == ".docx":
            source_format = DocumentFormat.DOCX
        else:
            QMessageBox.warning(self, "Conversion", "Selectionne un DOCX.")
            return
        self._convert_document(document, source_format, DocumentFormat.PDF)

    def convert_selected_pdf(self, target_format: DocumentFormat) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Selection", "Selectionne un document.")
            return
        if document.path.suffix.lower() != ".pdf":
            QMessageBox.warning(self, "Conversion", "Selectionne un PDF.")
            return
        self._convert_document(document, DocumentFormat.PDF, target_format)

    def _convert_document(
        self,
        document: ScannedDocument,
        source_format: DocumentFormat,
        target_format: DocumentFormat,
    ) -> None:
        output_path = self._conversion_output_path(document, target_format)
        response = self.converter.convert(
            ConversionRequest(
                source_path=document.path,
                output_path=output_path,
                source_format=source_format,
                target_format=target_format,
            )
        )
        if response.available:
            message = response.message
            if source_format == DocumentFormat.PDF and target_format == DocumentFormat.DOCX:
                message = f"{message}\nReconstruction editable best-effort."
            QMessageBox.information(self, "Conversion", f"{message}\n{response.output_path}")
        else:
            self.user_logger.message(
                "conversion",
                response.message,
                level="ERROR",
                context=str(document.path),
            )
            QMessageBox.warning(self, "Conversion", response.message)
        self.refresh()

    def _conversion_output_path(self, document: ScannedDocument, target_format: DocumentFormat) -> Path:
        target_name, role, action_date = self._document_action_context(document)
        target_folder = build_target_folder_path(
            self.settings.result_dir,
            target_name=target_name,
            role_or_mission=role,
            date=action_date,
        )
        target_folder.mkdir(parents=True, exist_ok=True)
        candidate = target_folder / f"{document.path.stem}_converted.{target_format.value}"
        index = 2
        while candidate.exists():
            candidate = target_folder / f"{document.path.stem}_converted_{index}.{target_format.value}"
            index += 1
        return candidate

    def save_settings_from_form(self) -> None:
        owner = self.settings_github_owner_input.text().strip() or "VicoD3X"
        base_url = self.settings_ai_url_input.text().strip() or self.settings.local_ai_base_url
        updated = replace(
            self.settings,
            github_owner=owner,
            local_ai_base_url=base_url,
            result_dir=result_dir_for(self.settings.document_source_dir),
        )
        self.settings_manager.save(updated)
        self._reload_runtime(self.settings_manager.load())

    def sync_github_projects(self) -> None:
        owner = self.github_owner_input.text().strip() or self.settings.github_owner
        if owner != self.settings.github_owner:
            self.settings = self.settings_manager.update_github_owner(self.settings, owner)
            self._bind_runtime(self.settings)
        result = GitHubProjectSync(
            owner=self.settings.github_owner,
            cache_dir=self.settings.project_context_cache_dir,
        ).sync()
        self.projects = result.projects
        self._populate_projects_table()
        if result.available:
            QMessageBox.information(self, "Projets publics", result.message)
        else:
            QMessageBox.warning(self, "Projets publics", result.message)

    def copy_selected_project_name(self) -> None:
        project = self._selected_project_from_table()
        if project is None:
            QMessageBox.information(self, "Projet public", "Selectionne un projet.")
            return
        QApplication.clipboard().setText(project.repository_name)
        self._append_chat_message("system", f"Nom copie: {project.repository_name}")

    def copy_selected_project_url(self) -> None:
        project = self._selected_project_from_table()
        if project is None:
            QMessageBox.information(self, "Projet public", "Selectionne un projet.")
            return
        QApplication.clipboard().setText(project.url)
        self._append_chat_message("system", f"URL copiee: {project.url}")

    def copy_selected_project_hyperlink(self) -> None:
        project = self._selected_project_from_table()
        if project is None:
            QMessageBox.information(self, "Projet public", "Selectionne un projet.")
            return
        payload = self.project_clipboard.build_payload(project)
        self._copy_project_payload_to_clipboard(payload.plain_text, payload.html)
        self._append_chat_message("system", f"Hyperlien Word copie: {project.repository_name}")

    def open_selected_project(self) -> None:
        project = self._selected_project_from_table()
        if project is None:
            QMessageBox.information(self, "Projet public", "Selectionne un projet.")
            return
        if not project.url:
            QMessageBox.warning(self, "Projet public", "Ce projet n'a pas d'URL.")
            return
        self._open_url(project.url)

    def send_chat_message(self) -> None:
        self.local_ai_status.setText("V1 sans IA: aucun modele local ne demarre")

    def insert_selected_project_from_table(self) -> None:
        selected = (
            self.projects_table.selectionModel().selectedRows()
            if self.projects_table.selectionModel()
            else []
        )
        if not selected:
            QMessageBox.information(self, "Projet public", "Selectionne un projet.")
            return
        item = self.projects_table.item(selected[0].row(), 0)
        if item is None:
            return
        self.use_project_payload(item.data(Qt.ItemDataRole.UserRole))

    def use_project_payload(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            QMessageBox.warning(self, "Projet public", "Projet illisible.")
            return
        project = self._project_from_payload(data)
        if project is None:
            QMessageBox.warning(self, "Projet public", "Projet introuvable dans le cache.")
            return
        self.selected_projects[self._chat_key()] = project
        self._append_chat_message("system", f"Projet public selectionne: {project.repository_name}")
        self._render_chat()

    def adapt_selected_text(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return
        QMessageBox.information(
            self,
            "IA desactivee",
            "L'adaptation automatique de lettre est desactivee pour la V1 sans LLM.",
        )

    def create_selected_document_pack(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return

        target_name, role = self._target_for_record(record)
        target_folder = self._target_folder_for_record(record)
        date_text = record.created_at[:10]
        letter_kind = (
            DocumentKind.FREELANCE_PROPOSAL
            if record.opportunity_type == OpportunityType.FREELANCE
            else DocumentKind.COVER_LETTER
        )
        try:
            cv_path = self._ensure_pack_document(
                target_folder=target_folder,
                kind=DocumentKind.CV,
                target_name=target_name,
                role_or_mission=role,
                date_text=date_text,
                source_path=Path(record.cv_path),
                previous_output_path=Path(record.cv_output_path) if record.cv_output_path else None,
            )
            letter_path = self._ensure_pack_document(
                target_folder=target_folder,
                kind=letter_kind,
                target_name=target_name,
                role_or_mission=role,
                date_text=date_text,
                source_path=Path(record.cover_letter_source_path),
                previous_output_path=(
                    Path(record.cover_letter_output_path)
                    if record.cover_letter_output_path
                    else None
                ),
            )
            draft = self._deterministic_mail_draft(record, target_name, role)
            mail_path = self._save_mail_preview(
                result_dir=target_folder,
                kind=DocumentKind.EMAIL_DRAFT,
                target_name=target_name,
                role_or_mission=role,
                date=date_text,
                content=f"Objet: {draft.subject}\n\nCorps:\n{draft.body}",
            )
        except OSError as exc:
            self.user_logger.error("create_document_pack", exc, context=f"{target_name} - {role}")
            QMessageBox.warning(self, "Pack impossible", str(exc))
            return

        self._append_chat_message(
            "system",
            "\n".join(
                [
                    "Pack documentaire pret:",
                    str(cv_path),
                    str(letter_path),
                    str(mail_path),
                ]
            ),
        )
        QMessageBox.information(self, "Pack cree", f"Pack pret dans:\n{target_folder}")
        self._safe_open_path(target_folder, "open_pack_folder")
        self.refresh()

    def prepare_selected_mail(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return

        target_name, role = self._target_for_record(record)
        draft = self._deterministic_mail_draft(record, target_name, role)

        content = f"Objet: {draft.subject}\n\nCorps:\n{draft.body}"
        target_folder = self._target_folder_for_record(record)
        output = self._save_mail_preview(
            result_dir=target_folder,
            kind=DocumentKind.EMAIL_DRAFT,
            target_name=target_name,
            role_or_mission=role,
            date=record.created_at[:10],
            content=content,
        )
        PreviewDialog(
            title="Mail prepare",
            heading=draft.subject,
            body=draft.body,
            output_path=output,
            parent=self,
        ).exec()
        self._append_chat_message("assistant", f"Mail prepare:\nObjet: {draft.subject}\n\n{draft.body}")

    def _ensure_pack_document(
        self,
        *,
        target_folder: Path,
        kind: DocumentKind,
        target_name: str,
        role_or_mission: str,
        date_text: str,
        source_path: Path,
        previous_output_path: Path | None,
    ) -> Path:
        source_candidate = previous_output_path if previous_output_path and previous_output_path.exists() else source_path
        filename = build_document_filename(
            kind=kind,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date_text,
            extension=source_candidate.suffix or source_path.suffix or "pdf",
        )
        target_path = build_result_path(target_folder, filename)
        if target_path.exists():
            return target_path
        return copy_to_result(source_candidate, target_path)

    def _deterministic_mail_draft(
        self,
        record: ApplicationRecord,
        target_name: str,
        role_or_mission: str,
    ) -> MailDraft:
        if record.opportunity_type == OpportunityType.FREELANCE:
            subject = f"Proposition - {role_or_mission} - Victor Aubry"
            body = "\n\n".join(
                [
                    "Bonjour,",
                    (
                        f"Je vous contacte au sujet de la mission {role_or_mission} "
                        f"pour {target_name}."
                    ),
                    (
                        "Vous trouverez en pieces jointes mon CV ainsi que le document associe. "
                        "Je reste disponible pour echanger sur le besoin, le perimetre et les "
                        "prochaines etapes."
                    ),
                    "Bien cordialement,\nVictor Aubry",
                ]
            )
            return MailDraft(subject=subject, body=body, source="deterministic_v1", available=True)

        subject = f"Candidature - {role_or_mission} - Victor Aubry"
        body = "\n\n".join(
            [
                "Bonjour,",
                (
                    f"Je vous contacte afin de vous transmettre ma candidature pour le poste "
                    f"de {role_or_mission} chez {target_name}."
                ),
                (
                    "Vous trouverez en pieces jointes mon CV ainsi que ma lettre de motivation. "
                    "Je reste disponible pour tout echange complementaire."
                ),
                "Bien cordialement,\nVictor Aubry",
            ]
        )
        return MailDraft(subject=subject, body=body, source="deterministic_v1", available=True)

    def _save_mail_preview(
        self,
        *,
        result_dir: Path,
        kind: DocumentKind,
        target_name: str,
        role_or_mission: str,
        date: str,
        content: str,
    ) -> Path:
        result_dir.mkdir(parents=True, exist_ok=True)
        filename = build_document_filename(
            kind=kind,
            target_name=target_name,
            role_or_mission=role_or_mission,
            date=date,
            extension="txt",
        )
        path = build_result_path(result_dir, filename)
        path.write_text(content, encoding="utf-8")
        return path

    def _ensure_ai_ready(self) -> bool:
        self.local_ai_status.setText("V1 sans IA: aucun modele local ne demarre")
        return False

    def _schedule_ai_idle_stop(self) -> None:
        self.ai_last_activity = monotonic()
        self.ai_idle_timer.start(self.ai_idle_timeout_ms)

    def stop_ai_after_idle(self) -> None:
        if self.ai_server is None:
            return
        if monotonic() - self.ai_last_activity < (self.ai_idle_timeout_ms / 1000):
            self._schedule_ai_idle_stop()
            return
        if self.ai_server.is_online():
            self.ai_server.stop()
        self._update_ai_status()

    def closeEvent(self, event) -> None:
        if self.ai_server is not None and self.ai_server.is_online():
            self.ai_server.stop()
        super().closeEvent(event)

    def _append_chat_message(self, role: str, text: str) -> None:
        key = self._chat_key()
        history = self.chat_histories.setdefault(key, [])
        history.append((role, text))
        self._render_chat()

    def _render_chat(self) -> None:
        key = self._chat_key()
        project = self.selected_projects.get(key)
        if project is None:
            self.project_chip.setText("Projet public selectionne: aucun")
        else:
            self.project_chip.setText(f"Projet public selectionne: {project.repository_name}")

        lines: list[str] = []
        for role, text in self.chat_histories.get(key, []):
            label = {
                "user": "Victor",
                "assistant": "Auto-CV",
                "system": "Contexte",
            }.get(role, role)
            lines.append(f"{label}\n{text}")
        if not lines:
            lines.append("Auto-CV\nAtelier pret. Les actions locales sont disponibles.")
        self.chat_transcript.setPlainText("\n\n".join(lines))
        self.chat_transcript.moveCursor(QTextCursor.MoveOperation.End)

    def _chat_history_text(self) -> str:
        history = self.chat_histories.get(self._chat_key(), [])
        return "\n".join(f"{role}: {text}" for role, text in history[-8:])

    def _chat_key(self) -> str:
        record = self._selected_visible_record()
        return record.id if record else "__global__"

    def _chat_target(self, record: ApplicationRecord | None) -> tuple[str, str]:
        if record is None:
            return "Auto-CV", "Conversation libre"
        return self._target_for_record(record)

    def _selected_project_for_chat(self) -> GitHubProjectContext | None:
        return self.selected_projects.get(self._chat_key())

    def _project_from_payload(self, data: dict) -> GitHubProjectContext | None:
        url = data.get("url", "")
        name = data.get("repository_name", "")
        return next(
            (
                project
                for project in self.projects
                if (url and project.url == url) or (name and project.repository_name == name)
            ),
            None,
        )

    def _selected_visible_record(self) -> ApplicationRecord | None:
        current_view = VIEW_NAMES[self.stack.currentIndex()]
        if current_view == "Candidatures":
            return self._selected_record_from_table(self.jobs_table, self.job_records)
        if current_view == "Freelance":
            return self._selected_record_from_table(self.freelance_table, self.freelance_records)
        return self._selected_record_from_table(self.table, self.current_records)

    def _selected_record_from_table(
        self,
        table: QTableWidget,
        records: list[ApplicationRecord],
    ) -> ApplicationRecord | None:
        selected = table.selectionModel().selectedRows() if table.selectionModel() else []
        if not selected:
            return None
        row = selected[0].row()
        if row < 0 or row >= len(records):
            return None
        return records[row]

    def _selected_document(self) -> ScannedDocument | None:
        selected = self.documents_table.selectionModel().selectedRows() if self.documents_table.selectionModel() else []
        if not selected:
            return None
        row = selected[0].row()
        if row < 0 or row >= len(self.scanned_documents):
            return None
        return self.scanned_documents[row]

    def _selected_project_from_table(self) -> GitHubProjectContext | None:
        selected = (
            self.projects_table.selectionModel().selectedRows()
            if self.projects_table.selectionModel()
            else []
        )
        if not selected:
            return None
        row = selected[0].row()
        if row < 0 or row >= len(self.projects):
            return None
        return self.projects[row]

    def _selected_trash_entry(self) -> TrashEntry | None:
        selected = self.trash_table.selectionModel().selectedRows() if self.trash_table.selectionModel() else []
        if not selected:
            return None
        row = selected[0].row()
        if row < 0 or row >= len(self.trash_entries):
            return None
        return self.trash_entries[row]

    def _trash_reason_label(self, entry: TrashEntry) -> str:
        labels = {
            "canceled_edit": "Modification annulee",
            "unchanged_edit": "Copie inchangee",
            "obsolete": "Obsolete",
        }
        return labels.get(entry.reason.value, entry.reason.value)

    def _trash_expiration_label(self, entry: TrashEntry) -> str:
        try:
            deleted_at = datetime.fromisoformat(entry.deleted_at)
        except ValueError:
            return "30 jours"
        if deleted_at.tzinfo is None:
            deleted_at = deleted_at.replace(tzinfo=UTC)
        expiration = deleted_at.astimezone(UTC) + timedelta(days=self.trash_service.retention_days)
        return expiration.date().isoformat()

    def _context_for_record(self, record: ApplicationRecord) -> str:
        if record.opportunity_type == OpportunityType.JOB:
            offer = self.job_offers.get(record.opportunity_id)
            if offer is None:
                return ""
            return "\n".join(
                [
                    f"Entreprise: {offer.company}",
                    f"Poste: {offer.title}",
                    f"URL: {offer.url}",
                    f"Localisation: {offer.location}",
                    f"Description:\n{offer.description}",
                    f"Notes:\n{offer.notes}",
                ]
            )

        opportunity = self.freelance_opportunities.get(record.opportunity_id)
        if opportunity is None:
            return ""
        return "\n".join(
            [
                f"Client: {opportunity.client}",
                f"Mission: {opportunity.mission_type}",
                f"Besoin:\n{opportunity.need}",
                f"Budget: {opportunity.budget}",
                f"URL: {opportunity.url}",
                f"Notes:\n{opportunity.notes}",
            ]
        )

    def _target_for_record(self, record: ApplicationRecord) -> tuple[str, str]:
        if record.opportunity_type == OpportunityType.JOB:
            offer = self.job_offers.get(record.opportunity_id)
            if offer is None:
                return "Offre inconnue", "-"
            return offer.company, offer.title

        opportunity = self.freelance_opportunities.get(record.opportunity_id)
        if opportunity is None:
            return "Mission inconnue", "-"
        return opportunity.client, opportunity.mission_type

    def _target_folder_for_record(self, record: ApplicationRecord) -> Path:
        target_name, role = self._target_for_record(record)
        expected = build_target_folder_path(
            self.settings.result_dir,
            target_name=target_name,
            role_or_mission=role,
            date=record.created_at[:10],
        )
        if record.export_dir:
            candidate = Path(record.export_dir)
            try:
                if candidate.resolve() != self.settings.result_dir.resolve():
                    expected = candidate
            except OSError:
                expected = candidate
        expected.mkdir(parents=True, exist_ok=True)
        return expected

    def _document_action_context(self, document: ScannedDocument | None) -> tuple[str, str, str]:
        record = self._selected_visible_record()
        if record is not None:
            target_name, role = self._target_for_record(record)
            return target_name, role, record.created_at[:10]

        if document is not None:
            return document.path.stem, "Document", date.today().isoformat()

        return "Auto-CV", "Document", date.today().isoformat()

    def _document_kind_for_working_copy(self, document: ScannedDocument) -> DocumentKind:
        if document.selected_as_cv or document.kind.value == "cv":
            return DocumentKind.CV
        if document.selected_as_cover_letter or document.kind.value == "cover_letter":
            return DocumentKind.COVER_LETTER
        if document.path.suffix.lower() == ".pdf":
            return DocumentKind.CV
        if document.path.suffix.lower() == ".docx":
            return DocumentKind.COVER_LETTER
        return DocumentKind.NOTES

    def _mail_output_path_for_record(self, record: ApplicationRecord) -> Path:
        target_name, role = self._target_for_record(record)
        filename = build_document_filename(
            kind=DocumentKind.EMAIL_DRAFT,
            target_name=target_name,
            role_or_mission=role,
            date=record.created_at[:10],
            extension="txt",
        )
        return build_result_path(self._target_folder_for_record(record), filename)

    def _record_pdf_final_exists(self, record: ApplicationRecord) -> bool:
        target_folder = self._target_folder_for_record(record)
        cv_path = Path(record.cv_output_path) if record.cv_output_path else None
        for path in target_folder.glob("*.pdf"):
            if cv_path is not None:
                try:
                    if path.resolve() == cv_path.resolve():
                        continue
                except OSError:
                    continue
            return True
        return False

    def _exists_label(self, path_text: str | Path) -> str:
        return "OK" if path_text and Path(path_text).exists() else "Absent"

    def _status_label(self, status: ApplicationStatus) -> str:
        return APPLICATION_STATUS_LABELS.get(status.value, status.value)

    def _set_combo_status(self, combo: QComboBox, status: ApplicationStatus) -> None:
        index = combo.findData(status.value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _open_path(self, path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
            return
        subprocess.Popen(["xdg-open", str(path)])

    def _safe_open_path(self, path: Path, action: str) -> bool:
        try:
            self._open_path(path)
        except OSError as exc:
            self.user_logger.error(action, exc, context=str(path))
            QMessageBox.warning(self, "Ouverture impossible", f"Impossible d'ouvrir:\n{path}")
            return False
        return True

    def _open_existing_path(self, path_text: str, label: str) -> None:
        if not path_text:
            QMessageBox.information(self, label, f"Aucun fichier {label.lower()} disponible.")
            return
        path = Path(path_text)
        if not path.exists():
            QMessageBox.warning(self, label, f"Fichier introuvable:\n{path}")
            return
        self._safe_open_path(path, f"open_{label.lower().replace(' ', '_')}")

    def _open_url(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception as exc:
            self.user_logger.error("open_project_url", exc, context=url)
            QMessageBox.warning(self, "Projet public", f"Impossible d'ouvrir:\n{url}")

    def _copy_project_payload_to_clipboard(self, plain_text: str, html: str) -> str:
        clipboard = QApplication.clipboard()
        mime = QMimeData()
        mime.setText(plain_text)
        if html:
            mime.setHtml(html)
        try:
            clipboard.setMimeData(mime)
        except Exception as exc:
            self.user_logger.error("project_clipboard", exc, context=plain_text)
            clipboard.setText(plain_text)
            return "plain"
        return "html"

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #07111f; }
            #Sidebar {
                background: #050a14;
                border: none;
            }
            #AppTitle {
                color: #f8fbff;
                font-size: 22px;
                font-weight: 700;
            }
            #AppSubtitle {
                color: #88a3c4;
                font-size: 12px;
            }
            #NavButton {
                color: #c7d7ea;
                background: transparent;
                text-align: left;
                border: none;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
            }
            #NavButton:checked {
                background: #10233a;
                color: #ffffff;
            }
            #NavButton:hover {
                background: #0d1b2e;
            }
            #SourceStatus {
                color: #7dd3fc;
                font-size: 12px;
                line-height: 16px;
            }
            #PageTitle {
                color: #f5f9ff;
                font-size: 24px;
                font-weight: 700;
            }
            #PageSubtitle {
                color: #91a8c4;
                font-size: 13px;
            }
            #PrimaryButton {
                background: #12a99b;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 9px 14px;
                font-weight: 600;
            }
            #PrimaryButton:hover { background: #19c2b2; }
            #SecondaryButton {
                background: #14263d;
                color: #e5effb;
                border: 1px solid #27405f;
                border-radius: 6px;
                padding: 9px 14px;
                font-weight: 600;
            }
            #SecondaryButton:hover { background: #1b314e; }
            #MetricBox {
                background: #0d1b2e;
                border: 1px solid #203653;
                border-radius: 8px;
            }
            #MetricLabel {
                color: #93a9c4;
                font-size: 12px;
            }
            #MetricValue {
                color: #f8fbff;
                font-size: 24px;
                font-weight: 700;
            }
            #ApplicationTable {
                background: #0b1626;
                alternate-background-color: #0d1b2e;
                border: 1px solid #203653;
                border-radius: 8px;
                gridline-color: #1d304a;
                color: #d9e7f5;
                selection-background-color: #123f52;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background: #10233a;
                color: #adc0d8;
                border: none;
                border-bottom: 1px solid #203653;
                padding: 9px;
                font-size: 12px;
                font-weight: 700;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #172940;
            }
            #DetailPanel {
                background: #081321;
                border-left: 1px solid #203653;
            }
            #PanelTitle {
                color: #86a0bf;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
            }
            #DetailTitle {
                color: #f5f9ff;
                font-size: 18px;
                font-weight: 700;
            }
            #DetailMeta {
                color: #5eead4;
                font-size: 13px;
                font-weight: 600;
            }
            #PathBox {
                background: #0b1626;
                border: 1px solid #203653;
                border-radius: 6px;
                color: #cbdced;
                font-size: 12px;
                padding: 8px;
            }
            #ChatTranscript {
                background: #07111f;
                border: 1px solid #203653;
                border-radius: 8px;
                color: #d9e7f5;
                font-size: 12px;
                padding: 8px;
            }
            #ProjectChip {
                background: #10233a;
                border: 1px solid #24577a;
                border-radius: 6px;
                color: #bae6fd;
                padding: 8px;
                font-weight: 600;
            }
            #ActionsPanel, #FormPanel {
                background: #0b1626;
                border: 1px solid #203653;
                border-radius: 8px;
            }
            #ActionTitle {
                color: #d7e4f4;
                font-size: 13px;
                font-weight: 700;
            }
            #ActionButton {
                background: #101f33;
                color: #e5effb;
                border: 1px solid #2a4260;
                border-radius: 6px;
                padding: 8px 10px;
                font-weight: 600;
            }
            #ActionButton:hover {
                background: #172b45;
            }
            #DangerButton {
                background: #30111f;
                color: #fecdd3;
                border: 1px solid #7f1d1d;
                border-radius: 6px;
                padding: 8px 10px;
                font-weight: 600;
            }
            #DangerButton:hover {
                background: #451a2b;
            }
            #AiStatus {
                color: #93a9c4;
                font-size: 12px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background: #081321;
                border: 1px solid #2a4260;
                border-radius: 6px;
                padding: 8px;
                color: #e5effb;
                selection-background-color: #123f52;
                selection-color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background: #0b1626;
                color: #e5effb;
                selection-background-color: #123f52;
                border: 1px solid #2a4260;
            }
            QLabel {
                color: #d9e7f5;
            }
            """
        )


class MetricBox(QFrame):
    def __init__(self, label: str, value: str) -> None:
        super().__init__()
        self.setObjectName("MetricBox")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self.setMinimumHeight(82)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self.label = QLabel(label)
        self.label.setObjectName("MetricLabel")
        self.value = QLabel(value)
        self.value.setObjectName("MetricValue")
        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


class AssistantTranscript(QTextEdit):
    projectDropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(PROJECT_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasFormat(PROJECT_MIME_TYPE):
            payload = bytes(event.mimeData().data(PROJECT_MIME_TYPE)).decode("utf-8")
            self.projectDropped.emit(payload)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class ProjectTableWidget(QTableWidget):
    def startDrag(self, supported_actions) -> None:
        selected = self.selectionModel().selectedRows() if self.selectionModel() else []
        if not selected:
            return
        item = self.item(selected[0].row(), 0)
        if item is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not payload:
            return

        mime = QMimeData()
        mime.setData(PROJECT_MIME_TYPE, str(payload).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(supported_actions)


def _project_payload(project: GitHubProjectContext) -> str:
    return json.dumps(
        {
            "repository_name": project.repository_name,
            "url": project.url,
        },
        ensure_ascii=False,
    )


class JobApplicationDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nouvelle candidature")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        form = QGridLayout()
        form.setSpacing(10)

        self.company = QLineEdit()
        self.title = QLineEdit()
        self.url = QLineEdit()
        self.location = QLineEdit()
        self.description = QTextEdit()
        self.description.setMinimumHeight(120)
        self.notes = QTextEdit()
        self.notes.setMinimumHeight(80)

        fields = [
            ("Entreprise", self.company),
            ("Poste", self.title),
            ("URL", self.url),
            ("Localisation", self.location),
            ("Description", self.description),
            ("Notes", self.notes),
        ]
        for row, (label, widget) in enumerate(fields):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(widget, row, 1)

        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if not self.company.text().strip() or not self.title.text().strip():
            QMessageBox.warning(self, "Champs requis", "Entreprise et poste sont obligatoires.")
            return
        super().accept()

    def values(self) -> dict[str, str]:
        return {
            "company": self.company.text().strip(),
            "title": self.title.text().strip(),
            "url": self.url.text().strip(),
            "location": self.location.text().strip(),
            "description": self.description.toPlainText().strip(),
            "notes": self.notes.toPlainText().strip(),
        }


class FreelanceOpportunityDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nouvelle mission freelance")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        form = QGridLayout()
        form.setSpacing(10)

        self.client = QLineEdit()
        self.mission_type = QLineEdit()
        self.url = QLineEdit()
        self.budget = QLineEdit()
        self.need = QTextEdit()
        self.need.setMinimumHeight(120)
        self.notes = QTextEdit()
        self.notes.setMinimumHeight(80)

        fields = [
            ("Client / plateforme", self.client),
            ("Type de mission", self.mission_type),
            ("URL", self.url),
            ("Budget / TJM", self.budget),
            ("Besoin", self.need),
            ("Notes", self.notes),
        ]
        for row, (label, widget) in enumerate(fields):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(widget, row, 1)

        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if not self.client.text().strip() or not self.mission_type.text().strip():
            QMessageBox.warning(self, "Champs requis", "Client et type de mission sont obligatoires.")
            return
        super().accept()

    def values(self) -> dict[str, str]:
        return {
            "client": self.client.text().strip(),
            "mission_type": self.mission_type.text().strip(),
            "url": self.url.text().strip(),
            "budget": self.budget.text().strip(),
            "need": self.need.toPlainText().strip(),
            "notes": self.notes.toPlainText().strip(),
        }


class PreviewDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        heading: str,
        body: str,
        output_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        title_label = QLabel(heading)
        title_label.setObjectName("DetailTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        path_label = QLabel(f"Sauvegarde dans: {output_path}")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(body)
        layout.addWidget(text, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def run_desktop_app(settings: AppSettings) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Auto-CV")
    app.setFont(QFont("Segoe UI", 9))
    window = MainWindow(settings)
    window.show()
    return app.exec()
