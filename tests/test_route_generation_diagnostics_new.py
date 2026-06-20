"""Тесты диагностики генерации маршрутов."""

from __future__ import annotations

from unittest.mock import patch

from models.route_generation_candidate import RouteGenerationCandidate
from models.route_generation_run import RouteGenerationRun
from services.context_merge_service import RequestContext
from services.route_builder_service import RouteBuilderService
from services.route_eligibility import ALGORITHM_VERSION
from services.route_generation_diagnostics.candidate_audit import audit_city_pool
from services.route_generation_diagnostics.persist import persist_generation_run


def test_persist_generation_run_creates_candidates_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="diag-persist-city")
    cafe = place_factory(slug="diag-cafe", category="cafe", city_id=city.id)
    pharmacy = place_factory(slug="diag-pharm", category="pharmacy", city_id=city.id)
    audited = audit_city_pool(db_session, city=city)
    run = persist_generation_run(
        db_session,
        city_id=city.id,
        user_id=None,
        request_json={"source": "test"},
        status="success",
        failure_reason=None,
        audited=audited,
        selected_place_ids={cafe.id},
    )
    assert run.id is not None
    rows = db_session.query(RouteGenerationCandidate).filter(
        RouteGenerationCandidate.generation_run_id == run.id,
    ).all()
    assert len(rows) >= 2
    pharm_row = next(row for row in rows if row.place_id == pharmacy.id)
    assert pharm_row.is_eligible is False
    assert pharm_row.rejection_reasons
    assert pharm_row.selected is False


def test_canonical_generation_creates_run_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="diag-run-city")
    place_factory(slug="run-cafe", category="cafe", city_id=city.id, lat=city.center_lat, lng=city.center_lng)
    with patch(
        "services.candidate_retrieval_service.CandidateRetrievalService.get_candidates",
        return_value=[],
    ):
        request = RequestContext(
            location=(city.center_lat, city.center_lng),
            city_id=city.slug,
            time_budget_minutes=120,
        )
        final = RouteBuilderService().build_route(db=db_session, request=request, profile=None)
    run_id = getattr(final, "generation_run_id", None)
    assert run_id is not None
    run = db_session.query(RouteGenerationRun).filter(RouteGenerationRun.id == run_id).first()
    assert run is not None
    assert run.algorithm_version == ALGORITHM_VERSION


def test_generation_failed_writes_system_log_new(db_session, city_factory) -> None:
    from models.product_event import ProductEvent
    from models.system_log import SystemLog
    from services.route_generation_logging import log_route_generation_failed

    city = city_factory(slug="diag-log-city")
    log_route_generation_failed(
        db_session,
        source="test",
        city_slug=city.slug,
        reason="route_generation_failed",
    )
    assert db_session.query(SystemLog).filter(SystemLog.message == "route_generation_failed").count() == 1
    assert db_session.query(ProductEvent).filter(ProductEvent.event_type == "route_generation_failed").count() == 1
