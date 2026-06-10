from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import time

import httpx

from autocv.ai.status import check_local_ai_status
from autocv.settings.app_settings import AppSettings


@dataclass(frozen=True, slots=True)
class LocalAiServerResult:
    available: bool
    message: str


class LocalAiServerManager:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.runner_path = (
            settings.data_dir
            / "runners"
            / "llama.cpp"
            / "b9591"
            / "bin"
            / "llama-server.exe"
        )
        self.model_path = (
            settings.data_dir
            / "models"
            / "Qwen3-14B-GGUF"
            / f"{settings.local_ai_model_name}-{settings.local_ai_default_quantization}.gguf"
        )
        self.log_dir = settings.data_dir / "logs"
        self.runtime_dir = settings.data_dir / "runtime"
        self.pid_file = self.runtime_dir / "qwen-llama-server.pid"
        self.stdout_log = self.log_dir / "qwen-llama-server.out.log"
        self.stderr_log = self.log_dir / "qwen-llama-server.err.log"

    def is_online(self) -> bool:
        return check_local_ai_status(self.settings.local_ai_base_url).online

    def ensure_running(self, timeout_seconds: int = 240) -> LocalAiServerResult:
        if self.is_online():
            return LocalAiServerResult(
                available=True,
                message="IA locale online.",
            )
        if not self.runner_path.exists():
            return LocalAiServerResult(
                available=False,
                message=f"llama-server introuvable: {self.runner_path}",
            )
        if not self.model_path.exists():
            return LocalAiServerResult(
                available=False,
                message=f"Modele Qwen introuvable: {self.model_path}",
            )

        try:
            process = self._start_process()
        except OSError as exc:
            return LocalAiServerResult(
                available=False,
                message=f"Demarrage IA impossible: {exc}",
            )

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.is_online():
                self._warmup()
                return LocalAiServerResult(
                    available=True,
                    message="Auto-CV IA online: http://127.0.0.1:8080/v1",
                )
            if process.poll() is not None:
                return LocalAiServerResult(
                    available=False,
                    message=self._startup_failure_message(process.returncode),
                )
            time.sleep(2)

        return LocalAiServerResult(
            available=False,
            message="Demarrage IA trop long. Relance l'action dans quelques secondes.",
        )

    def stop(self, timeout_seconds: int = 30) -> LocalAiServerResult:
        pid = self._read_pid()
        if pid is None:
            if not self.is_online():
                return LocalAiServerResult(available=True, message="Auto-CV IA deja arretee.")
            return self._fallback_stop(timeout_seconds)

        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError as exc:
            return LocalAiServerResult(
                available=False,
                message=f"Arret IA impossible: {exc}",
            )

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not self.is_online():
                self.pid_file.unlink(missing_ok=True)
                return LocalAiServerResult(available=True, message="Auto-CV IA stopped.")
            time.sleep(0.5)

        return LocalAiServerResult(available=False, message="Arret IA trop long.")

    def _start_process(self) -> subprocess.Popen:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        args = [
            str(self.runner_path),
            "-m",
            str(self.model_path),
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "--ctx-size",
            "4096",
            "--parallel",
            "1",
            "--n-gpu-layers",
            "99",
            "--flash-attn",
            "auto",
            "--cache-type-k",
            "q8_0",
            "--cache-type-v",
            "q8_0",
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with (
            self.stdout_log.open("ab") as stdout,
            self.stderr_log.open("ab") as stderr,
        ):
            process = subprocess.Popen(
                args,
                cwd=self.runner_path.parent,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                creationflags=creationflags,
            )
        self.pid_file.write_text(str(process.pid), encoding="ascii")
        return process

    def _warmup(self) -> bool:
        payload = {
            "model": self.model_path.name,
            "messages": [
                {
                    "role": "system",
                    "content": "Reponds sans raisonnement. Donne uniquement la reponse finale.",
                },
                {"role": "user", "content": "/no_think\nReponds exactement: OK"},
            ],
            "max_tokens": 8,
            "temperature": 0.1,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        try:
            timeout = httpx.Timeout(connect=2.0, read=180.0, write=10.0, pool=5.0)
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{self.settings.local_ai_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                )
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    def _read_pid(self) -> int | None:
        if not self.pid_file.exists():
            return None
        try:
            return int(self.pid_file.read_text(encoding="ascii").strip())
        except ValueError:
            self.pid_file.unlink(missing_ok=True)
            return None

    def _startup_failure_message(self, returncode: int | None) -> str:
        log_tail = _tail_text(self.stderr_log, max_lines=50)
        if log_tail:
            return f"Demarrage IA interrompu (code {returncode}).\n{log_tail}"
        return f"Demarrage IA interrompu (code {returncode})."

    def _fallback_stop(self, timeout_seconds: int) -> LocalAiServerResult:
        if os.name != "nt":
            return LocalAiServerResult(
                available=False,
                message="Serveur IA online mais PID Auto-CV introuvable.",
            )
        try:
            result = subprocess.run(
                ["taskkill", "/IM", "llama-server.exe", "/F"],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return LocalAiServerResult(available=False, message=f"Arret IA impossible: {exc}")
        self.pid_file.unlink(missing_ok=True)
        return LocalAiServerResult(
            available=result.returncode == 0,
            message=(result.stdout or result.stderr or "Auto-CV IA stopped.").strip(),
        )


def default_qwen_script_path(data_dir: Path) -> Path:
    return data_dir / "start-qwen-autocv.ps1"


def _tail_text(path: Path, *, max_lines: int) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-max_lines:])
