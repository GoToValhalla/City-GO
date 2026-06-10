def friendly_backend_error(raw: object) -> str:
    text = raw if isinstance(raw, str) else ""
    normalized = text.casefold()

    if not normalized:
        return "Backend вернул неизвестную ошибку. Попробуй еще раз позже."
    if _contains_any(normalized, ("timed out", "timeout")):
        return "Backend не ответил вовремя. Попробуй еще раз через минуту."
    if _contains_any(normalized, _CONNECTION_MARKERS):
        return "Backend сейчас недоступен. Попробуй еще раз через минуту."
    if "city center missing" in normalized:
        return "Не найден центр города по умолчанию. Нужно проверить настройки города."
    if _contains_any(normalized, ("404", "not found")):
        return "Backend не нашел нужные данные для этого запроса."
    if _contains_any(normalized, ("500", "502", "503", "504")):
        return "Backend временно ответил ошибкой. Попробуй повторить запрос."
    if "bad response" in normalized:
        return "Backend вернул неожиданный ответ. Попробуй позже."
    return "Не удалось выполнить запрос к backend. Попробуй позже."


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


_CONNECTION_MARKERS = (
    "connection refused",
    "connecterror",
    "couldn't connect",
    "failed to connect",
    "all connection attempts failed",
    "network is unreachable",
)
