from datetime import UTC, datetime
from pathlib import Path
import traceback


class UserActionLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path

    def error(self, action: str, error: BaseException, *, context: str = "") -> None:
        details = "".join(traceback.format_exception_only(type(error), error)).strip()
        self.message(action, details, level="ERROR", context=context)

    def message(self, action: str, message: str, *, level: str = "INFO", context: str = "") -> None:
        timestamp = datetime.now(UTC).isoformat(timespec="seconds")
        context_part = f" | context={context}" if context else ""
        line = f"{timestamp} | {level} | {action} | {message}{context_part}\n"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(line)
