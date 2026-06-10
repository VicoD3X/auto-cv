from dataclasses import replace
import signal
import subprocess

from autocv.ai.server_manager import LocalAiServerManager
from autocv.ai.status import LocalAiStatus
from autocv.settings.app_settings import AppSettings


def _settings(tmp_path):
    source_dir = tmp_path / "GENERIQUE PRO"
    source_dir.mkdir()
    return replace(
        AppSettings.defaults(),
        data_dir=tmp_path / "data",
        document_source_dir=source_dir,
        result_dir=source_dir / "Auto-CV" / "Result",
        project_context_cache_dir=tmp_path / "data" / "project_context",
    )


def test_ai_server_manager_does_not_start_when_online(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    manager = LocalAiServerManager(settings)
    monkeypatch.setattr(
        "autocv.ai.server_manager.check_local_ai_status",
        lambda base_url: LocalAiStatus(online=True, message="online"),
    )

    def fail_popen(*args, **kwargs):
        raise AssertionError("subprocess.Popen should not be called")

    monkeypatch.setattr("autocv.ai.server_manager.subprocess.Popen", fail_popen)

    result = manager.ensure_running()

    assert result.available is True
    assert result.message == "IA locale online."


def test_ai_server_manager_requires_runner(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    manager = LocalAiServerManager(settings)
    monkeypatch.setattr(
        "autocv.ai.server_manager.check_local_ai_status",
        lambda base_url: LocalAiStatus(online=False, message="offline"),
    )

    result = manager.ensure_running()

    assert result.available is False
    assert "llama-server introuvable" in result.message


def test_ai_server_manager_starts_then_rechecks_endpoint(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    manager = LocalAiServerManager(settings)
    _install_fake_ai_files(manager)
    statuses = iter(
        [
            LocalAiStatus(online=False, message="offline"),
            LocalAiStatus(online=True, message="online"),
        ]
    )
    monkeypatch.setattr(
        "autocv.ai.server_manager.check_local_ai_status",
        lambda base_url: next(statuses),
    )

    monkeypatch.setattr("autocv.ai.server_manager.subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr("autocv.ai.server_manager.time.sleep", lambda seconds: None)
    monkeypatch.setattr(LocalAiServerManager, "_warmup", lambda self: True)

    result = manager.ensure_running()

    assert result.available is True
    assert result.message == "Auto-CV IA online: http://127.0.0.1:8080/v1"
    assert manager.pid_file.read_text(encoding="ascii") == "1234"


def test_ai_server_manager_handles_start_timeout(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    manager = LocalAiServerManager(settings)
    _install_fake_ai_files(manager)
    monkeypatch.setattr(
        "autocv.ai.server_manager.check_local_ai_status",
        lambda base_url: LocalAiStatus(online=False, message="offline"),
    )
    monkeypatch.setattr("autocv.ai.server_manager.subprocess.Popen", lambda *args, **kwargs: FakeProcess())

    result = manager.ensure_running(timeout_seconds=0)

    assert result.available is False
    assert "Demarrage IA trop long" in result.message


def test_ai_server_manager_stop_kills_recorded_pid(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    manager = LocalAiServerManager(settings)
    manager.runtime_dir.mkdir(parents=True)
    manager.pid_file.write_text("1234", encoding="ascii")
    killed = {}
    monkeypatch.setattr(
        "autocv.ai.server_manager.check_local_ai_status",
        lambda base_url: LocalAiStatus(online=False, message="offline"),
    )

    def fake_kill(pid, sig):
        killed["pid"] = pid
        killed["sig"] = sig

    monkeypatch.setattr("autocv.ai.server_manager.os.kill", fake_kill)

    result = manager.stop()

    assert result.available is True
    assert result.message == "Auto-CV IA stopped."
    assert killed == {"pid": 1234, "sig": signal.SIGTERM}
    assert manager.pid_file.exists() is False


def test_ai_server_manager_fallback_stop_uses_taskkill(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    manager = LocalAiServerManager(settings)
    monkeypatch.setattr(
        "autocv.ai.server_manager.check_local_ai_status",
        lambda base_url: LocalAiStatus(online=True, message="online"),
    )

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="stopped", stderr="")

    monkeypatch.setattr("autocv.ai.server_manager.subprocess.run", fake_run)

    result = manager.stop()

    assert result.available is True
    assert result.message == "stopped"


class FakeProcess:
    pid = 1234
    returncode = None

    def poll(self):
        return None


def _install_fake_ai_files(manager: LocalAiServerManager) -> None:
    manager.runner_path.parent.mkdir(parents=True)
    manager.runner_path.write_text("runner", encoding="utf-8")
    manager.model_path.parent.mkdir(parents=True)
    manager.model_path.write_text("model", encoding="utf-8")
