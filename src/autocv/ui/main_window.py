import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from autocv.domain import ApplicationRecord, ApplicationStatus, OpportunityType
from autocv.i18n.fr_fr import APPLICATION_STATUS_LABELS
from autocv.infrastructure import (
    ApplicationRecordRepository,
    FreelanceOpportunityRepository,
    JobOfferRepository,
    LocalDatabase,
)
from autocv.settings.app_settings import AppSettings
from autocv.use_cases import BootstrapWorkspace, MissingDocumentSourceError, V1ApplicationService


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        if QApplication.instance() is not None:
            QApplication.instance().setFont(QFont("Segoe UI", 9))
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
        self.current_records: list[ApplicationRecord] = []

        self.setWindowTitle("Auto-CV")
        self.resize(1280, 780)
        self.setMinimumSize(1120, 680)

        self._build_actions()
        self._build_ui()
        self._apply_style()
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
        layout.addWidget(self._build_main_panel(), stretch=1)
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
        subtitle = QLabel("Candidatures")
        subtitle.setObjectName("AppSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        for item in ["Tableau de bord", "Candidatures", "Freelance", "Documents", "Projets GitHub", "Paramètres"]:
            button = QPushButton(item)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setChecked(item == "Tableau de bord")
            layout.addWidget(button)

        layout.addStretch()

        self.source_status = QLabel()
        self.source_status.setObjectName("SourceStatus")
        self.source_status.setWordWrap(True)
        layout.addWidget(self.source_status)

        return sidebar

    def _build_main_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        heading_box = QVBoxLayout()
        title = QLabel("Tableau de bord")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Vue rapide des candidatures et sorties prêtes dans Result")
        subtitle.setObjectName("PageSubtitle")
        heading_box.addWidget(title)
        heading_box.addWidget(subtitle)
        header.addLayout(heading_box)
        header.addStretch()

        new_job = QPushButton("+ Candidature")
        new_job.setObjectName("PrimaryButton")
        new_job.clicked.connect(self.create_job_application)
        new_freelance = QPushButton("+ Mission freelance")
        new_freelance.setObjectName("SecondaryButton")
        new_freelance.clicked.connect(self.create_freelance_opportunity)
        header.addWidget(new_job)
        header.addWidget(new_freelance)
        layout.addLayout(header)

        metrics = QHBoxLayout()
        self.metric_total = MetricBox("Total", "0")
        self.metric_ready = MetricBox("Prêt", "0")
        self.metric_sent = MetricBox("Envoyé", "0")
        self.metric_freelance = MetricBox("Freelance", "0")
        for metric in [self.metric_total, self.metric_ready, self.metric_sent, self.metric_freelance]:
            metrics.addWidget(metric)
        layout.addLayout(metrics)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("ApplicationTable")
        self.table.setHorizontalHeaderLabels(
            ["Type", "Cible", "Poste / mission", "Statut", "CV", "Lettre / prop.", "Sortie"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.update_detail_from_selection)
        layout.addWidget(self.table, stretch=1)

        return panel

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("DetailPanel")
        panel.setFixedWidth(360)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)

        title = QLabel("Détail")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        self.detail_title = QLabel("Aucune sélection")
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
        actions_title = QLabel("Actions")
        actions_title.setObjectName("ActionTitle")
        actions_layout.addWidget(actions_title)
        self.adapt_letter_button = QPushButton("Adapter la lettre")
        self.adapt_letter_button.setObjectName("ActionButton")
        self.adapt_letter_button.clicked.connect(self.show_private_engine_message)
        self.prepare_mail_button = QPushButton("Préparer le mail")
        self.prepare_mail_button.setObjectName("ActionButton")
        self.prepare_mail_button.clicked.connect(self.show_private_engine_message)
        self.open_result_button = QPushButton("Ouvrir Result")
        self.open_result_button.setObjectName("ActionButton")
        self.open_result_button.clicked.connect(self.open_result_directory)
        for button in [self.adapt_letter_button, self.prepare_mail_button, self.open_result_button]:
            button.setMinimumHeight(36)
            actions_layout.addWidget(button)
        layout.addWidget(actions)

        layout.addStretch()

        self.local_ai_status = QLabel("IA locale: Qwen3-14B Q4_K_M")
        self.local_ai_status.setObjectName("AiStatus")
        layout.addWidget(self.local_ai_status)

        return panel

    def refresh(self) -> None:
        records = self.applications.list_all()
        self.current_records = records
        self._populate_table(records)
        self._update_metrics(records)
        self._update_source_status()
        self.update_detail_from_selection()

    def _populate_table(self, records: list[ApplicationRecord]) -> None:
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            target_name, role = self._target_for_record(record)
            cells = [
                "Salariat" if record.opportunity_type == OpportunityType.JOB else "Freelance",
                target_name,
                role,
                APPLICATION_STATUS_LABELS.get(record.status.value, record.status.value),
                "OK" if record.cv_output_path else "-",
                "OK" if record.cover_letter_output_path else "-",
                "Result" if record.export_dir else "-",
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                item.setForeground(QColor("#0f172a"))
                if column == 3:
                    item.setForeground(QColor("#0f766e"))
                self.table.setItem(row, column, item)

        self.table.resizeRowsToContents()
        if records:
            self.table.selectRow(0)

    def _update_metrics(self, records: list[ApplicationRecord]) -> None:
        ready = sum(1 for record in records if record.status == ApplicationStatus.READY)
        sent = sum(1 for record in records if record.status == ApplicationStatus.SENT)
        freelance = sum(1 for record in records if record.opportunity_type == OpportunityType.FREELANCE)
        self.metric_total.set_value(str(len(records)))
        self.metric_ready.set_value(str(ready))
        self.metric_sent.set_value(str(sent))
        self.metric_freelance.set_value(str(freelance))

    def _update_source_status(self) -> None:
        if self.bootstrap.document_source_ready:
            text = "Source: GENERIQUE PRO prêt\nSortie: Result prêt"
        else:
            text = "Source: documents manquants\nSortie: Result prêt"
        self.source_status.setText(text)

    def update_detail_from_selection(self) -> None:
        selected = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not selected:
            self.detail_title.setText("Aucune sélection")
            self.detail_meta.setText("")
            self.detail_paths.setPlainText("")
            return

        record = self.current_records[selected[0].row()]
        target_name, role = self._target_for_record(record)
        self.detail_title.setText(f"{target_name}\n{role}")
        self.detail_meta.setText(
            f"{APPLICATION_STATUS_LABELS.get(record.status.value, record.status.value)} · "
            f"{'Salariat' if record.opportunity_type == OpportunityType.JOB else 'Freelance'}"
        )
        self.detail_paths.setPlainText(
            "\n".join(
                [
                    f"CV source:\n{record.cv_path}",
                    "",
                    f"CV renommé:\n{record.cv_output_path or '-'}",
                    "",
                    f"Lettre source:\n{record.cover_letter_source_path}",
                    "",
                    f"Sortie prévue:\n{record.cover_letter_output_path or '-'}",
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

    def open_result_directory(self) -> None:
        path = self.bootstrap.result_dir
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(path)])
        else:
            subprocess.Popen(["open", str(path)])

    def show_private_engine_message(self) -> None:
        QMessageBox.information(
            self,
            "Moteur privé",
            "Le branchement Qwen3 local est la prochaine brique. "
            "Le contrat est prêt, le runner privé reste hors dépôt public.",
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

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #f5f7fa; }
            #Sidebar {
                background: #151923;
                border: none;
            }
            #AppTitle {
                color: #f8fafc;
                font-size: 22px;
                font-weight: 700;
            }
            #AppSubtitle {
                color: #94a3b8;
                font-size: 12px;
            }
            #NavButton {
                color: #cbd5e1;
                background: transparent;
                text-align: left;
                border: none;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
            }
            #NavButton:checked {
                background: #243244;
                color: #ffffff;
            }
            #NavButton:hover {
                background: #1f2937;
            }
            #SourceStatus {
                color: #a7f3d0;
                font-size: 12px;
                line-height: 16px;
            }
            #PageTitle {
                color: #111827;
                font-size: 24px;
                font-weight: 700;
            }
            #PageSubtitle {
                color: #64748b;
                font-size: 13px;
            }
            #PrimaryButton {
                background: #0f766e;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 9px 14px;
                font-weight: 600;
            }
            #PrimaryButton:hover { background: #0d9488; }
            #SecondaryButton {
                background: #e2e8f0;
                color: #111827;
                border: none;
                border-radius: 6px;
                padding: 9px 14px;
                font-weight: 600;
            }
            #SecondaryButton:hover { background: #cbd5e1; }
            #MetricBox {
                background: #ffffff;
                border: 1px solid #dbe3ec;
                border-radius: 8px;
            }
            #MetricLabel {
                color: #64748b;
                font-size: 12px;
            }
            #MetricValue {
                color: #111827;
                font-size: 24px;
                font-weight: 700;
            }
            #ApplicationTable {
                background: #ffffff;
                border: 1px solid #dbe3ec;
                border-radius: 8px;
                gridline-color: #e5e7eb;
                selection-background-color: #d9f4ef;
                selection-color: #111827;
            }
            QHeaderView::section {
                background: #f8fafc;
                color: #475569;
                border: none;
                border-bottom: 1px solid #dbe3ec;
                padding: 9px;
                font-size: 12px;
                font-weight: 700;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eef2f7;
            }
            #DetailPanel {
                background: #ffffff;
                border-left: 1px solid #dbe3ec;
            }
            #PanelTitle {
                color: #64748b;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
            }
            #DetailTitle {
                color: #111827;
                font-size: 18px;
                font-weight: 700;
            }
            #DetailMeta {
                color: #0f766e;
                font-size: 13px;
                font-weight: 600;
            }
            #PathBox {
                background: #f8fafc;
                border: 1px solid #dbe3ec;
                border-radius: 6px;
                color: #334155;
                font-size: 12px;
                padding: 8px;
            }
            #ActionsPanel {
                background: #ffffff;
                border: 1px solid #dbe3ec;
                border-radius: 8px;
            }
            #ActionTitle {
                color: #334155;
                font-size: 13px;
                font-weight: 700;
            }
            #ActionButton {
                background: #f8fafc;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 10px;
                font-weight: 600;
            }
            #ActionButton:hover {
                background: #e2e8f0;
            }
            #AiStatus {
                color: #64748b;
                font-size: 12px;
            }
            QLineEdit, QTextEdit {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                color: #111827;
            }
            QLabel {
                color: #111827;
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


def run_desktop_app(settings: AppSettings) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Auto-CV")
    app.setFont(QFont("Segoe UI", 9))
    window = MainWindow(settings)
    window.show()
    return app.exec()
