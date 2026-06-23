from dataclasses import dataclass

MAX_CALLBACK_BYTES = 64


@dataclass(frozen=True)
class Callback:
    action: str
    parts: tuple[str, ...] = ()


def build_callback(action: str, *parts: object) -> str:
    value = ":".join([action, *(str(part) for part in parts if part is not None)])
    if len(value.encode("utf-8")) > MAX_CALLBACK_BYTES:
        raise ValueError(f"Telegram callback_data is too long: {value}")
    return value


def parse_callback(data: str | None) -> Callback:
    if not data:
        return Callback(action="unknown")
    head, *tail = data.split(":")
    return Callback(action=head, parts=tuple(tail))
