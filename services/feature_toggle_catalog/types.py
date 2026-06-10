from typing import TypedDict


class ToggleDef(TypedDict):
    key: str
    label: str
    description: str
    default: bool
    scope: str
    group: str
