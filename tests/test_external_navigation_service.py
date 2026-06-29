from types import SimpleNamespace

from services.external_navigation_service import build_external_navigation


def point(position, place_id, title, lat, lng):
    return SimpleNamespace(position=position, place_id=place_id, place_title=title, lat=lat, lng=lng)


def test_external_navigation_builds_segment_first_links():
    navigation = build_external_navigation([
        point(1, 10, "Парк", 43.2581, 76.9558),
        point(2, 11, "Собор", 43.2602, 76.9601),
    ])

    assert navigation.mode == "segment_first"
    assert navigation.navigation_ready_pct == 100.0
    assert len(navigation.destination_links) == 2
    assert len(navigation.segments) == 1
    segment = navigation.segments[0]
    assert segment.from_index == 1
    assert segment.to_index == 2
    assert segment.distance_m > 0
    assert segment.walk_duration_min > 0
    assert {link.provider for link in segment.links} == {"yandex_maps", "2gis"}


def test_two_gis_uses_lon_lat_order_and_yandex_uses_lat_lon_order():
    navigation = build_external_navigation([
        point(1, 10, "Парк", 43.2581, 76.9558),
        point(2, 11, "Собор", 43.2602, 76.9601),
    ])
    links = {link.provider: link.web_url for link in navigation.segments[0].links}

    assert "43.258100,76.955800~43.260200,76.960100" in links["yandex_maps"]
    assert "from/76.955800,43.258100/to/76.960100,43.260200" in links["2gis"]


def test_external_navigation_marks_invalid_coordinates_without_breaking_response():
    navigation = build_external_navigation([
        point(1, 10, "Без координат", None, None),
        point(2, 11, "Собор", 43.2602, 76.9601),
    ])

    assert navigation.navigation_ready_pct == 50.0
    assert navigation.segments == []
    assert "some_points_have_no_valid_coordinates" in navigation.warnings
    assert "not_enough_points_for_segment_navigation" in navigation.warnings


def test_external_navigation_disables_unstable_full_route_for_long_routes():
    points = [point(index, index, f"Точка {index}", 43.25 + index / 1000, 76.95 + index / 1000) for index in range(1, 11)]

    navigation = build_external_navigation(points)

    assert len(navigation.segments) == 9
    assert navigation.full_route.available is False
    assert navigation.full_route.reason == "too_many_points_for_stable_full_route"
