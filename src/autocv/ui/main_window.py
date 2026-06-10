from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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

from autocv.ai import check_local_ai_status
from autocv.conversion import ConversionRequest, DocumentFormat, LocalDocumentConverter
from autocv.documents import DocumentScanner, ScannedDocument
from autocv.documents.naming import DocumentKind
from autocv.domain import ApplicationRecord, ApplicationStatus, OpportunityType
from autocv.i18n.fr_fr import APPLICATION_STATUS_LABELS
from autocv.infrastructure import (
    ApplicationRecordRepository,
    FreelanceOpportunityRepository,
    JobOfferRepository,
    LocalDatabase,
)
from autocv.mail import MailDraftRequest
from autocv.projects import GitHubProjectContext, GitHubProjectSync
from autocv.settings.app_settings import AppSettings, SettingsManager, result_dir_for
from autocv.use_cases import BootstrapWorkspace, MissingDocumentSourceError, V1AiService, V1ApplicationService


VIEW_NAMES = [
    "Tableau de bord",
    "Candidatures",
    "Freelance",
    "Documents",
    "Projets GitHub",
    "Parametres",
]


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        if QApplication.instance() is not None:
            QApplication.instance().setFont(QFont("Segoe UI", 9))

        self.settings_manager = SettingsManager(settings.data_dir / "settings.json")
        self.converter = LocalDocumentConverter()
        self.ai_service = V1AiService()

        self.current_records: list[ApplicationRecord] = []
        self.job_records: list[ApplicationRecord] = []
        self.freelance_records: list[ApplicationRecord] = []
        self.scanned_documents: list[ScannedDocument] = []
        self.projects: list[GitHubProjectContext] = []
        self.nav_buttons: dict[str, QPushButton] = {}

        self._bind_runtime(settings)

        self.setWindowTitle("Auto-CV")
        self.resize(1280, 780)
        self.setMinimumSize(1120, 680)

        self._build_actions()
        self._build_ui()
        self._apply_style()
        self.refresh()

    def _bind_runtime(self, settings: AppSettings) -> None:
        self.settings = settings
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

    def _reload_runtime(self, settings: AppSettings) -> None:
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
        layout.addWidget(self._build_detail_panel())

        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)

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
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.view_indexes: dict[str, int] = {}
        builders = [
            self._build_dashboard_view,
            self._build_jobs_view,
            self._build_freelance_view,
            self._build_documents_view,
            self._build_projects_view,
            self._build_settings_view,
        ]
        for name, builder in zip(VIEW_NAMES, builders, strict=True):
            self.view_indexes[name] = self.stack.addWidget(builder())
        layout.addWidget(self.stack)
        return container

    def _new_page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout, QHBoxLayout]:
        page = QWidget()
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
        set_cv = QPushButton("Definir comme CV")
        set_cv.setObjectName("ActionButton")
        set_cv.clicked.connect(lambda: self.set_selected_document("cv"))
        set_letter = QPushButton("Definir comme lettre")
        set_letter.setObjectName("ActionButton")
        set_letter.clicked.connect(lambda: self.set_selected_document("letter"))
        open_file = QPushButton("Ouvrir")
        open_file.setObjectName("ActionButton")
        open_file.clicked.connect(self.open_selected_document)
        open_result = QPushButton("Ouvrir Result")
        open_result.setObjectName("ActionButton")
        open_result.clicked.connect(self.open_result_directory)
        for button in [set_cv, set_letter, open_file, open_result]:
            selection_actions.addWidget(button)
        selection_actions.addStretch()
        layout.addLayout(selection_actions)

        conversion_actions = QHBoxLayout()
        to_pdf = QPushButton("DOCX/XLSX -> PDF")
        to_pdf.setObjectName("ActionButton")
        to_pdf.clicked.connect(self.convert_selected_to_pdf)
        to_docx = QPushButton("PDF -> DOCX")
        to_docx.setObjectName("ActionButton")
        to_docx.clicked.connect(lambda: self.convert_selected_pdf(DocumentFormat.DOCX))
        to_xlsx = QPushButton("PDF -> XLSX")
        to_xlsx.setObjectName("ActionButton")
        to_xlsx.clicked.connect(lambda: self.convert_selected_pdf(DocumentFormat.XLSX))
        for button in [to_pdf, to_docx, to_xlsx]:
            conversion_actions.addWidget(button)
        conversion_actions.addStretch()
        layout.addLayout(conversion_actions)
        return page

    def _build_projects_view(self) -> QWidget:
        page, layout, header = self._new_page(
            "Projets GitHub",
            "Cache local du contexte public VicoD3X pour aider les ajustements IA",
        )

        self.github_owner_input = QLineEdit()
        self.github_owner_input.setFixedWidth(160)
        sync_button = QPushButton("Synchroniser")
        sync_button.setObjectName("PrimaryButton")
        sync_button.clicked.connect(self.sync_github_projects)
        header.addWidget(QLabel("Owner"))
        header.addWidget(self.github_owner_input)
        header.addWidget(sync_button)

        self.projects_table = QTableWidget(0, 5)
        self.projects_table.setObjectName("ApplicationTable")
        self.projects_table.setHorizontalHeaderLabels(["Projet", "Langage", "Topics", "Description", "URL"])
        self._configure_table(self.projects_table)
        layout.addWidget(self.projects_table, stretch=1)
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
        self.settings_ai_url_input = QLineEdit()

        form.addRow("Dossier source", self.settings_source_dir)
        form.addRow("Dossier Result", self.settings_result_dir)
        form.addRow("CV source", self.settings_cv_path)
        form.addRow("Lettre source", self.settings_letter_path)
        form.addRow("GitHub owner", self.settings_github_owner_input)
        form.addRow("IA locale URL", self.settings_ai_url_input)
        layout.addWidget(form_panel)
        layout.addStretch()
        return page

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("DetailPanel")
        panel.setFixedWidth(360)

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
        self.detail_paths.setMinimumHeight(180)
        layout.addWidget(self.detail_paths)

        actions = QFrame()
        actions.setObjectName("ActionsPanel")
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(12, 12, 12, 12)
        actions_layout.setSpacing(8)
        actions_title = QLabel("Actions IA")
        actions_title.setObjectName("ActionTitle")
        actions_layout.addWidget(actions_title)
        self.adapt_letter_button = QPushButton("Adapter la lettre")
        self.adapt_letter_button.setObjectName("ActionButton")
        self.adapt_letter_button.clicked.connect(self.adapt_selected_text)
        self.prepare_mail_button = QPushButton("Preparer le mail")
        self.prepare_mail_button.setObjectName("ActionButton")
        self.prepare_mail_button.clicked.connect(self.prepare_selected_mail)
        self.open_result_button = QPushButton("Ouvrir Result")
        self.open_result_button.setObjectName("ActionButton")
        self.open_result_button.clicked.connect(self.open_result_directory)
        for button in [self.adapt_letter_button, self.prepare_mail_button, self.open_result_button]:
            button.setMinimumHeight(36)
            actions_layout.addWidget(button)
        layout.addWidget(actions)

        layout.addStretch()

        self.local_ai_status = QLabel("IA locale: verification...")
        self.local_ai_status.setObjectName("AiStatus")
        self.local_ai_status.setWordWrap(True)
        layout.addWidget(self.local_ai_status)

        return panel

    def _configure_table(self, table: QTableWidget) -> None:
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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
        self.projects = GitHubProjectSync(
            owner=self.settings.github_owner,
            cache_dir=self.settings.project_context_cache_dir,
        ).load_cached()

        self._populate_dashboard_table(records)
        self._populate_records_table(self.jobs_table, self.job_records)
        self._populate_records_table(self.freelance_table, self.freelance_records)
        self._populate_documents_table()
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

    def _populate_projects_table(self) -> None:
        self.projects_table.setRowCount(len(self.projects))
        for row, project in enumerate(self.projects):
            cells = [
                project.repository_name,
                ", ".join(project.languages) or "-",
                ", ".join(project.topics) or "-",
                project.description,
                project.url,
            ]
            self._set_table_row(self.projects_table, row, cells, project.url)
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
            item.setForeground(QColor("#0f172a"))
            if "statut" in (table.horizontalHeaderItem(column).text().lower()):
                item.setForeground(QColor("#0f766e"))
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
        self.settings_ai_url_input.setText(self.settings.local_ai_base_url)
        self.github_owner_input.setText(self.settings.github_owner)

    def _update_ai_status(self) -> None:
        status = check_local_ai_status(self.settings.local_ai_base_url)
        if status.online:
            self.local_ai_status.setText("IA locale: online")
        else:
            self.local_ai_status.setText("IA locale: offline")
        self.adapt_letter_button.setEnabled(status.online)
        self.prepare_mail_button.setEnabled(status.online)

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
        self._open_path(document.path)

    def open_result_directory(self) -> None:
        self.settings.result_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(self.settings.result_dir)

    def convert_selected_to_pdf(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Selection", "Selectionne un document.")
            return
        extension = document.path.suffix.lower()
        if extension == ".docx":
            source_format = DocumentFormat.DOCX
        elif extension in {".xlsx", ".xls"}:
            source_format = DocumentFormat.XLSX
        else:
            QMessageBox.warning(self, "Conversion", "Selectionne un DOCX, XLSX ou XLS.")
            return
        self._convert_document(document.path, source_format, DocumentFormat.PDF)

    def convert_selected_pdf(self, target_format: DocumentFormat) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Selection", "Selectionne un document.")
            return
        if document.path.suffix.lower() != ".pdf":
            QMessageBox.warning(self, "Conversion", "Selectionne un PDF.")
            return
        self._convert_document(document.path, DocumentFormat.PDF, target_format)

    def _convert_document(
        self,
        source_path: Path,
        source_format: DocumentFormat,
        target_format: DocumentFormat,
    ) -> None:
        output_path = self._conversion_output_path(source_path, target_format)
        response = self.converter.convert(
            ConversionRequest(
                source_path=source_path,
                output_path=output_path,
                source_format=source_format,
                target_format=target_format,
            )
        )
        if response.available:
            QMessageBox.information(self, "Conversion", f"{response.message}\n{response.output_path}")
        else:
            QMessageBox.warning(self, "Conversion", response.message)
        self.refresh()

    def _conversion_output_path(self, source_path: Path, target_format: DocumentFormat) -> Path:
        self.settings.result_dir.mkdir(parents=True, exist_ok=True)
        candidate = self.settings.result_dir / f"{source_path.stem}_converted.{target_format.value}"
        index = 2
        while candidate.exists():
            candidate = self.settings.result_dir / f"{source_path.stem}_converted_{index}.{target_format.value}"
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
            QMessageBox.information(self, "GitHub", result.message)
        else:
            QMessageBox.warning(self, "GitHub", result.message)

    def adapt_selected_text(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return

        target_name, role = self._target_for_record(record)
        context = self._context_for_record(record)
        response = self.ai_service.adapt_application_text(
            record=record,
            target_name=target_name,
            role_or_mission=role,
            context=context,
        )
        if not response.available:
            QMessageBox.warning(self, "IA locale indisponible", response.text)
            return

        kind = (
            DocumentKind.FREELANCE_PROPOSAL
            if record.opportunity_type == OpportunityType.FREELANCE
            else DocumentKind.COVER_LETTER
        )
        output = self.ai_service.save_preview(
            result_dir=self.settings.result_dir,
            kind=kind,
            target_name=target_name,
            role_or_mission=role,
            date=record.created_at[:10],
            content=response.text,
        )
        PreviewDialog(
            title="Texte genere",
            heading=f"{target_name} - {role}",
            body=response.text,
            output_path=output,
            parent=self,
        ).exec()

    def prepare_selected_mail(self) -> None:
        record = self._selected_visible_record()
        if record is None:
            QMessageBox.information(self, "Selection", "Selectionne une candidature ou une mission.")
            return

        target_name, role = self._target_for_record(record)
        draft = self.ai_service.draft_mail(
            request=MailDraftRequest(
                opportunity_type=record.opportunity_type,
                target_name=target_name,
                role_or_mission=role,
                context=self._context_for_record(record),
                attachment_paths=(
                    record.cv_output_path or record.cv_path,
                    record.cover_letter_output_path or record.cover_letter_source_path,
                ),
            )
        )
        if not draft.available:
            QMessageBox.warning(self, "IA locale indisponible", draft.body)
            return

        content = f"Objet: {draft.subject}\n\nCorps:\n{draft.body}"
        output = self.ai_service.save_preview(
            result_dir=self.settings.result_dir,
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
