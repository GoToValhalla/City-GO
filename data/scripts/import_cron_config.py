from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_TARGET_FILE = Path("data/config/import_targets.json")


def load_targets(path: Path = DEFAULT_TARGET_FILE) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        _target(city.get("city"), scope)
        for city in payload.get("targets", [])
        for scope in city.get("scopes", [])
        if scope.get("enabled", True)
    ]


def select_targets(
    targets: list[dict[str, Any]],
    cities: tuple[str, ...],
    scopes: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [
        target
        for target in targets
        if (not cities or target["city"] in cities)
        and (not scopes or target["scope"] in scopes)
    ]


def split_csv(values: list[str] | None) -> tuple[str, ...]:
    raw = values or []
    parts = [
        part.strip()
        for value in raw
        for part in value.split(",")
        if part.strip()
    ]
    return tuple(dict.fromkeys(parts))


def _target(city_slug: str, scope: dict[str, Any]) -> dict[str, Any]:
    return {
        "city": city_slug,
        "scope": scope["code"],
        "profile": scope["profile"],
        "bbox": scope["bbox"],
        "refresh_interval_hours": scope.get("refresh_interval_hours") or 168,
    }


def merge_import_targets(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Объединяет targets без дублей (city+scope)."""
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for target in group:
            key = (str(target["city"]), str(target["scope"]))
            if key in seen:
                continue
            seen.add(key)
            merged.append(target)
    return merged


def load_db_targets(db: Any) -> list[dict[str, Any]]:
    """Enabled scopes из БД для городов в import/review статусах."""
    from models.city import City
    from models.city_import_scope import CityImportScope

    rows = (
        db.query(CityImportScope, City)
        .join(City, City.id == CityImportScope.city_id)
        .filter(
            CityImportScope.enabled.is_(True),
            CityImportScope.bbox.isnot(None),
            City.launch_status.in_(("importing", "imported", "review_required")),
        )
        .all()
    )
    return [
        {
            "city": city.slug,
            "scope": scope.code,
            "profile": scope.import_profile,
            "bbox": scope.bbox,
            "refresh_interval_hours": scope.refresh_interval_hours or 168,
        }
        for scope, city in rows
    ]
