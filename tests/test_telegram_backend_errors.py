from telegram_bot.services.backend_errors import friendly_backend_error


def test_friendly_backend_error_for_connection_failure() -> None:
    assert (
        friendly_backend_error("All connection attempts failed")
        == "Backend сейчас недоступен. Попробуй еще раз через минуту."
    )


def test_friendly_backend_error_for_timeout() -> None:
    assert (
        friendly_backend_error("ReadTimeout timed out")
        == "Backend не ответил вовремя. Попробуй еще раз через минуту."
    )


def test_friendly_backend_error_for_bad_response() -> None:
    assert (
        friendly_backend_error("bad response")
        == "Backend вернул неожиданный ответ. Попробуй позже."
    )
