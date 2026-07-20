"""City-profile builders for the CITYGO-358 deterministic route evaluation
dataset. Every builder is a pure function of the pytest fixtures already
provided by tests/conftest.py (city_factory, published_place_factory,
place_factory) — no new fixture infrastructure, no network, no production
database, matching the task's "repository-native fixtures" and "no network
dependency" constraints.

Coordinates are deterministic, hand-picked lat/lng offsets around a fixed
center — never randomly generated — so a "compact" vs. "distributed" city
is a real geometric property or the test is meaningless, and re-running
never produces different data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CENTER_LAT = 54.9611
CENTER_LNG = 20.4703

# Small, deterministic offsets (degrees). ~0.001 deg latitude is ~111m —
# "compact" scenarios stay within a few hundred meters of each other;
# "distributed" scenarios spread points several kilometers apart.
_COMPACT_OFFSETS = [(0.0, 0.0), (0.0008, 0.0006), (0.0015, -0.0009), (-0.0007, 0.0012), (0.0011, 0.0011)]
_DISTRIBUTED_OFFSETS = [(0.0, 0.0), (0.03, 0.02), (-0.025, 0.03), (0.04, -0.03), (-0.035, -0.025)]
_SPARSE_OFFSETS = [(0.0, 0.0), (0.002, 0.001)]

ROUTE_FRIENDLY_CATEGORIES = ("cafe", "museum", "park", "viewpoint")


@dataclass
class CityScenario:
    """A fully-built, deterministic city fixture ready for route evaluation."""

    scenario_id: str
    city_slug: str
    place_ids: list[int] = field(default_factory=list)
    eligible_place_ids: list[int] = field(default_factory=list)
    ineligible_place_ids: list[int] = field(default_factory=list)
    destination_slug: str | None = None
    notes: str = ""


def _make_places(published_place_factory, city, *, offsets, category_cycle=ROUTE_FRIENDLY_CATEGORIES):
    ids = []
    for index, (dlat, dlng) in enumerate(offsets):
        category = category_cycle[index % len(category_cycle)]
        place = published_place_factory(
            slug=f"{city.slug}-place-{index}",
            title=f"{city.name} Place {index}",
            city_id=city.id,
            category=category,
            lat=CENTER_LAT + dlat,
            lng=CENTER_LNG + dlng,
        )
        ids.append(place.id)
    return ids


def build_healthy_compact_city(city_factory, published_place_factory) -> CityScenario:
    city = city_factory(slug="eval-compact-city", launch_status="published")
    ids = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS)
    return CityScenario(
        scenario_id="healthy_compact_published_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=ids,
        notes="5 published, route-eligible places within ~200m of each other.",
    )


def build_healthy_distributed_city(city_factory, published_place_factory) -> CityScenario:
    city = city_factory(slug="eval-distributed-city", launch_status="published")
    ids = _make_places(published_place_factory, city, offsets=_DISTRIBUTED_OFFSETS)
    return CityScenario(
        scenario_id="healthy_distributed_published_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=ids,
        notes="5 published, route-eligible places several km apart, exercising radius-expansion/city-wide fallback.",
    )


def build_sparse_city(city_factory, published_place_factory) -> CityScenario:
    city = city_factory(slug="eval-sparse-city", launch_status="published")
    ids = _make_places(published_place_factory, city, offsets=_SPARSE_OFFSETS)
    return CityScenario(
        scenario_id="sparse_published_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=ids,
        notes="Only 2 published, route-eligible places — must never fabricate a ready route from too few points.",
    )


def build_single_place_city(city_factory, published_place_factory) -> CityScenario:
    """Exactly ONE eligible place — the sharpest possible reproduction of
    the CITYGO-356 "one point -> never ready" invariant end-to-end through
    the real build pipeline (not just the canonical route_status()
    function in isolation)."""
    city = city_factory(slug="eval-single-place-city", launch_status="published")
    ids = _make_places(published_place_factory, city, offsets=_SPARSE_OFFSETS[:1])
    return CityScenario(
        scenario_id="single_eligible_place_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=ids,
        notes="Exactly 1 published, route-eligible place in the whole city.",
    )


def build_active_preview_city(city_factory, published_place_factory) -> CityScenario:
    city = city_factory(slug="eval-preview-city", launch_status="preview")
    ids = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS)
    return CityScenario(
        scenario_id="active_preview_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=[],
        ineligible_place_ids=ids,
        notes="Places are otherwise fully eligible, but City.launch_status='preview' — CITYGO-355 leakage class.",
    )


def build_preparing_city(city_factory, published_place_factory) -> CityScenario:
    city = city_factory(slug="eval-preparing-city", launch_status="preparing")
    ids = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS)
    return CityScenario(
        scenario_id="preparing_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=[],
        ineligible_place_ids=ids,
        notes="launch_status='preparing' was never in the old BLOCKED_CITY_LAUNCH_STATUSES set — exact CITYGO-355 regression shape.",
    )


def build_inactive_published_city(city_factory, published_place_factory) -> CityScenario:
    city = city_factory(slug="eval-inactive-city", launch_status="published", is_active=False)
    ids = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS)
    return CityScenario(
        scenario_id="inactive_published_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=[],
        ineligible_place_ids=ids,
        notes="launch_status='published' but City.is_active=False — the other half of the public city gate.",
    )


def build_mostly_service_only_city(city_factory, place_factory, published_place_factory) -> CityScenario:
    city = city_factory(slug="eval-service-only-city", launch_status="published")
    service_ids = []
    for index in range(4):
        place = place_factory(
            slug=f"eval-service-only-{index}",
            title=f"Service point {index}",
            city_id=city.id,
            category="bank" if index % 2 == 0 else "pharmacy",
            lat=CENTER_LAT + 0.0005 * index,
            lng=CENTER_LNG + 0.0005 * index,
            is_active=True,
            is_published=True,
            is_visible_in_catalog=True,
            is_route_eligible=False,
            publication_status="published",
        )
        service_ids.append(place.id)
    eligible = _make_places(published_place_factory, city, offsets=[(0.0009, 0.0009)], category_cycle=("cafe",))
    return CityScenario(
        scenario_id="mostly_service_only_city",
        city_slug=city.slug,
        place_ids=service_ids + eligible,
        eligible_place_ids=eligible,
        ineligible_place_ids=service_ids,
        notes="4 bank/pharmacy (hard-excluded, non-route-eligible) places + 1 real cafe.",
    )


def build_mixed_eligibility_city(city_factory, published_place_factory, place_factory) -> CityScenario:
    city = city_factory(slug="eval-mixed-city", launch_status="published")
    eligible = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS[:3])
    ineligible_ids = []
    unpublished = published_place_factory(
        slug="eval-mixed-unpublished", city_id=city.id, category="museum",
        lat=CENTER_LAT + 0.002, lng=CENTER_LNG + 0.002, is_published=False,
    )
    ineligible_ids.append(unpublished.id)
    invisible = published_place_factory(
        slug="eval-mixed-invisible", city_id=city.id, category="park",
        lat=CENTER_LAT + 0.003, lng=CENTER_LNG + 0.003, is_visible_in_catalog=False,
    )
    ineligible_ids.append(invisible.id)
    non_route_eligible = published_place_factory(
        slug="eval-mixed-non-route-eligible", city_id=city.id, category="cafe",
        lat=CENTER_LAT + 0.004, lng=CENTER_LNG + 0.004, is_route_eligible=False,
    )
    ineligible_ids.append(non_route_eligible.id)
    return CityScenario(
        scenario_id="mixed_eligibility_city",
        city_slug=city.slug,
        place_ids=eligible + ineligible_ids,
        eligible_place_ids=eligible,
        ineligible_place_ids=ineligible_ids,
        notes="3 fully eligible places + 3 places each violating exactly one visibility/eligibility gate.",
    )


def build_destination_enabled_city(city_factory, published_place_factory, db_session) -> CityScenario:
    from models.destination import Destination, DestinationPlaceMembership

    city = city_factory(slug="eval-destination-city", launch_status="published")
    ids = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS)
    destination = Destination(
        slug="eval-destination",
        name="Eval Destination",
        destination_type="city",
        legacy_city_id=city.id,
        center_lat=CENTER_LAT,
        center_lng=CENTER_LNG,
        launch_status="published",
        is_active=True,
        is_published=True,
    )
    db_session.add(destination)
    db_session.commit()
    db_session.refresh(destination)
    for place_id in ids:
        db_session.add(
            DestinationPlaceMembership(
                place_id=place_id,
                destination_id=destination.id,
                is_primary=True,
                assignment_type="legacy_city",
            )
        )
    db_session.commit()
    return CityScenario(
        scenario_id="destination_enabled_city",
        city_slug=city.slug,
        place_ids=ids,
        eligible_place_ids=ids,
        destination_slug=destination.slug,
        notes="All places are also DestinationPlaceMembership rows for a published Destination.",
    )


def build_closed_status_city(city_factory, published_place_factory, place_factory) -> CityScenario:
    """Places with status closed / temporarily_closed must never enter public routes."""
    city = city_factory(slug="eval-closed-status-city", launch_status="published")
    eligible = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS[:2])
    closed = place_factory(
        slug="eval-status-closed",
        city_id=city.id,
        category="cafe",
        status="closed",
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
        lat=CENTER_LAT + 0.005,
        lng=CENTER_LNG + 0.005,
    )
    temp = place_factory(
        slug="eval-status-temp-closed",
        city_id=city.id,
        category="park",
        status="temporarily_closed",
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
        lat=CENTER_LAT + 0.006,
        lng=CENTER_LNG + 0.006,
    )
    return CityScenario(
        scenario_id="closed_status_city",
        city_slug=city.slug,
        place_ids=eligible + [closed.id, temp.id],
        eligible_place_ids=eligible,
        ineligible_place_ids=[closed.id, temp.id],
        notes="Canonical public contract requires Place.status IS NULL or active.",
    )


def build_public_hidden_category_city(city_factory, published_place_factory, place_factory) -> CityScenario:
    """PUBLIC_HIDDEN_CATEGORIES leakage scenarios (beyond HARD_EXCLUDED-only checks)."""
    from services.place_public_visibility import PUBLIC_HIDDEN_CATEGORIES
    from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

    city = city_factory(slug="eval-hidden-cat-city", launch_status="published")
    eligible = _make_places(published_place_factory, city, offsets=_COMPACT_OFFSETS[:2])
    # Categories present in PUBLIC_HIDDEN but exercised explicitly.
    hidden_samples = ("bank", "atm", "pharmacy", "parking", "transport", "health", "medical")
    assert set(hidden_samples).issubset(PUBLIC_HIDDEN_CATEGORIES)
    ineligible_ids = []
    for index, category in enumerate(hidden_samples):
        place = place_factory(
            slug=f"eval-hidden-{category}",
            city_id=city.id,
            category=category,
            is_published=True,
            is_visible_in_catalog=True,
            is_route_eligible=False,
            publication_status="published",
            lat=CENTER_LAT + 0.01 + 0.001 * index,
            lng=CENTER_LNG + 0.01 + 0.001 * index,
        )
        ineligible_ids.append(place.id)
    extra = sorted(PUBLIC_HIDDEN_CATEGORIES - HARD_EXCLUDED_CATEGORIES)
    for index, category in enumerate(extra[:3]):
        place = place_factory(
            slug=f"eval-hidden-extra-{category}",
            city_id=city.id,
            category=category,
            is_published=True,
            is_visible_in_catalog=True,
            is_route_eligible=False,
            publication_status="published",
            lat=CENTER_LAT + 0.02 + 0.001 * index,
            lng=CENTER_LNG + 0.02 + 0.001 * index,
        )
        ineligible_ids.append(place.id)
    return CityScenario(
        scenario_id="public_hidden_category_city",
        city_slug=city.slug,
        place_ids=eligible + ineligible_ids,
        eligible_place_ids=eligible,
        ineligible_place_ids=ineligible_ids,
        notes="Hidden public categories must never leak even when stored flags look published.",
    )
