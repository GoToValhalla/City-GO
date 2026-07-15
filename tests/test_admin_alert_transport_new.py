"""Transport-level regression coverage for services/admin_alert_service.py,
covering the production defect: admin_alert_send_failed: HTTP Error 401:
Unauthorized.

Root cause (proven by repository inspection, not assumed): the code path is
correct — every send_admin_alert() call site (import worker, import
pipeline, debug reports) shares one canonical token/chat_id resolution and
one Telegram sendMessage transport. Alert failures were already caught and
non-fatal, and admin_alert_send_failed was already logged truthfully. A 401
from Telegram for a real token means the token itself is invalid — most
likely the production container's .env TELEGRAM_BOT_TOKEN/BOT_TOKEN has
drifted from the separately-validated secrets.TELEGRAM_BOT_TOKEN used by
GitHub Actions' own workflow-level Telegram notifications (deploy.yml never
writes TELEGRAM_BOT_TOKEN into /srv/app/.env — only TELEGRAM_MINI_APP_URL).
This is a production configuration defect, not a code defect.

Two real code gaps were closed defensively: (1) .strip() on token/chat_id,
since pydantic-settings does not trim .env values and a stray
newline/space silently turns a valid token into an invalid one (the same
class of bug already fixed for city_slug propagation this session), and
(2) explicit token redaction on the failure path, since the request URL
embeds the raw token (Telegram's own auth scheme puts it in the URL path,
not a header) and exception string() is not a documented guarantee never to
echo it.
"""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

from services.admin_alert_service import _redact_token, send_admin_alert


def _settings(**overrides):
    defaults = {"telegram_bot_token": "", "bot_token": "", "telegram_chat_id": ""}
    defaults.update(overrides)
    return defaults


def test_successful_alert_delivery_new():
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "real-token-123"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"{}"

        result = send_admin_alert(title="Import pipeline finished", message="ok", level="info")

        assert result == {"sent": True}
        request = mock_urlopen.call_args[0][0]
        assert request.full_url == "https://api.telegram.org/botreal-token-123/sendMessage"
        assert request.get_method() == "POST"


def test_401_unauthorized_is_reported_truthfully_and_non_fatal_new():
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "bad-token"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.telegram.org/botbad-token/sendMessage",
            code=401, msg="Unauthorized", hdrs=None, fp=None,
        )

        result = send_admin_alert(title="Import pipeline failed", message="boom", level="error")

        assert result["sent"] is False
        assert "401" in result["reason"]
        assert "Unauthorized" in result["reason"]


def test_missing_token_does_not_attempt_send_and_is_reported_new():
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = ""
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"

        result = send_admin_alert(title="Import pipeline failed", message="boom")

        assert result == {"sent": False, "reason": "not_configured"}
        mock_urlopen.assert_not_called()


def test_missing_chat_id_does_not_attempt_send_new():
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "real-token"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = ""

        result = send_admin_alert(title="Import pipeline failed", message="boom")

        assert result == {"sent": False, "reason": "not_configured"}
        mock_urlopen.assert_not_called()


def test_token_with_trailing_whitespace_from_env_is_normalized_new():
    """A .env value like TELEGRAM_BOT_TOKEN=abc123\\n (trailing newline
    surviving into the process env) must not silently produce a malformed
    URL/401 — the same defect class already found in city_slug this
    session."""
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "  real-token-123\n"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = " -100555 \n"
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"{}"

        result = send_admin_alert(title="Import pipeline finished", message="ok", level="info")

        assert result == {"sent": True}
        request = mock_urlopen.call_args[0][0]
        assert request.full_url == "https://api.telegram.org/botreal-token-123/sendMessage"


def test_transport_network_failure_is_non_fatal_new():
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "real-token"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"
        mock_urlopen.side_effect = urllib.error.URLError("timed out")

        result = send_admin_alert(title="Import pipeline failed", message="boom")

        assert result["sent"] is False
        assert "timed out" in result["reason"]


def test_secret_redaction_strips_token_from_error_text_new():
    text = _redact_token("HTTP Error 401 for https://api.telegram.org/botSECRET123/sendMessage", "SECRET123")
    assert "SECRET123" not in text
    assert "***REDACTED***" in text


def test_secret_redaction_applied_on_send_failure_new():
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "SECRET-TOKEN-XYZ"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"

        class LeakyError(Exception):
            def __str__(self) -> str:
                return "connection to https://api.telegram.org/botSECRET-TOKEN-XYZ/sendMessage failed"

        mock_urlopen.side_effect = LeakyError()

        result = send_admin_alert(title="Import pipeline failed", message="boom")

        assert "SECRET-TOKEN-XYZ" not in result["reason"]
        assert "***REDACTED***" in result["reason"]


def test_alert_failure_does_not_raise_or_alter_caller_flow_new():
    """Callers (import worker, import pipeline) must be able to call
    send_admin_alert() unconditionally without try/except of their own —
    any exception from the transport must be swallowed inside the
    function."""
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "real-token"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"
        mock_urlopen.side_effect = RuntimeError("unexpected transport crash")

        result = send_admin_alert(title="Import pipeline failed", message="boom", job_id=42)

        assert result["sent"] is False
        assert "unexpected transport crash" in result["reason"]


def test_bot_token_fallback_used_when_telegram_bot_token_unset_new():
    """The canonical fallback order (telegram_bot_token, then bot_token) is
    the same one used by telegram_bot/main.py and
    routers/telegram_bot_webhook.py — verifying it stays consistent here
    guards against a future edit silently diverging the auth contract."""
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = ""
        mock_settings.bot_token = "fallback-token"
        mock_settings.telegram_chat_id = "-100555"
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"{}"

        send_admin_alert(title="Import pipeline finished", message="ok", level="info")

        request = mock_urlopen.call_args[0][0]
        assert request.full_url == "https://api.telegram.org/botfallback-token/sendMessage"


def test_chat_id_override_does_not_change_auth_token_new():
    """debug_report_service.py is the one caller that overrides chat_id
    (routing to a separate reporting chat) — this must never also swap the
    bot token, or the two "different auth per call path" would become
    real, which the task explicitly requires to not happen."""
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "shared-token"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"{}"

        send_admin_alert(title="Import pipeline finished", message="ok", chat_id_override="-100999")

        request = mock_urlopen.call_args[0][0]
        assert request.full_url == "https://api.telegram.org/botshared-token/sendMessage"
        assert b"chat_id=-100999" in request.data


def test_no_duplicate_alert_sent_for_single_call_new():
    with patch("services.admin_alert_service.settings") as mock_settings, patch(
        "services.admin_alert_service.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_settings.telegram_bot_token = "real-token"
        mock_settings.bot_token = ""
        mock_settings.telegram_chat_id = "-100555"
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"{}"

        send_admin_alert(title="Import pipeline finished", message="ok")

        assert mock_urlopen.call_count == 1
