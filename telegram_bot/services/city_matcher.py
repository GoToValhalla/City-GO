CityPayload = dict[str, object]


def match_city(cities: list[CityPayload], text: str) -> CityPayload | None:
    normalized = _normalize(text)
    matches = tuple(
        filter(
            lambda city: _city_is_active(city) and _city_matches(city, normalized),
            cities,
        )
    )
    return next(iter(matches), None)


def _city_matches(city: CityPayload, normalized_text: str) -> bool:
    names = tuple(filter(None, map(_city_token, (city.get("name"), city.get("slug")))))
    return any(name in normalized_text for name in names)


def _city_token(value: object) -> str | None:
    return _normalize(value) if isinstance(value, str) and value else None


def _city_is_active(city: CityPayload) -> bool:
    return city.get("is_active") is not False


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())
