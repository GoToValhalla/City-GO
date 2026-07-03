from __future__ import annotations

from fastapi.testclient import TestClient

from tests.test_admin_backlog_breakdown_new import _make_place


def _apply(client: TestClient, action_code: str, limit: int = 100) -> dict[str, object]:
    response = client.post(
        "/admin/overview/backlog-reduction/apply",
        json={"action_code": action_code, "limit": limit, "confirmation_text": "APPLY"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _dry(client: TestClient, action_code: str, limit: int = 100) -> dict[str, object]:
    response = client.post("/admin/overview/backlog-reduction/dry-run", json={"action_code": action_code, "limit": limit})
    assert response.status_code == 200, response.text
    return response.json()


def test_recompute_route_eligibility_updates_stale_flags_new(client: TestClient, db_session, place_factory) -> None:
    museum = _make_place(db_session, place_factory, "stale-museum", category="museum", canonical_category="museum", is_route_eligible=False)
    bank = _make_place(db_session, place_factory, "stale-bank", category="bank", canonical_category="bank", is_route_eligible=True)

    payload = _apply(client, "recompute_route_eligibility")

    db_session.refresh(museum)
    db_session.refresh(bank)
    assert payload["changed_count"] == 2
    assert museum.is_route_eligible is True
    assert museum.route_exclusion_reason is None
    assert bank.is_route_eligible is False
    assert "hard_excluded_category:" in (bank.route_exclusion_reason or "")


def test_service_categories_are_excluded_from_routes_only_new(client: TestClient, db_session, place_factory) -> None:
    pharmacy = _make_place(db_session, place_factory, "service-pharmacy", category="pharmacy", canonical_category="pharmacy")
    bus_stop = _make_place(db_session, place_factory, "service-stop", category="bus_stop", canonical_category="bus_stop")
    cafe = _make_place(db_session, place_factory, "service-cafe", category="cafe", canonical_category="cafe")

    payload = _apply(client, "exclude_service_places_from_routes")

    for place in (pharmacy, bus_stop, cafe):
        db_session.refresh(place)
    assert payload["changed_count"] == 2
    assert pharmacy.is_published is True
    assert bus_stop.is_visible_in_catalog is True
    assert pharmacy.is_route_eligible is False
    assert bus_stop.is_route_eligible is False
    assert cafe.is_route_eligible is True


def test_classify_unknown_categories_uses_only_high_confidence_rules_new(client: TestClient, db_session, place_factory) -> None:
    museum = _make_place(db_session, place_factory, "unknown-museum", title="Музей истории", category="unknown", canonical_category="unknown")
    ambiguous = _make_place(db_session, place_factory, "unknown-ambiguous", title="Точка у воды", category="unknown", canonical_category="unknown")
    pharmacy = _make_place(db_session, place_factory, "unknown-pharmacy", title="Аптека на углу", category="unknown", canonical_category="unknown")

    payload = _apply(client, "classify_unknown_categories_deterministic")

    for place in (museum, ambiguous, pharmacy):
        db_session.refresh(place)
    assert payload["changed_count"] == 2
    assert museum.canonical_category == "museum"
    assert museum.is_route_eligible is True
    assert ambiguous.canonical_category == "unknown"
    assert pharmacy.canonical_category == "pharmacy"
    assert pharmacy.is_route_eligible is False


def test_manual_review_normalization_moves_only_safe_legacy_rows_new(client: TestClient, db_session, place_factory) -> None:
    safe = _make_place(db_session, place_factory, "safe-manual", publication_status="needs_review", is_published=False, is_visible_in_catalog=False, verification_status="needs_recheck")
    explicit = _make_place(db_session, place_factory, "explicit-manual", publication_status="deferred", is_published=False, is_visible_in_catalog=False, verification_status="verified")

    payload = _apply(client, "normalize_manual_review_backlog")

    db_session.refresh(safe)
    db_session.refresh(explicit)
    assert payload["changed_count"] == 1
    assert payload["skipped_count"] == 1
    assert safe.publication_status == "auto_backlog"
    assert explicit.publication_status == "deferred"


def test_content_enrichment_actions_queue_work_without_fake_content_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "enqueue-description", short_description=None)

    payload = _apply(client, "enqueue_description_enrichment")

    db_session.refresh(place)
    assert payload["queued_count"] == 1
    assert payload["changed_count"] == 0
    assert place.short_description is None


def test_photo_and_address_enqueue_do_not_fill_fake_values_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "enqueue-content", image_url=None, address=None)

    photo = _apply(client, "enqueue_photo_discovery")
    address = _apply(client, "enqueue_address_recovery")

    db_session.refresh(place)
    assert photo["queued_count"] == 1
    assert address["queued_count"] == 1
    assert place.image_url is None
    assert place.address is None


def test_verification_recheck_does_not_mark_place_verified_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "verification-queue", verification_status="needs_recheck")

    payload = _apply(client, "auto_recheck_verification_backlog")

    db_session.refresh(place)
    assert payload["queued_count"] == 1
    assert place.verification_status == "needs_recheck"


def test_disabled_low_confidence_action_is_dry_run_only_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "low-confidence-disabled", existence_confidence_level="low")

    preview = _dry(client, "recompute_low_confidence")
    response = client.post(
        "/admin/overview/backlog-reduction/apply",
        json={"action_code": "recompute_low_confidence", "limit": 10, "confirmation_text": "APPLY"},
    )

    assert preview["status"] == "unsupported"
    assert response.status_code == 409
