from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

FORBIDDEN_COPY = (
    "published/catalog",
    "route policy",
    "canonical category",
    "taxonomy",
    "enrichment/policy",
    "verification backlog",
    "critical confidence",
    "is_route_eligible",
    "route_builder",
    "backend",
    "sql",
    "bucket",
    "status_",
    "eligible",
    "policy",
)
REQUIRED_QUEUES = {
    "route_blockers",
    "route_unknown",
    "route_excluded",
    "no_photo",
    "no_address",
    "no_description",
    "low_confidence",
    "auto_backlog",
    "manual_review",
    "needs_verification",
}


def _make_place(db_session, place_factory, slug: str, **updates: Any):
    base = {
        "slug": slug,
        "title": updates.pop("title", slug.replace("-", " ").title()),
        "category": updates.pop("category", "museum"),
        "address": updates.pop("address", "ул. Тестовая, 1"),
        "image_url": updates.pop("image_url", "https://img.test/a.jpg"),
        "publication_status": updates.pop("publication_status", "published"),
        "is_active": updates.pop("is_active", True),
        "is_published": updates.pop("is_published", True),
        "is_visible_in_catalog": updates.pop("is_visible_in_catalog", True),
        "is_route_eligible": updates.pop("is_route_eligible", True),
    }
    place = place_factory(**base)
    defaults = {
        "canonical_category": base["category"],
        "short_description": "Подробное описание места для оператора и проверки качества данных.",
        "verification_status": "verified",
        "existence_confidence_level": "high",
        "confidence_score": 8,
        "quality_score": 80,
    }
    for key, value in {**defaults, **updates}.items():
        setattr(place, key, value)
    db_session.commit()
    db_session.refresh(place)
    return place


def _payload(client: TestClient) -> dict[str, Any]:
    response = client.get("/admin/overview/backlog-breakdown")
    assert response.status_code == 200
    return response.json()


def _queue(payload: dict[str, Any], code: str) -> dict[str, Any]:
    return next(queue for queue in payload["queues"] if queue["code"] == code)


def _reasons(queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {reason["code"]: reason for reason in queue["reasons"]}


def test_backlog_breakdown_returns_summary_and_queues_new(client: TestClient) -> None:
    payload = _payload(client)

    assert {"generated_at", "summary", "queues", "overlaps"} <= set(payload)
    assert REQUIRED_QUEUES <= {queue["code"] for queue in payload["queues"]}
    assert {"unique_problem_places", "total_problem_signals", "auto_fixable_places", "manual_places"} <= set(payload["summary"])


def test_backlog_breakdown_counts_unique_places_once_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(
        db_session,
        place_factory,
        "one-place-many-signals",
        image_url=None,
        short_description="todo",
        existence_confidence_level="low",
        confidence_score=1,
        quality_score=20,
    )

    summary = _payload(client)["summary"]

    assert summary["unique_problem_places"] == 1
    assert summary["total_problem_signals"] >= 3


def test_route_blockers_breakdown_splits_reasons_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "manual-disabled", is_route_eligible=False)
    _make_place(db_session, place_factory, "unknown-category", category="unknown", canonical_category="unknown")
    _make_place(db_session, place_factory, "service-bank", category="bank", canonical_category="bank")

    queue = _queue(_payload(client), "route_blockers")
    reasons = _reasons(queue)

    assert queue["total_count"] == 3
    assert reasons["manual_disabled"]["count"] == 1
    assert reasons["unknown_category"]["count"] == 1
    assert reasons["service_category"]["count"] == 1
    assert "missing_coordinates" in reasons


def test_manual_review_breakdown_separates_auto_and_verification_overlap_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "pure-manual", publication_status="needs_review", is_published=False, is_visible_in_catalog=False, is_route_eligible=False)
    _make_place(db_session, place_factory, "manual-verification", publication_status="needs_review", verification_status="needs_recheck", is_published=False, is_visible_in_catalog=False, is_route_eligible=False)
    _make_place(db_session, place_factory, "manual-low", publication_status="needs_review", existence_confidence_level="low", is_published=False, is_visible_in_catalog=False, is_route_eligible=False)
    _make_place(db_session, place_factory, "auto-only", publication_status="auto_backlog", is_published=False, is_visible_in_catalog=False, is_route_eligible=False)

    payload = _payload(client)
    manual = _queue(payload, "manual_review")
    auto = _queue(payload, "auto_backlog")
    verification = _queue(payload, "needs_verification")
    manual_reasons = _reasons(manual)

    assert manual["total_count"] == 3
    assert auto["total_count"] == 1
    assert verification["total_count"] == 1
    assert manual_reasons["overlaps_with_verification"]["count"] == 1
    assert manual_reasons["overlaps_with_low_confidence"]["count"] == 1


def test_no_description_breakdown_counts_bad_descriptions_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "desc-null", short_description=None)
    _make_place(db_session, place_factory, "desc-empty", short_description="")
    _make_place(db_session, place_factory, "desc-title", title="Повтор названия", short_description="Повтор названия")
    _make_place(db_session, place_factory, "desc-short", short_description="Коротко")
    _make_place(db_session, place_factory, "desc-placeholder", short_description="Описание будет добавлено")
    _make_place(db_session, place_factory, "desc-good", short_description="Хорошее подробное описание места для туристической карточки.")

    queue = _queue(_payload(client), "no_description")
    reasons = _reasons(queue)

    assert queue["total_count"] == 5
    assert reasons["description_null"]["count"] == 1
    assert reasons["description_empty"]["count"] == 1
    assert reasons["description_equals_title"]["count"] == 1
    assert reasons["description_too_short"]["count"] >= 1
    assert reasons["placeholder_description"]["count"] == 1


def test_backlog_breakdown_has_no_technical_copy_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "tech-copy-guard", publication_status="needs_review", is_published=False, is_visible_in_catalog=False, is_route_eligible=False)

    payload = _payload(client)
    texts = []
    for queue in payload["queues"]:
        texts.extend([queue["title"], queue["recommended_action"]])
        texts.extend(reason["title"] for reason in queue["reasons"])
    text = " ".join(texts).casefold()

    for term in FORBIDDEN_COPY:
        assert term not in text, term


def test_backlog_breakdown_sample_endpoints_match_reason_counts_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "sample-no-photo", image_url=None)
    _make_place(db_session, place_factory, "sample-manual", publication_status="needs_review", is_published=False, is_visible_in_catalog=False, is_route_eligible=False)

    payload = _payload(client)

    for queue in payload["queues"]:
        response = client.get(queue["sample_endpoint"])
        assert response.status_code == 200, queue["code"]
        assert response.json()["total"] == queue["total_count"], queue["code"]
        for reason in queue["reasons"]:
            endpoint = reason.get("sample_endpoint")
            if endpoint is None:
                continue
            reason_response = client.get(endpoint)
            assert reason_response.status_code == 200, reason["code"]
            assert reason_response.json()["total"] == reason["count"], reason["code"]
