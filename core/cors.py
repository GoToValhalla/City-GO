from __future__ import annotations


def parse_cors_origins(raw: str) -> list[str]:
    values = [item.strip() for item in raw.split(",")]
    origins = [item for item in values if item]
    return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]
