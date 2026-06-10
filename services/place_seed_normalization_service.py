from schemas.place_seed_item import PlaceSeedItem


def normalize_place_seed_item(item: PlaceSeedItem) -> PlaceSeedItem:
    return item.model_copy(
        update={
            "title": _clean_text(item.title),
            "slug": _slug(item.slug),
            "city_slug": _slug(item.city_slug),
            "category": _slug(item.category),
            "address": _optional_text(item.address),
            "short_description": _optional_text(item.short_description),
            "source": _optional_slug(item.source),
            "source_url": _optional_text(item.source_url),
        }
    )


def _optional_text(value: str | None) -> str | None:
    cleaned = _clean_text(value or "")
    return cleaned or None


def _optional_slug(value: str | None) -> str | None:
    cleaned = _slug(value or "")
    return cleaned or None


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


def _slug(value: str) -> str:
    return _clean_text(value).casefold().replace(" ", "-")
