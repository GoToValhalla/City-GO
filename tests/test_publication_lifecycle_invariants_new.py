"""CITYGO-339..344: import/enrichment must never publish or unpublish a live
Place row; only explicit admin actions may. One independent regression test
per ticket, plus the extra scenarios required by the task: approve/reject
proposed field changes, published-place preservation during import and
enrichment, unpublished place cannot auto-publish, single-place/city-wide
publication parity, and a persisted Python/SQL eligibility parity matrix.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.place_publication_decision import PlacePublicationDecision
from models.review_queue_item import ReviewQueueItem
from services.admin_city_publication_service import publish_city
from services.admin_service import publish_place
from services.canonical_publication_apply import apply_canonical_publication_verdict
from services.canonical_publication_guard import CanonicalPublicationVerdict, assess_place_import_decision, evaluate_canonical_publication
from services.import_pipeline_publication import apply_pipeline_publication
from services.place_import_lifecycle_service import apply_accepted_import_to_place
from services.route_eligibility_policy import compile_route_eligible_sql_conditions, evaluate_place_route_eligibility


def _job(db_session, city) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import")
    db_session.add(job)
    db_session.commit()
    return job


# --- CITYGO-339: import path must only record decision/evidence, never publish/unpublish ---


def test_citygo_339_mid_pipeline_publication_never_auto_publishes(db_session, city_factory, place_factory):
    """The mid-pipeline step (evidence_allowed=False, always, for this step)
    must never call the live-publish writer — a trusted, otherwise
    publish-quality, not-yet-public place stays unpublished and only gets a
    recorded decision + review item, never a live publish."""
    city = city_factory(slug="citygo-339-city")
    place = place_factory(
        city_id=city.id, slug="citygo-339-place", category="cafe", address="Main 1",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="needs_review",
    )
    place.source = "osm"
    place.confidence = 0.9
    db_session.commit()
    job = _job(db_session, city)
    counters: dict[str, int] = {}

    apply_pipeline_publication(db_session, city, job, place, counters, evidence_allowed=False)
    db_session.commit()
    db_session.refresh(place)

    assert place.is_published is False
    decision_rows = db_session.query(PlacePublicationDecision).filter_by(place_id=place.id).count()
    assert decision_rows >= 1


def test_citygo_339_hard_reject_still_hides_already_live_place_as_quality_enforcement(db_session, city_factory, place_factory):
    """Hard safety rejection (here: blank title) is quality enforcement, not
    the "publish" action CITYGO-339 targets — it has always been allowed to
    hide even an already-live place (canonical_publication_guard's own
    "hard safety rejection always wins" contract), and
    tests/test_import_pipeline_foundation_safety.py locks in the same
    behavior for invalid coordinates and hard-excluded categories."""
    city = city_factory(slug="citygo-339-city-2")
    place = place_factory(city_id=city.id, slug="citygo-339-place-2", title="", category="cafe")
    assert place.is_published is True
    job = _job(db_session, city)
    counters: dict[str, int] = {}

    apply_pipeline_publication(db_session, city, job, place, counters, evidence_allowed=False)
    db_session.commit()
    db_session.refresh(place)

    assert place.is_published is False
    assert place.publication_status == "archived"


# --- CITYGO-340: already-public places preserve live publication for review outcomes; hard reject stays separate ---


def test_citygo_340_already_public_place_preserves_publication_for_review_outcome():
    place = Place(
        city_id=1, title="Public Cafe", category="coffee", lat=54.9, lng=20.4,
        source="osm", confidence=0.3, is_active=True, status="active",
        is_published=True, is_visible_in_catalog=True,
    )
    decision = assess_place_import_decision(place)
    verdict = evaluate_canonical_publication(place, import_decision=decision, evidence_allowed=True)

    assert verdict.outcome == "preserve_public"


def test_citygo_340_hard_reject_is_separate_from_preserve_public_even_for_public_place():
    place = Place(
        city_id=1, title="Public Cafe", category="coffee", lat=0.0, lng=0.0,
        source="osm", confidence=0.9, is_active=True, status="active",
        is_published=True, is_visible_in_catalog=True,
    )
    decision = assess_place_import_decision(place)
    verdict = evaluate_canonical_publication(place, import_decision=decision, evidence_allowed=True)

    assert verdict.outcome == "reject"


def test_citygo_340_unpublished_auto_publish_quality_becomes_review_not_live_publish_without_evidence():
    place = Place(
        city_id=1, title="Cafe", category="coffee", lat=54.9, lng=20.4,
        source="osm", confidence=0.9, address="Main 1", is_active=True, status="active",
        is_published=False, is_visible_in_catalog=False,
    )
    decision = assess_place_import_decision(place)
    verdict = evaluate_canonical_publication(place, import_decision=decision, evidence_allowed=False)

    assert verdict.outcome == "blocked"
    assert place.is_published is False


# --- CITYGO-341: import actors cannot change live publication flags; writer consolidated ---


def test_citygo_341_record_only_apply_never_calls_live_writer(db_session, city_factory, place_factory):
    city = city_factory(slug="citygo-341-city")
    place = place_factory(city_id=city.id, slug="citygo-341-place", is_published=False, is_visible_in_catalog=False, publication_status="needs_review")
    verdict = CanonicalPublicationVerdict(
        outcome="publish", reasons=("quality_ok",),
        import_decision=assess_place_import_decision(place), lineage={},
    )

    key = apply_canonical_publication_verdict(db_session, place, verdict, job_id=None, snapshot_id=None, record_only=True)
    db_session.commit()
    db_session.refresh(place)

    assert key == "review_required"
    assert place.is_published is False
    assert place.is_visible_in_catalog is False


def test_citygo_341_non_record_only_apply_still_publishes_for_admin_finalize_paths(db_session, city_factory, place_factory):
    """The non-record-only mode (used by the evidence-gated finalize path,
    not by any import actor mid-pipeline) must still work — this proves the
    record_only flag is additive, not a removal of the writer's capability."""
    city = city_factory(slug="citygo-341-city-2")
    place = place_factory(city_id=city.id, slug="citygo-341-place-2", is_published=False, is_visible_in_catalog=False, publication_status="needs_review", category="cafe")
    verdict = CanonicalPublicationVerdict(
        outcome="publish", reasons=("quality_ok",),
        import_decision=assess_place_import_decision(place), lineage={},
    )

    key = apply_canonical_publication_verdict(db_session, place, verdict, job_id=None, snapshot_id=None, record_only=False)
    db_session.commit()
    db_session.refresh(place)

    assert key in {"auto_published", "limited_published"}
    assert place.is_published is True


# --- CITYGO-342: no proposed-field overwrite of live Place before approval; published stays public ---


def test_citygo_342_published_place_change_set_persisted_without_live_overwrite(db_session, place_factory):
    place = place_factory(slug="citygo-342-place", title="Old Title", address="Old Addr")
    item = {
        "title": "Old Title", "short_description": None, "category": place.category,
        "raw_lat": place.lat, "raw_lng": place.lng, "source_url": None,
        "lifecycle_status": "active", "opening_hours": None, "website": None, "phone": None,
        "address": "New Addr",
    }

    decision = apply_accepted_import_to_place(place, item, category_id=place.category_id)
    db_session.commit()
    db_session.refresh(place)

    assert decision.action == "needs_review"
    assert decision.change_set["address"] == {"before": "Old Addr", "after": "New Addr"}
    assert place.address == "Old Addr"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True


def test_citygo_342_unpublished_place_diff_applies_and_stays_hidden(db_session, place_factory):
    place = place_factory(
        slug="citygo-342-place-2", title="Old Title", address="Old Addr",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="needs_review",
    )
    item = {
        "title": "Old Title", "short_description": None, "category": place.category,
        "raw_lat": place.lat, "raw_lng": place.lng, "source_url": None,
        "lifecycle_status": "active", "opening_hours": None, "website": None, "phone": None,
        "address": "New Addr",
    }

    decision = apply_accepted_import_to_place(place, item, category_id=place.category_id)

    assert decision.action == "needs_review"
    assert place.address == "New Addr"
    assert place.is_published is False


# --- CITYGO-343: single-place publish uses the same canonical writer + route eligibility as city-wide ---


def test_citygo_343_publish_place_uses_evaluated_route_eligibility_not_hardcoded_true(db_session, city_factory, place_factory):
    city = city_factory(slug="citygo-343-city")
    # Category "bank" is hard-excluded from route eligibility but otherwise
    # publication-eligible, so publish_place must publish it with
    # is_route_eligible=False rather than hardcoding True.
    place = place_factory(
        city_id=city.id, slug="citygo-343-place", category="cafe",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="draft",
    )
    place.transport_required = True  # excludes from route eligibility, still catalog-publishable
    db_session.commit()

    published = publish_place(db_session, place.id, actor="admin-test")

    assert published.is_published is True
    assert published.is_route_eligible is False


def test_stage2_validation_publish_place_grants_route_eligible_true_for_qualifying_place(db_session, city_factory, place_factory):
    """Stage 2 production validation blocker (found 2026-07-16): a place
    that genuinely qualifies for routes (museum, active, tourist_catalog,
    not transport-required) must become is_route_eligible=True on publish
    — apply_admin_city_publication_place used to evaluate the route policy
    BEFORE setting is_published/is_visible_in_catalog, so the policy always
    saw a draft and returned False regardless of the place's real
    category/quality. The only prior regression test for this path used
    transport_required=True, which is excluded from routes independently
    of the publish-timing bug, so it never caught this."""
    city = city_factory(slug="stage2-validation-route-eligible-city")
    place = place_factory(
        city_id=city.id, slug="stage2-validation-route-eligible-place", category="museum",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="draft",
    )
    place.canonical_category = "museum"
    db_session.commit()

    published = publish_place(db_session, place.id, actor="admin-test")

    assert published.is_published is True
    assert published.is_route_eligible is True
    assert published.route_exclusion_reason is None


def test_citygo_343_python_sql_coordinate_zero_parity(db_session, city_factory, place_factory):
    city = city_factory(slug="citygo-343-city-2")
    place = place_factory(
        city_id=city.id, slug="citygo-343-equator-place", category="museum",
        lat=0.0, lng=45.0,
    )

    python_verdict = evaluate_place_route_eligibility(place)
    sql_conditions = compile_route_eligible_sql_conditions()
    sql_row = db_session.execute(select(Place.id).where(Place.id == place.id, *sql_conditions)).first()

    assert "invalid_coordinates" not in python_verdict.reasons
    assert sql_row is not None, "SQL must not reject a place with only one coordinate at 0.0"


def test_citygo_343_python_sql_both_coordinates_zero_parity(db_session, city_factory, place_factory):
    city = city_factory(slug="citygo-343-city-3")
    place = place_factory(city_id=city.id, slug="citygo-343-null-island", category="museum", lat=0.0, lng=0.0)

    python_verdict = evaluate_place_route_eligibility(place)
    sql_conditions = compile_route_eligible_sql_conditions()
    sql_row = db_session.execute(select(Place.id).where(Place.id == place.id, *sql_conditions)).first()

    assert "invalid_coordinates" in python_verdict.reasons
    assert sql_row is None


# --- CITYGO-344: single-place and city-wide publication are identical ---


def test_citygo_344_single_place_and_city_wide_publish_produce_identical_flags(db_session, city_factory, place_factory):
    city_a = city_factory(slug="citygo-344-city-a", launch_status="review_required", is_active=False)
    city_b = city_factory(slug="citygo-344-city-b", launch_status="review_required", is_active=False)
    place_a = place_factory(
        city_id=city_a.id, slug="citygo-344-place-a", category="cafe",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="draft",
    )
    place_b = place_factory(
        city_id=city_b.id, slug="citygo-344-place-b", category="cafe",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="draft",
    )

    published_a = publish_place(db_session, place_a.id, actor="admin-test")
    result_b = publish_city(db_session, city_b.id, actor="admin-test", override_readiness_gate=True)
    db_session.refresh(place_b)

    assert published_a.is_published is True
    assert place_b.is_published is True
    assert published_a.is_route_eligible == place_b.is_route_eligible
    assert published_a.publication_status == place_b.publication_status == "published"
    assert result_b.places_published == 1


# --- extra required scenario: enrichment/cleanup never unpublishes published places ---


def test_cleanup_never_unpublishes_published_place_only_flags_for_review(db_session, city_factory, place_factory):
    from data.scripts.cleanup_imported_places_quality import _cleanup_city

    city = city_factory(slug="cleanup-preserve-city")
    place = place_factory(city_id=city.id, slug="cleanup-preserve-place", category="transport")
    assert place.is_published is True

    result = _cleanup_city(db=db_session, city=city, apply=True, sample_limit=10)
    db_session.commit()
    db_session.refresh(place)

    assert place.is_published is True
    assert place.is_active is True
    assert result["hidden_applied"] == 0
    assert result["review_flagged"] == 1
    review_rows = db_session.query(ReviewQueueItem).filter_by(place_id=place.id).count()
    assert review_rows == 1


def test_cleanup_still_hides_unpublished_bad_place(db_session, city_factory, place_factory):
    from data.scripts.cleanup_imported_places_quality import _cleanup_city

    city = city_factory(slug="cleanup-hide-city")
    place = place_factory(
        city_id=city.id, slug="cleanup-hide-place", category="transport",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="draft",
    )

    result = _cleanup_city(db=db_session, city=city, apply=True, sample_limit=10)
    db_session.commit()
    db_session.refresh(place)

    assert place.is_active is False
    assert result["hidden_applied"] == 1


def test_enrichment_quality_cleanup_step_preserves_published_places(db_session, city_factory, place_factory, monkeypatch):
    """The enrichment-only pipeline calls the same cleanup function used
    standalone — proving CITYGO-341's fix at the shared function protects
    both call sites without touching enrichment_only.py itself."""
    from data.scripts.cleanup_imported_places_quality import run as run_quality_cleanup

    city = city_factory(slug="enrichment-preserve-city")
    place = place_factory(city_id=city.id, slug="enrichment-preserve-place", category="transport")
    assert place.is_published is True

    monkeypatch.setattr("data.scripts.cleanup_imported_places_quality.SessionLocal", lambda: db_session)
    db_session.close = lambda: None

    run_quality_cleanup(["--city", city.slug, "--apply"])
    db_session.refresh(place)

    assert place.is_published is True


# --- extra required scenario: unpublished place cannot auto-publish via the mid-pipeline step ---


def test_unpublished_place_cannot_auto_publish_via_mid_pipeline_step(db_session, city_factory, place_factory):
    city = city_factory(slug="no-auto-publish-city")
    place = place_factory(
        city_id=city.id, slug="no-auto-publish-place", category="cafe",
        is_published=False, is_visible_in_catalog=False, is_route_eligible=False,
        is_searchable=False, publication_status="needs_review",
    )
    place.source = "osm"
    place.confidence = 0.9
    place.address = "Main 1"
    db_session.commit()
    job = _job(db_session, city)
    counters: dict[str, int] = {}

    apply_pipeline_publication(db_session, city, job, place, counters, evidence_allowed=False)
    db_session.commit()
    db_session.refresh(place)

    assert place.is_published is False


# --- extra required scenario: persisted Python/SQL eligibility parity matrix ---


@pytest.mark.parametrize(
    "lat,lng,category,is_published,is_visible,publication_status,expect_eligible",
    [
        (54.9, 20.4, "museum", True, True, "published", True),
        (0.0, 45.0, "museum", True, True, "published", True),
        (45.0, 0.0, "museum", True, True, "published", True),
        (0.0, 0.0, "museum", True, True, "published", False),
        (54.9, 20.4, "pharmacy", True, True, "published", False),
        (54.9, 20.4, "museum", False, True, "published", False),
        (54.9, 20.4, "museum", True, False, "published", False),
        (54.9, 20.4, "museum", True, True, "needs_review", False),
    ],
)
def test_persisted_python_sql_eligibility_parity_matrix(
    db_session, city_factory, place_factory,
    lat, lng, category, is_published, is_visible, publication_status, expect_eligible,
):
    city = city_factory(slug=f"parity-city-{lat}-{lng}-{category}-{is_published}-{is_visible}-{publication_status}".replace(".", "_").replace(" ", ""))
    place = place_factory(
        city_id=city.id,
        slug=f"parity-place-{lat}-{lng}-{category}-{is_published}-{is_visible}-{publication_status}".replace(".", "_").replace(" ", ""),
        category=category, lat=lat, lng=lng,
        is_published=is_published, is_visible_in_catalog=is_visible,
        is_route_eligible=True, publication_status=publication_status,
    )
    db_session.commit()

    python_verdict = evaluate_place_route_eligibility(place)
    sql_conditions = compile_route_eligible_sql_conditions()
    sql_row = db_session.execute(select(Place.id).where(Place.id == place.id, *sql_conditions)).first()

    assert python_verdict.eligible is expect_eligible
    assert (sql_row is not None) is expect_eligible
