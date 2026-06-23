from dataclasses import dataclass, field


@dataclass(frozen=True)
class BotCity:
    id: int
    slug: str
    name: str
    places_count: int = 0


@dataclass(frozen=True)
class BotPlace:
    id: int
    title: str
    category: str | None = None
    category_name: str | None = None
    short_description: str | None = None
    address: str | None = None
    image_url: str | None = None
    opening_hours_display: str | None = None
    hours_reliable: bool = False
    lat: float | None = None
    lng: float | None = None
    distance_m: int | None = None


@dataclass(frozen=True)
class BotRoutePoint:
    index: int
    place_id: int
    title: str
    category: str | None = None
    short_description: str | None = None
    address: str | None = None
    image_url: str | None = None
    lat: float | None = None
    lng: float | None = None


@dataclass(frozen=True)
class BotRoute:
    id: int
    title: str
    short_description: str | None = None
    duration_minutes: int | None = None
    distance_km: float | None = None
    points: list[BotRoutePoint] = field(default_factory=list)


@dataclass(frozen=True)
class Page:
    items: list[object]
    page: int
    has_next: bool
