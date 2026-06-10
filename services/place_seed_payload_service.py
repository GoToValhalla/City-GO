from schemas.place_seed_item import PlaceSeedItem
from services.place_staleness_policy import normalize_place_status


def place_payload(
    item: PlaceSeedItem,
    city_id: int,
    category_id: int | None,
) -> dict[str, object]:
    return {
        "city_id": city_id,
        "category_id": category_id,
        "slug": item.slug,
        "title": item.title,
        "short_description": item.short_description,
        "address": item.address,
        "source": item.source,
        "source_url": item.source_url,
        "confidence": item.confidence,
        "last_verified_at": item.last_verified_at,
        "status": normalize_place_status(item.status),
        "lat": float(item.lat or 0.0),
        "lng": float(item.lng or 0.0),
        "category": item.category,
        "opening_hours": item.opening_hours,
        "average_visit_duration_minutes": item.average_visit_duration_minutes,
        "price_level": item.price_level,
        "outdoor": _has_tag(item, "outdoor"),
        "indoor": _has_tag(item, "indoor"),
        "dog_friendly": _has_any(item, ("pet_friendly", "with_dog")),
        "family_friendly": _has_any(item, ("kid_friendly", "with_kids")),
        "is_active": item.is_active,
    }


def _has_tag(item: PlaceSeedItem, tag: str) -> bool:
    return tag in item.taxonomy.tags or tag in item.taxonomy.scenario_tags


def _has_any(item: PlaceSeedItem, tags: tuple[str, ...]) -> bool:
    return any(_has_tag(item, tag) for tag in tags)
