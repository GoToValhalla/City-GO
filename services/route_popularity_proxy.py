from __future__ import annotations


def popularity_proxy_score(place: object) -> float:
    fields = (
        ("wikidata_id", 0.35),
        ("osm_id", 0.25),
        ("source_url", 0.2),
        ("image_url", 0.1),
        ("short_description", 0.1),
    )
    signals = tuple(map(lambda item: item[1] if _has(getattr(place, item[0], None)) else 0.0, fields))
    return max(0.2, min(1.0, sum(signals)))


def _has(value: object) -> bool:
    return bool(str(value or "").strip())
