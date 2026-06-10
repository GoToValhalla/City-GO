from dataclasses import dataclass


@dataclass(frozen=True)
class RouteStart:
    lat: float
    lng: float
    source: str
    label: str
