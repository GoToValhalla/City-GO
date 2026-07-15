"""Truthful import funnel and rejection breakdown (Task 1.1).

Every assertion here reads a counter that _apply_import/_process_one_item
already computes at the exact point the decision is made — nothing in this
test file, or in the code under test, recomputes a funnel value from a
different source. See data/scripts/import_city_osm.py::_apply_import for
the funnel construction and services/admin_city_import_runner.py::
summarize_import_results for the cross-scope aggregation (sum, never pick
one result over another — see the found=136/saved=0 regression this
builds on).
"""

from __future__ import annotations

from typing import Any

from data.scripts.import_city_osm import _apply_import, _normalize_osm_object
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from models.place import Place
from services.admin_city_import_job_payload import build_import_job_payload
from services.admin_city_import_runner import summarize_import_results


def _city_and_scope(db_session, slug: str = "funnel-city") -> tuple[City, CityImportScope]:
    city = City(slug=slug, name="Funnel City", country="Test")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled")
    db_session.add(scope)
    db_session.commit()
    return city, scope


def _node(osm_id: int, *, name: str = "Кафе", amenity: str = "cafe", lat: float = 54.9, lng: float = 20.5, extra_tags: dict[str, Any] | None = None) -> dict[str, Any]:
    tags = {"name": name, "amenity": amenity}
    if extra_tags:
        tags.update(extra_tags)
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lng, "tags": tags}


def _apply(db_session, city, scope, raw: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_normalize_osm_object(item, city.slug) for item in raw]
    return _apply_import(db_session, city, scope, "tourist_core", raw, normalized)


# --- unit: funnel stage values come from real decision points ---


def test_funnel_reports_fetched_normalized_and_accepted_for_all_new_places(db_session):
    city, scope = _city_and_scope(db_session)
    raw = [_node(1, name="Кафе Раз"), _node(2, name="Кафе Два"), _node(3, name="Кафе Три")]

    result = _apply(db_session, city, scope, raw)
    funnel = result["funnel"]

    assert funnel["requested"] == 3
    assert funnel["fetched"] == 3
    assert funnel["normalized"] == 3
    assert funnel["accepted"] == 3
    assert funnel["created"] == 3
    assert funnel["matched_existing"] == 0
    assert funnel["rejected_by_reason"] == {}


def test_funnel_records_rejection_reasons_with_counts_new(db_session):
    city, scope = _city_and_scope(db_session)
    raw = [
        _node(1, name=""),  # missing_name (cafe has no fallback title)
        _node(2, name=""),  # missing_name
        {"type": "node", "id": 3, "tags": {"name": "Без координат", "amenity": "cafe"}},  # missing_coordinates
        _node(4, amenity="atm"),  # hidden_category ("useful" is publicly hidden)
        _node(5, name="Кафе Пять"),  # accepted
    ]

    result = _apply(db_session, city, scope, raw)
    funnel = result["funnel"]

    assert funnel["rejected_by_reason"] == {"missing_name": 2, "missing_coordinates": 1, "hidden_category": 1}
    assert funnel["accepted"] == 1
    assert funnel["created"] == 1


def test_funnel_records_matched_existing_and_sent_to_review_on_real_change_new(db_session):
    """place_import_lifecycle_service.apply_accepted_import_to_place() routes
    every real field change on a matched place to needs_review (manual
    review gate), not a distinct "updated" outcome — the funnel must reflect
    that truthfully rather than assume an "updated" path that never fires
    for a matched place with changed data."""
    city, scope = _city_and_scope(db_session)
    raw = [_node(1, name="Кафе Раз")]
    _apply(db_session, city, scope, raw)

    changed_raw = [_node(1, name="Кафе Раз (обновлено)")]
    result = _apply(db_session, city, scope, changed_raw)
    funnel = result["funnel"]

    assert funnel["matched_existing"] == 1
    assert funnel["created"] == 0
    assert funnel["sent_to_review"] == 1


def test_funnel_records_unchanged_when_nothing_differs_new(db_session):
    city, scope = _city_and_scope(db_session)
    raw = [_node(1, name="Кафе Раз")]
    _apply(db_session, city, scope, raw)

    result = _apply(db_session, city, scope, raw)
    funnel = result["funnel"]

    assert funnel["matched_existing"] == 1
    assert funnel["unchanged"] == 1
    assert funnel["created"] == 0
    assert funnel["sent_to_review"] == 0


# --- deduplicated must be "unavailable", never fabricated as 0 ---


def test_funnel_reports_deduplicated_as_unavailable_not_zero_new(db_session):
    """No raw-object dedup step exists anywhere in this pipeline. Reporting
    0 would falsely claim "we checked and found no duplicates" when no
    check ever ran."""
    city, scope = _city_and_scope(db_session)
    result = _apply(db_session, city, scope, [_node(1)])

    assert result["funnel"]["deduplicated"] == "unavailable"
    assert result["funnel"]["deduplicated"] != 0


# --- totals-consistency invariant: every processed object ends in exactly one terminal state ---


def test_every_normalized_item_ends_in_exactly_one_terminal_funnel_state_new(db_session):
    city, scope = _city_and_scope(db_session)
    raw = [
        _node(1, name="Кафе Раз"),  # accepted, created
        _node(2, name=""),  # rejected: missing_name
        _node(3, amenity="atm"),  # rejected: hidden_category
        {"type": "node", "id": 4, "tags": {"name": "Плохо", "amenity": "cafe"}},  # rejected: missing_coordinates
    ]

    result = _apply(db_session, city, scope, raw)
    funnel = result["funnel"]

    accepted_terminal = funnel["created"] + funnel["updated"] + funnel["unchanged"] + funnel["hidden"] + funnel["sent_to_review"]
    rejected_terminal = sum(funnel["rejected_by_reason"].values())

    assert funnel["normalized"] == 4
    assert funnel["accepted"] == 1
    assert accepted_terminal == funnel["accepted"]
    assert rejected_terminal == funnel["normalized"] - funnel["accepted"]
    assert accepted_terminal + rejected_terminal == funnel["normalized"]


def test_rejection_reasons_are_deterministic_across_identical_runs_new(db_session):
    city_a, scope_a = _city_and_scope(db_session, slug="funnel-city-a")
    city_b, scope_b = _city_and_scope(db_session, slug="funnel-city-b")
    raw = [
        _node(1, name=""),  # missing_name
        _node(2, name=""),  # missing_name
        {"type": "node", "id": 3, "tags": {"name": "Без координат", "amenity": "cafe"}},  # missing_coordinates
    ]

    result_a = _apply(db_session, city_a, scope_a, raw)
    result_b = _apply(db_session, city_b, scope_b, raw)

    assert result_a["funnel"]["rejected_by_reason"] == result_b["funnel"]["rejected_by_reason"]
    assert result_a["funnel"]["rejected_by_reason"] == {"missing_name": 2, "missing_coordinates": 1}


# --- API-level: summarize_import_results aggregates the same funnel across scopes ---


def _payload(*import_results: dict[str, Any]) -> dict[str, Any]:
    return {
        "results": [
            {"status": "success", "scope": f"scope-{index}", "import_result": import_result}
            for index, import_result in enumerate(import_results)
        ]
    }


def test_summarize_import_results_sums_funnel_across_scopes_new():
    payload = _payload(
        {"raw_count": 5, "created": 2, "funnel": {
            "requested": 5, "fetched": 5, "deduplicated": "unavailable", "normalized": 5,
            "accepted": 4, "rejected_by_reason": {"missing_name": 1}, "matched_existing": 0,
            "created": 2, "updated": 1, "unchanged": 1, "hidden": 0, "sent_to_review": 0, "failed": 0,
        }},
        {"raw_count": 3, "created": 1, "funnel": {
            "requested": 3, "fetched": 3, "deduplicated": "unavailable", "normalized": 3,
            "accepted": 3, "rejected_by_reason": {"unsupported_category": 1}, "matched_existing": 1,
            "created": 1, "updated": 0, "unchanged": 1, "hidden": 0, "sent_to_review": 1, "failed": 0,
        }},
    )

    summary = summarize_import_results(payload)
    funnel = summary["funnel"]

    assert funnel["requested"] == 8
    assert funnel["fetched"] == 8
    assert funnel["normalized"] == 8
    assert funnel["accepted"] == 7
    assert funnel["created"] == 3
    assert funnel["updated"] == 1
    assert funnel["unchanged"] == 2
    assert funnel["sent_to_review"] == 1
    assert funnel["matched_existing"] == 1
    assert funnel["rejected_by_reason"] == {"missing_name": 1, "unsupported_category": 1}
    assert funnel["deduplicated"] == "unavailable"


def test_summarize_import_results_funnel_unavailable_when_every_scope_fails_new():
    """No scope ever reached _apply_import — the funnel itself must be
    unavailable, not a fabricated all-zero accounting."""
    payload = {"results": [
        {"status": "failed", "scope": "tourist_core", "error": "Too many OSM objects: 4660 > 2500"},
        {"status": "failed", "scope": "useful_services", "error": "HTTP 429"},
    ]}

    summary = summarize_import_results(payload)
    funnel = summary["funnel"]

    for key in ("requested", "fetched", "normalized", "accepted", "created", "updated", "unchanged", "sent_to_review", "hidden", "matched_existing", "failed"):
        assert funnel[key] == "unavailable", key
    assert funnel["deduplicated"] == "unavailable"
    assert funnel["rejected_by_reason"] == {}


def test_summarize_import_results_funnel_survives_bbox_fallback_new():
    """Regression companion to the found=136/saved=0 fix: the funnel must
    sum the original run and the fallback run, matching the same rule as
    the flat counters."""
    payload = _payload({
        "raw_count": 136, "created": 0, "updated": 0, "needs_review": 22,
        "funnel": {
            "requested": 136, "fetched": 136, "deduplicated": "unavailable", "normalized": 136,
            "accepted": 22, "rejected_by_reason": {"unsupported_category": 114}, "matched_existing": 0,
            "created": 0, "updated": 0, "unchanged": 0, "hidden": 0, "sent_to_review": 22, "failed": 0,
        },
        "fallback_result": {"import_result": {
            "raw_count": 0, "created": 0, "updated": 0, "needs_review": 0,
            "funnel": {
                "requested": 0, "fetched": 0, "deduplicated": "unavailable", "normalized": 0,
                "accepted": 0, "rejected_by_reason": {}, "matched_existing": 0,
                "created": 0, "updated": 0, "unchanged": 0, "hidden": 0, "sent_to_review": 0, "failed": 0,
            },
        }},
    })

    summary = summarize_import_results(payload)

    assert summary["places_found"] == 136
    assert summary["places_saved"] == 22
    assert summary["funnel"]["sent_to_review"] == 22
    assert summary["funnel"]["rejected_by_reason"] == {"unsupported_category": 114}


# --- negative / edge cases ---


def test_funnel_handles_zero_raw_objects_as_real_zero_not_unavailable_new(db_session):
    """An empty OSM query result is a legitimate zero (the scope really
    found nothing), not an unknown/unavailable state — the pipeline did
    run and did produce a truthful count."""
    city, scope = _city_and_scope(db_session)

    result = _apply(db_session, city, scope, [])
    funnel = result["funnel"]

    assert funnel["fetched"] == 0
    assert funnel["normalized"] == 0
    assert funnel["accepted"] == 0
    assert funnel["rejected_by_reason"] == {}
    assert funnel["deduplicated"] == "unavailable"


def test_summarize_import_results_partial_failure_still_sums_available_funnels_new():
    payload = {"results": [
        {"status": "success", "scope": "ok-scope", "import_result": {
            "raw_count": 4, "created": 4, "funnel": {
                "requested": 4, "fetched": 4, "deduplicated": "unavailable", "normalized": 4,
                "accepted": 4, "rejected_by_reason": {}, "matched_existing": 0,
                "created": 4, "updated": 0, "unchanged": 0, "hidden": 0, "sent_to_review": 0, "failed": 0,
            },
        }},
        {"status": "failed", "scope": "bad-scope", "error": "HTTP 504"},
    ]}

    summary = summarize_import_results(payload)
    funnel = summary["funnel"]

    assert funnel["fetched"] == 4
    assert funnel["created"] == 4
    assert "bad-scope: HTTP 504" in summary["last_error"]


# --- API: existing diagnostics/payload endpoint exposes the funnel ---


def test_admin_import_job_payload_exposes_funnel_from_import_diff_new(db_session, city_factory):
    """The existing import_execution_summary() reads job.step_details, which
    is where run_enrichment_pipeline already stores summarize_import_results'
    output (services/import_pipeline/runner.py: detail={"import_diff": summary}).
    No new write path is introduced — this proves the funnel this task adds
    to summarize_import_results reaches the existing admin API surface."""
    city = city_factory(slug="funnel-api-city")
    job = CityAdminImportJob(
        city_id=city.id, status="success", source="admin_city_import", current_step="ready_for_review",
        scopes_total=1, scopes_succeeded=1, places_found=5, places_saved=4,
        step_details={
            "collecting_places": {
                "import_diff": {
                    "status": "success", "scopes_total": 1, "scopes_succeeded": 1,
                    "places_found": 5, "places_saved": 4, "unchanged": 1, "hidden": 0, "rejected": 1,
                    "needs_review": 3,
                    "funnel": {
                        "requested": 5, "fetched": 5, "deduplicated": "unavailable", "normalized": 5,
                        "accepted": 4, "rejected_by_reason": {"missing_name": 1}, "matched_existing": 0,
                        "created": 1, "updated": 0, "unchanged": 1, "hidden": 0, "sent_to_review": 3, "failed": 0,
                    },
                },
            },
        },
    )
    db_session.add(job)
    db_session.commit()

    payload = build_import_job_payload(db_session, city)
    summary = payload["import_execution_summary"]

    assert summary["funnel"]["requested"] == 5
    assert summary["funnel"]["accepted"] == 4
    assert summary["funnel"]["rejected_by_reason"] == {"missing_name": 1}
    assert summary["funnel"]["deduplicated"] == "unavailable"
    assert summary["rejected_by_reason"] == {"missing_name": 1}


def test_admin_import_job_payload_funnel_is_none_not_zero_before_any_run_new(db_session, city_factory):
    """A city with no import job yet must not report a fabricated all-zero
    funnel — funnel must be None (genuinely unavailable), distinguishable
    from a real zero-object scope result."""
    city = city_factory(slug="funnel-api-no-job-city")

    payload = build_import_job_payload(db_session, city)
    summary = payload["import_execution_summary"]

    assert summary["funnel"] is None
    assert summary["rejected_by_reason"] is None
