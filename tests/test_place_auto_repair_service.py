from __future__ import annotations

from types import SimpleNamespace

from services.place_auto_repair_service import PlaceAutoRepairService
from tests.allure_support import title


@title("Auto repair normalizes category alias and blocks route utility junk")
def test_auto_repair_normalizes_category_alias_and_blocks_route_utility_junk() -> None:
    place = _place(category="pharmacy", opening_hours={"daily": "09:00-21:00"}, address="Main street")

    summary = PlaceAutoRepairService().repair_places([place])

    assert place.category == "health"
    assert place.canonical_category == "health"
    # Route eligibility is a controlled Place field: the pure repair engine
    # only reports the desired verdict; the canonical publication writer
    # applies it for already-published places (see admin_city_import_job_service).
    route_item = next(item for item in summary.items if item.reason == "route_ineligible_utility_or_service")
    assert route_item.route_eligible is False
    assert place.tourist_eligible is False
    assert summary.repaired_count >= 2
    assert summary.by_reason["route_ineligible_utility_or_service"] == 1


@title("Auto repair selects safe main photo from candidates")
def test_auto_repair_selects_safe_main_photo_from_candidates() -> None:
    place = _place(
        category="museum",
        image_url="",
        images=[SimpleNamespace(url="", is_public=True), SimpleNamespace(url="https://example.test/museum.jpg", is_public=True)],
        address="Museum street",
        opening_hours={"daily": "10:00-18:00"},
    )

    summary = PlaceAutoRepairService().repair_places([place])

    assert place.image_url == "https://example.test/museum.jpg"
    assert summary.by_reason["main_photo_selected"] == 1


@title("Auto repair sends unsafe data gaps to review queue")
def test_auto_repair_sends_unsafe_data_gaps_to_review_queue() -> None:
    place = _place(category="park", image_url="", address="", opening_hours=None, confidence=0.2)

    summary = PlaceAutoRepairService().repair_places([place])

    assert summary.needs_review_count >= 3
    assert summary.by_reason["missing_photo"] == 1
    assert summary.by_reason["missing_or_weak_address"] == 1
    assert summary.by_reason["missing_or_invalid_opening_hours"] == 1
    assert summary.by_reason["low_confidence"] == 1


@title("Auto repair creates draft description only with enough evidence")
def test_auto_repair_creates_draft_description_only_with_enough_evidence() -> None:
    place = _place(category="landmark", short_description="", address="Main square", opening_hours={"daily": "open"})

    summary = PlaceAutoRepairService().repair_places([place])

    assert "достопримечательность" in place.short_description
    # Verification status is a controlled Place field: the pure repair engine
    # only reports the desired verdict; the canonical verification writer
    # applies it (see admin_city_import_job_service).
    description_item = next(item for item in summary.items if item.reason == "draft_description_created")
    assert description_item.verification_status == "needs_recheck"
    assert summary.by_reason["draft_description_created"] == 1


def _place(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=1,
        title="Test place",
        category="museum",
        canonical_category=None,
        is_route_eligible=True,
        tourist_eligible=True,
        route_policy="city_walking",
        route_exclusion_reason=None,
        image_url="https://example.test/current.jpg",
        images=[],
        short_description="A detailed enough description for a city route place.",
        address="Main street",
        opening_hours={"daily": "10:00-18:00"},
        confidence=0.8,
        is_duplicate_suspected=False,
        verification_status="unverified",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
