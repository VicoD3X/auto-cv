from dataclasses import dataclass

from autocv.i18n.fr_fr import APP_LABELS
from autocv.settings.app_settings import AppSettings


@dataclass(slots=True)
class AppRuntime:
    settings: AppSettings

    def run(self) -> None:
        # The real PySide6 application will be attached once the first UI screen is defined.
        print(
            f"{APP_LABELS['app_ready']} - "
            f"mode={self.settings.default_mode} - "
            f"platform={self.settings.primary_platform} - "
            f"ui={self.settings.user_interface_language}"
        )


def create_runtime() -> AppRuntime:
    return AppRuntime(settings=AppSettings.load())
