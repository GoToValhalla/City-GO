from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.stage6_contracts import catalog, destination, media, projection, quality, review_quality, routing


def test_catalog_contract_preserves_explicit_transaction_ownership(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(catalog, "update_admin_place_fields", lambda db, place_id, fields, **kwargs: calls.append(kwargs) or "place")
    command = catalog.CatalogPlaceUpdate(place_id=7, fields={"title": "Museum"}, actor="operator")

    assert catalog.update_catalog_place(object(), command) == "place"
    assert calls == [{"actor": "operator", "commit": False, "locked_place": None}]


def test_destination_contract_delegates_to_owner(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(destination, "upsert_membership", lambda db, **kwargs: calls.append(kwargs) or "membership")
    command = destination.DestinationMembershipCommand(place_id=3, destination_id=4, source="admin")

    assert destination.assign_place(object(), command) == "membership"
    assert calls[0]["place_id"] == 3
    assert calls[0]["destination_id"] == 4


def test_media_contract_returns_typed_result_without_commit(monkeypatch) -> None:
    calls: list[bool] = []
    image = SimpleNamespace(id=1, place_id=2, status="approved")
    monkeypatch.setattr(media, "approve_place_image", lambda *args, **kwargs: calls.append(kwargs["commit"]) or image)

    result = media.approve_media(object(), 1, actor="operator")

    assert result == media.MediaModerationResult(image_id=1, place_id=2, status="approved")
    assert calls == [False]


def test_quality_contract_returns_immutable_evaluation(monkeypatch) -> None:
    monkeypatch.setattr(quality, "diagnostic_gates", lambda *args, **kwargs: {
        "status": "critical", "blocks_publication": False, "failed_gates": ["photo_coverage"],
    })

    result = quality.evaluate_city_quality(object(), city_id=1, city_slug="rome")

    assert result.failed_gates == ("photo_coverage",)
    with pytest.raises(AttributeError):
        result.status = "pass"  # type: ignore[misc]


def test_routing_contract_returns_stable_artifact(monkeypatch) -> None:
    route = SimpleNamespace(id=5, city_id=2, slug="walk", route_places=[SimpleNamespace(place_id=8)])
    monkeypatch.setattr(routing, "get_public_route_by_id", lambda db, route_id: route)

    assert routing.public_route_artifact(object(), 5) == routing.RouteArtifact(5, 2, "walk", (8,))


def test_projection_contract_fails_closed_for_unknown_type() -> None:
    command = projection.ProjectionRebuildCommand("unknown", None, "operator", "admin", {})

    with pytest.raises(ValueError, match="Unsupported projection type"):
        projection.rebuild_projection(object(), command)


def test_publication_consumes_explicit_review_decision(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(review_quality, "transition_publication",
                        lambda db, command: calls.append(command) or "transition")
    place = SimpleNamespace(id=11)
    decision = review_quality.PublicationReviewDecision(
        place=place, decision=review_quality.ReviewDecision.APPROVE,
        actor="reviewer", reason_code="review_approved",
    )

    assert review_quality.consume_publication_decision(object(), decision) == "transition"
    assert calls[0].to_status == "published"


def test_quality_finding_is_evidence_not_a_publication_command() -> None:
    finding = review_quality.QualityFinding("place", "12", "missing_photo", "high", True)

    assert finding.blocks_publication is True
    assert not hasattr(finding, "to_status")
