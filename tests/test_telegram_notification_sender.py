import json
import urllib.error
import urllib.parse

import allure
import pytest

from scripts import send_telegram_notification as sender
from tests.allure_support import given, scenario, then, when

pytestmark = [pytest.mark.unit, pytest.mark.regression]


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


@scenario(
    "Telegram notifier корректно отправляет кириллицу и проверяет ответ API",
    epic="Платформа",
    feature="Инфраструктура и CI",
    story="Операционные уведомления",
    severity=allure.severity_level.CRITICAL,
)
def test_sender_posts_urlencoded_russian_message(monkeypatch) -> None:
    captured = {}

    with given("подготовлено уведомление о деплое на русском языке"):
        def fake_urlopen(request, timeout):
            captured["data"] = request.data
            captured["timeout"] = timeout
            return _Response({"ok": True})
        monkeypatch.setattr(sender.urllib.request, "urlopen", fake_urlopen)

    with when("уведомление отправляется в Telegram"):
        sender.send_message(token="token", chat_id="123", text="Деплой завершён успешно")

    with then("текст передан form-urlencoded без повреждения кириллицы"):
        payload = urllib.parse.parse_qs(captured["data"].decode("utf-8"))
        assert payload["chat_id"] == ["123"]
        assert payload["text"] == ["Деплой завершён успешно"]
        assert captured["timeout"] == 15


@scenario(
    "Telegram notifier повторяет временно неуспешный запрос",
    epic="Платформа",
    feature="Инфраструктура и CI",
    story="Надёжность операционных уведомлений",
    severity=allure.severity_level.CRITICAL,
)
def test_sender_retries_network_error(monkeypatch) -> None:
    attempts = []

    with given("первый запрос Telegram завершился сетевой ошибкой"):
        def fake_urlopen(request, timeout):
            attempts.append(timeout)
            if len(attempts) == 1:
                raise urllib.error.URLError("temporary outage")
            return _Response({"ok": True})
        monkeypatch.setattr(sender.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(sender.time, "sleep", lambda _seconds: None)

    with when("notifier выполняет отправку"):
        sender.send_message(token="token", chat_id="123", text="Worker failed")

    with then("после ошибки выполнена повторная успешная попытка"):
        assert len(attempts) == 2


@scenario(
    "Telegram notifier не маскирует отказ API",
    epic="Платформа",
    feature="Инфраструктура и CI",
    story="Диагностика операционных уведомлений",
    severity=allure.severity_level.CRITICAL,
)
def test_sender_fails_when_telegram_rejects_message(monkeypatch) -> None:
    with given("Telegram API отвечает ok=false"):
        monkeypatch.setattr(sender.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response({"ok": False, "description": "chat not found"}))
        monkeypatch.setattr(sender.time, "sleep", lambda _seconds: None)

    with when("notifier пытается отправить сообщение"):
        with pytest.raises(RuntimeError) as error:
            sender.send_message(token="token", chat_id="wrong", text="Deploy failed", attempts=2)

    with then("ошибка доставки явно попадает в результат шага"):
        assert "failed after 2 attempts" in str(error.value)
