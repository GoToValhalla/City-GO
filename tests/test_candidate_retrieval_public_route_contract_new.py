"""Regression tests for CITYGO-355.

Root cause: CandidateRetrievalService._base_query() used the place-level-only
route_eligible_sql_conditions() plus a separate, weaker manual City gate
(`is_active` and `launch_status not in {disabled, archived, hidden}`) for
public (non-admin) retrieval. That manual gate did NOT require
`launch_status == "published"`, so active cities in preview/preparing status
(any launch_status other than disabled/archived/hidden) could return public
route candidates. Fixed by routing public retrieval through the existing
canonical contract `services.route_eligibility.public_route_eligible_sql_conditions()`,
which composes `services.place_public_visibility.public_place_conditions()`
(requires City.is_active AND City.launch_status == "published") with the
place-level route eligibility conditions.

These tests use a real (SQLite, in-memory) database session via the
place_factory/city_factory fixtures, calling CandidateRetrievalService
directly — the same style as the existing
tests/test_candidate_retrieval_city_wide_fallback_new.py.
"""

from __future__ import annotations

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.candidate_retrieval_service import CandidateRetrievalService


def _ctx(*, city_id: str | None, is_admin: bool = False, radius_meters: int = 5000) -> MergedContext:
    return MergedContext(
        location=(54.9611, 20.4703),
        city_id=city_id,
        is_admin=is_admin,
        timezone="Europe/Moscow",
        time_budget_minutes=240,
        effective_time_budget_minutes=240,
        time_of_day=None,
        route_time_mode="flexible",
        interests=[],
        avoided_categories=[],
        avoided_place_ids=[],
        budget_level=BudgetLevel.MID,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
        radius_meters=radius_meters,
        effective_num_stops=6,
        min_stop_duration_minutes=20,
    )


# --- Published city -> candidates returned -----------------------------


def test_published_city_returns_public_candidates_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="published-city", launch_status="published")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    result_ids = {row.id for row in db_session.execute(query).scalars().all()}

    assert place.id in result_ids


# --- Preview/preparing city -> zero public candidates -------------------


def test_preview_city_returns_zero_public_candidates_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="preview-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    result = db_session.execute(query).scalars().all()

    assert result == []


def test_preparing_city_returns_zero_public_candidates_new(db_session, city_factory, published_place_factory) -> None:
    """"preparing" was never in BLOCKED_CITY_LAUNCH_STATUSES ({disabled,
    archived, hidden}), so the old manual gate let it through — the exact
    regression this task fixes."""
    city = city_factory(slug="preparing-city", launch_status="preparing")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    result = db_session.execute(query).scalars().all()

    assert result == []


# --- Hidden/archived/disabled city -> zero candidates --------------------


def test_hidden_city_returns_zero_candidates_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="hidden-city", launch_status="hidden")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_archived_city_returns_zero_candidates_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="archived-city", launch_status="archived")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_disabled_city_returns_zero_candidates_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="disabled-city", launch_status="disabled")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_inactive_published_city_returns_zero_candidates_new(db_session, city_factory, published_place_factory) -> None:
    """launch_status == "published" alone is not enough; City.is_active must
    also be True."""
    city = city_factory(slug="inactive-city", launch_status="published", is_active=False)
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


# --- Unpublished/invisible/service-only/forbidden/non-route-eligible places
# remain excluded -----------------------------------------------------------


def test_unpublished_place_excluded_in_published_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="pub-city-1", launch_status="published")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703, is_published=False)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_invisible_place_excluded_in_published_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="pub-city-2", launch_status="published")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703, is_visible_in_catalog=False)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_non_route_eligible_place_excluded_in_published_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="pub-city-3", launch_status="published")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703, is_route_eligible=False)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_service_only_place_excluded_in_published_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="pub-city-4", launch_status="published")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)
    place.internal_status = "service_only"
    db_session.add(place)
    db_session.commit()

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_hard_excluded_category_place_excluded_in_published_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="pub-city-5", launch_status="published")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)
    place.canonical_category = "pharmacy"
    db_session.add(place)
    db_session.commit()

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


def test_unpublished_status_place_excluded_via_publication_status_new(db_session, city_factory, published_place_factory) -> None:
    """publication_status must be one of the allowed set even when the
    boolean flags are true — "unpublished"/"draft"/"rejected" etc. must not
    leak through."""
    city = city_factory(slug="pub-city-6", launch_status="published")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703, publication_status="draft")

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


# --- Radius expansion and city-wide fallback inherit the same contract ----


def test_expanded_radius_fallback_excludes_preview_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="preview-radius-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    result = service._fallback_expand_radius(db_session, ctx)

    assert result == []


def test_city_wide_fallback_excludes_preview_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="preview-citywide-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    result = service._fallback_city_wide(db_session, ctx)

    assert result == []


def test_city_wide_fallback_includes_published_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="published-citywide-city", launch_status="published")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    result_ids = {row.id for row in service._fallback_city_wide(db_session, ctx)}

    assert place.id in result_ids


def test_get_candidates_end_to_end_excludes_preview_city_new(db_session, city_factory, published_place_factory) -> None:
    """End-to-end through get_candidates (radius -> expanded -> city-wide ->
    route-visible fallbacks) must never surface a preview-city place to a
    public caller."""
    city = city_factory(slug="preview-e2e-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    result = service.get_candidates(db_session, ctx)

    assert result == []


def test_get_candidates_end_to_end_includes_published_city_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="published-e2e-city", launch_status="published")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    result = service.get_candidates(db_session, ctx)

    assert {p.id for p in result} == {place.id}


# --- Admin preview is not regressed ---------------------------------------


def test_admin_preview_still_returns_preview_city_candidates_new(db_session, city_factory, published_place_factory) -> None:
    """Admin preview must remain unaffected by the public-contract fix: it
    intentionally does not require city publication (see
    admin_preview_route_eligible_sql_conditions's docstring)."""
    city = city_factory(slug="admin-preview-city", launch_status="preview")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug, is_admin=True)
    query = service._base_query(db_session, ctx)
    result_ids = {row.id for row in db_session.execute(query).scalars().all()}

    assert place.id in result_ids


def test_admin_preview_still_returns_hidden_city_candidates_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="admin-hidden-city", launch_status="hidden")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug, is_admin=True)
    query = service._base_query(db_session, ctx)
    result_ids = {row.id for row in db_session.execute(query).scalars().all()}

    assert place.id in result_ids


def test_admin_preview_still_excludes_non_route_eligible_place_new(db_session, city_factory, published_place_factory) -> None:
    """Admin preview skips city publication but must still respect
    place-level route eligibility — it is not an unconditional bypass."""
    city = city_factory(slug="admin-place-gate-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703, is_route_eligible=False)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug, is_admin=True)
    query = service._base_query(db_session, ctx)
    assert db_session.execute(query).scalars().all() == []


# --- Destination-aware retrieval does not weaken the public contract ------


def test_destination_route_reads_disabled_by_default_preserves_public_contract_new(
    db_session, city_factory, published_place_factory
) -> None:
    """With the destination-reads feature toggle at its default (off), a
    destination_slug on the context must not change the public
    preview-city-excluded outcome."""
    city = city_factory(slug="destination-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    service = CandidateRetrievalService()
    ctx = _ctx(city_id=city.slug)
    ctx.destination_slug = "some-destination"
    query = service._base_query(db_session, ctx)

    assert db_session.execute(query).scalars().all() == []
