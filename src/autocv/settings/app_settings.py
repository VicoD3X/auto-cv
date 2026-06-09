from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    app_name: str
    data_dir: Path
    default_mode: str
    primary_platform: str
    ipad_companion_enabled: bool
    repository_language: str
    user_interface_language: str
    generated_content_language: str

    @classmethod
    def load(cls) -> "AppSettings":
        return cls(
            app_name="Auto-CV",
            data_dir=Path.home() / ".autocv",
            default_mode="offline",
            primary_platform="windows-pc",
            ipad_companion_enabled=False,
            repository_language="en-US",
            user_interface_language="fr-FR",
            generated_content_language="fr-FR",
        )
