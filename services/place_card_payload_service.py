from models.place import Place
from services.place_runtime_defaults import effective_opening_hours, effective_visit_duration


def place_card_payload(place: Place) -> dict[str, object]:
    has_hours = isinstance(place.opening_hours, dict) and bool(place.opening_hours)
    has_duration = bool(place.average_visit_duration_minutes)
    image_url = getattr(place, "public_image_url", None) or place.image_url
    image_urls = getattr(place, "public_image_urls", None) or getattr(place, "image_urls", None)
    photo_urls = getattr(place, "public_photo_urls", None) or getattr(place, "photo_urls", None) or image_urls
    return {
        "id": place.id,
        "slug": place.slug,
        "title": place.title,
        "city_id": place.city_id,
        "category_id": place.category_id,
        "category": place.category,
        "short_description": place.short_description,
        "image_url": image_url,
        "image_urls": image_urls,
        "photo_urls": photo_urls,
        "image_id": getattr(place, "public_image_id", None),
        "image_source_type": getattr(place, "public_image_source_type", None),
        "image_attribution": getattr(place, "public_image_attribution", None),
        "image_license": getattr(place, "public_image_license", None),
        "image_confidence": getattr(place, "public_image_confidence", None),
        "image_status": getattr(place, "public_image_status", None),
        "address": place.address,
        "price_level": place.price_level,
        "dog_friendly": place.dog_friendly,
        "family_friendly": place.family_friendly,
        "indoor": place.indoor,
        "outdoor": place.outdoor,
        "source": place.source,
        "confidence": place.confidence,
        "average_visit_duration_minutes": effective_visit_duration(place),
        "visit_duration_source": "measured" if has_duration else "category_default",
        "opening_hours": effective_opening_hours(place),
        "opening_hours_mode": "verified" if has_hours else "estimated_default",
    }
