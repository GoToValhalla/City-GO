from typing import TypedDict


class UserLocation(TypedDict):
    lat: float
    lng: float


class UserAddress(TypedDict):
    raw_address: str


class SelectedCity(TypedDict):
    slug: str


class ContextSnapshot(TypedDict):
    has_location: bool
    raw_address: str | None
    has_route: bool
    route_points: int
    selected_city_slug: str | None
