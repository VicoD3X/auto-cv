from dataclasses import dataclass
import os

from autocv.i18n.fr_fr import APP_LABELS
from autocv.settings.app_settings import AppSettings
from autocv.use_cases import BootstrapWorkspace


@dataclass(slots=True)
class AppRuntime:
    settings: AppSettings

    def run(self) -> None:
        if os.environ.get("AUTOCV_CONSOLE_ONLY") == "1":
            self._run_console()
            return

        from autocv.ui.main_window import run_desktop_app

        run_desktop_app(self.settings)

    def _run_console(self) -> None:
        bootstrap_result = BootstrapWorkspace(self.settings).run()
        source_status = "source prête" if bootstrap_result.document_source_ready else "source manquante"

        print(
            f"{APP_LABELS['app_ready']} - "
            f"mode={self.settings.default_mode} - "
            f"platform={self.settings.primary_platform} - "
            f"ui={self.settings.user_interface_language} - "
            f"{source_status}"
        )


def create_runtime() -> AppRuntime:
    return AppRuntime(settings=AppSettings.load())
