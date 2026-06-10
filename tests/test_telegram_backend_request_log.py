import logging

from telegram_bot.services import backend_request_log


def test_log_backend_success_has_safe_fields(caplog) -> None:
    caplog.set_level(logging.INFO, logger=backend_request_log.logger.name)

    backend_request_log.log_backend_success(
        operation="user_routes.build",
        base_url="http://backend",
        started=backend_request_log.request_started(),
        status_code=200,
    )

    message = caplog.records[0].getMessage()
    assert "operation=user_routes.build" in message
    assert "base_url=http://backend" in message
    assert "status=200" in message
    assert "duration_ms=" in message


def test_log_backend_error_has_error_type_only(caplog) -> None:
    caplog.set_level(logging.WARNING, logger=backend_request_log.logger.name)

    backend_request_log.log_backend_error(
        operation="user_routes.correct",
        base_url="http://backend",
        started=backend_request_log.request_started(),
        error=ValueError("secret payload"),
    )

    message = caplog.records[0].getMessage()
    assert "operation=user_routes.correct" in message
    assert "error_type=ValueError" in message
    assert "secret payload" not in message
