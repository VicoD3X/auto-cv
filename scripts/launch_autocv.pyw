from pathlib import Path
import ctypes
import os
import sys
import traceback


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, "Auto-CV", 0x10)


def _write_error_log(error: BaseException) -> Path:
    log_dir = Path.home() / ".autocv" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "launcher-error.log"
    log_path.write_text(
        "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        encoding="utf-8",
    )
    return log_path


def main() -> None:
    os.chdir(ROOT)
    sys.path.insert(0, str(SRC))

    try:
        from autocv.app.main import main as run_app

        run_app()
    except Exception as exc:
        log_path = _write_error_log(exc)
        _show_error(f"Auto-CV n'a pas pu demarrer.\n\nLog: {log_path}")


if __name__ == "__main__":
    main()

