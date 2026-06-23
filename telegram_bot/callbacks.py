from dataclasses import dataclass

MAX_CALLBACK_BYTES = 64


@dataclass(frozen=True)
class ParsedCallback:
    scope: str
    action: str | None = None
    parts: tuple[str, ...] = ()


def cb(scope: str, action: str | None = None, *parts: object) -> str:
    values = [scope]
    if action is not None:
        values.append(action)
    values.extend(str(part) for part in parts if part is not None)
    value = ":".join(values)
    if len(value.encode("utf-8")) > MAX_CALLBACK_BYTES:
        raise ValueError(f"callback_data exceeds Telegram limit: {value}")
    return value


def parse_callback(data: str | None) -> ParsedCallback:
    if not data:
        return ParsedCallback(scope="unknown")
    scope, *rest = data.split(":")
    action = rest[0] if rest else None
    return ParsedCallback(scope=scope, action=action, parts=tuple(rest[1:]))
