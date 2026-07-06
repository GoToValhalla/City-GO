"""Recommended scope generation for discovery candidates."""

from __future__ import annotations

from schemas.destination_discovery import DiscoveryWarning, GeoBbox, GeoPoint, RecommendedScope


def recommend_scopes(raw: dict[str, object], *, include_buffer: bool = True) -> list[RecommendedScope]:
    name = str(raw.get("name") or "Направление")
    bbox_data = raw.get("bbox")
    warnings: list[DiscoveryWarning] = []
    bbox = GeoBbox.model_validate(bbox_data) if isinstance(bbox_data, dict) else None
    center = GeoPoint(lat=float(raw["lat"]), lon=float(raw["lon"])) if raw.get("lat") is not None and raw.get("lon") is not None else None
    if bbox is None and center is None:
        warnings.append(DiscoveryWarning(code="BOUNDARY_MISSING", severity="critical", message="Нет bbox и центра — контур небезопасен без проверки."))
        return []
    scopes = [
        RecommendedScope(
            code="city_core",
            name=f"{name} — ядро",
            import_profile="tourist_core",
            bbox=bbox,
            center=center if bbox is None else None,
            radius_meters=2500 if bbox is None else None,
            priority=100,
            reason="Базовый туристический контур по границам населённого пункта",
            warnings=warnings,
            confidence=0.8 if bbox else 0.45,
        ),
    ]
    if include_buffer and raw.get("border"):
        scopes.append(
            RecommendedScope(
                code="border_buffer",
                name=f"{name} — приграничный буфер",
                import_profile="tourist_core",
                bbox=bbox,
                priority=50,
                reason="Приграничная зона — уменьшенный приоритет",
                warnings=[DiscoveryWarning(code="BORDER_BUFFER_RISK", severity="warning", message="Приграничный контур — проверьте пересечения.")],
                confidence=0.5,
            ),
        )
    return scopes
