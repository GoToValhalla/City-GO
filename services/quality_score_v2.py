"""Объяснимый Quality Score V2 без подмены blocking-проверок числом."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse

from models.place import Place


@dataclass(slots=True)
class QualityResult:
    score: int
    bucket: str
    components: dict[str, int]
    blocking_issues: list[str]
    warnings: list[str]
    recommendations: list[str]
    explanation: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def calculate_quality_v2(place: Place) -> QualityResult:
    components: dict[str, int] = {}
    blocking: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    components["taxonomy"] = 12 if place.category_id and place.canonical_category not in {None, "service", "unknown"} else 0
    if not components["taxonomy"]:
        blocking.append("Не определена конкретная категория.")

    components["coordinates"] = 12 if _valid_coordinates(place.lat, place.lng) else 0
    if not components["coordinates"]:
        blocking.append("Некорректные координаты.")

    components["address"] = 9 if _present(place.address) else 0
    components["photo"] = 12 if _present(place.image_url) or bool(place.images) else 0
    components["description"] = 10 if len((place.short_description or "").strip()) >= 80 else 4 if _present(place.short_description) else 0
    components["opening_hours"] = 8 if bool(place.opening_hours) else 0
    components["contacts"] = 7 if _valid_phone(place.phone) or _valid_website(place.website) else 0
    components["verification"] = 10 if place.verification_status == "verified" else 3 if place.verification_status != "rejected" else 0
    components["freshness"] = 8 if place.updated_at and place.updated_at >= datetime.utcnow() - timedelta(days=365) else 2
    components["source_confidence"] = max(0, min(7, round((place.confidence or 0) * 7)))
    components["duplicate_risk"] = 5 if not place.is_duplicate_suspected else 0

    if not components["address"]: recommendations.append("Добавить адрес.")
    if not components["photo"]: recommendations.append("Добавить подтверждённое фото.")
    if components["description"] < 10: recommendations.append("Дополнить описание места.")
    if not components["opening_hours"]: warnings.append("Не указаны часы работы.")
    if place.is_duplicate_suspected: blocking.append("Есть риск дубликата.")

    score = max(0, min(100, sum(components.values())))
    bucket = "excellent" if score >= 85 else "good" if score >= 70 else "needs_work" if score >= 45 else "critical"
    explanation = [f"{name}: {value}" for name, value in components.items()]
    return QualityResult(score, bucket, components, blocking, warnings, recommendations, explanation)


def publication_ready(result: QualityResult) -> bool:
    return not result.blocking_issues


def _present(value: object) -> bool:
    return bool(str(value).strip()) if value is not None else False


def _valid_coordinates(lat: float | None, lng: float | None) -> bool:
    return lat is not None and lng is not None and (lat != 0 or lng != 0) and -90 <= lat <= 90 and -180 <= lng <= 180


def _valid_phone(phone: str | None) -> bool:
    digits = "".join(character for character in (phone or "") if character.isdigit())
    return len(digits) >= 7


def _valid_website(website: str | None) -> bool:
    if not website: return False
    parsed = urlparse(website if "://" in website else f"https://{website}")
    return bool(parsed.netloc and "." in parsed.netloc)
