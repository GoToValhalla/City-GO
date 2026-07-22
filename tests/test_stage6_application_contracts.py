from __future__ import annotations

import dataclasses
from datetime import time
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from models.place_schedule import PlaceSchedule
from services.stage6_contracts import catalog, catalog_entities, destination, media, projection, quality, review_quality, routing
from services.stage6_contracts.catalog_entities import CatalogScheduleWrite, catalog_schedule, write_catalog_schedule


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


def test_catalog_city_contract_delegates_to_existing_writer(monkeypatch) -> None:
    payload = SimpleNamespace(name="Rome")
    calls: list[tuple[object, str]] = []
    monkeypatch.setattr(catalog_entities, "create_city_and_queue_import",
                        lambda db, value, actor: calls.append((value, actor)) or "city")
    command = catalog_entities.CatalogCityCreate(payload=payload, actor="operator")

    assert catalog_entities.create_catalog_city(object(), command) == "city"
    assert calls == [(payload, "operator")]


def test_catalog_taxonomy_contract_delegates_to_existing_writer(monkeypatch) -> None:
    payload = SimpleNamespace(model_dump=lambda: {"code": "museum"})
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(catalog_entities, "create_category",
                        lambda db, **kwargs: calls.append(kwargs) or "category")
    command = catalog_entities.CatalogTaxonomyCreate(payload=payload, actor="operator")

    assert catalog_entities.create_catalog_category(object(), command) == "category"
    assert calls == [{"data": {"code": "museum"}, "actor": "operator"}]


def test_catalog_schedule_write_is_immutable() -> None:
    command = CatalogScheduleWrite(place_id=1, weekday="mon", open_time=time(9, 0), close_time=time(18, 0))

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.weekday = "tue"  # type: ignore[misc]


def test_write_catalog_schedule_creates_missing_row(db_session, place_factory) -> None:
    place = place_factory()

    row = write_catalog_schedule(
        db_session,
        CatalogScheduleWrite(place_id=place.id, weekday="mon", open_time=time(9, 0), close_time=time(18, 0)),
    )

    assert row.place_id == place.id
    assert row.weekday == "mon"
    assert row.open_time == time(9, 0)
    assert row.close_time == time(18, 0)
    assert row.is_closed is False


def test_write_catalog_schedule_updates_existing_row(db_session, place_factory) -> None:
    place = place_factory()
    first = write_catalog_schedule(
        db_session,
        CatalogScheduleWrite(place_id=place.id, weekday="mon", open_time=time(9, 0), close_time=time(18, 0)),
    )
    db_session.flush()

    second = write_catalog_schedule(
        db_session,
        CatalogScheduleWrite(place_id=place.id, weekday="mon", open_time=time(10, 0), close_time=time(19, 0), is_closed=True),
    )

    assert second.id == first.id
    assert second.open_time == time(10, 0)
    assert second.close_time == time(19, 0)
    assert second.is_closed is True


def test_write_catalog_schedule_flushes_but_does_not_commit(db_session, place_factory) -> None:
    place = place_factory()
    place_id = int(place.id)  # captured as a plain value: db_session.rollback()
    # below rolls back the fixture's own outer transaction (db_session wraps
    # the whole test in one transaction with no nested SAVEPOINT), which
    # would detach the ORM-bound `place` instance -- querying by a plain
    # captured id avoids touching that detached instance.

    write_catalog_schedule(
        db_session,
        CatalogScheduleWrite(place_id=place_id, weekday="mon", open_time=time(9, 0), close_time=time(18, 0)),
    )
    db_session.rollback()

    remaining = db_session.query(PlaceSchedule).filter(
        PlaceSchedule.place_id == place_id, PlaceSchedule.weekday == "mon",
    ).count()
    assert remaining == 0


def test_write_catalog_schedule_produces_exactly_one_row_per_place_and_weekday(db_session, place_factory) -> None:
    place = place_factory()

    write_catalog_schedule(db_session, CatalogScheduleWrite(place_id=place.id, weekday="mon", open_time=time(9, 0), close_time=time(18, 0)))
    write_catalog_schedule(db_session, CatalogScheduleWrite(place_id=place.id, weekday="mon", open_time=time(11, 0), close_time=time(20, 0)))
    write_catalog_schedule(db_session, CatalogScheduleWrite(place_id=place.id, weekday="mon", open_time=time(12, 0), close_time=time(21, 0)))

    rows = db_session.query(PlaceSchedule).filter(
        PlaceSchedule.place_id == place.id, PlaceSchedule.weekday == "mon",
    ).all()
    assert len(rows) == 1
    assert rows[0].open_time == time(12, 0)


def test_write_catalog_schedule_rejects_invalid_weekday(db_session, place_factory) -> None:
    place = place_factory()

    with pytest.raises(ValueError, match="Invalid weekday"):
        write_catalog_schedule(
            db_session,
            CatalogScheduleWrite(place_id=place.id, weekday="funday", open_time=None, close_time=None),
        )


def test_database_rejects_duplicate_place_weekday_row_at_the_constraint_level(db_session, place_factory) -> None:
    place = place_factory()
    db_session.add(PlaceSchedule(place_id=place.id, weekday="mon"))
    db_session.flush()
    db_session.add(PlaceSchedule(place_id=place.id, weekday="mon"))

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_catalog_schedule_returns_calendar_weekday_order(db_session, place_factory) -> None:
    place = place_factory()
    for weekday in ("sun", "wed", "mon", "fri"):
        write_catalog_schedule(
            db_session,
            CatalogScheduleWrite(place_id=place.id, weekday=weekday, open_time=None, close_time=None, is_closed=True),
        )

    rows = catalog_schedule(db_session, place.id)

    assert [row.weekday for row in rows] == ["mon", "wed", "fri", "sun"]


def test_catalog_schedule_returns_immutable_tuple(db_session, place_factory) -> None:
    place = place_factory()
    write_catalog_schedule(
        db_session,
        CatalogScheduleWrite(place_id=place.id, weekday="mon", open_time=None, close_time=None, is_closed=True),
    )

    rows = catalog_schedule(db_session, place.id)

    assert isinstance(rows, tuple)
    with pytest.raises(AttributeError):
        rows.append(None)  # type: ignore[attr-defined]


def test_catalog_schedule_returns_empty_tuple_for_place_with_no_schedule(db_session, place_factory) -> None:
    place = place_factory()

    rows = catalog_schedule(db_session, place.id)

    assert rows == ()
