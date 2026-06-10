from autocv.app.user_log import UserActionLogger


def test_user_action_logger_writes_error_log(tmp_path) -> None:
    log_path = tmp_path / "logs" / "autocv.log"
    logger = UserActionLogger(log_path)

    logger.error("conversion", RuntimeError("boom"), context="document.docx")

    content = log_path.read_text(encoding="utf-8")
    assert "ERROR | conversion" in content
    assert "RuntimeError: boom" in content
    assert "context=document.docx" in content
