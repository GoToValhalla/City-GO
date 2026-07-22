from datetime import datetime

from data.scripts import import_cron_db
from data.scripts.city_coverage_report import parse_args as coverage_args
from data.scripts.import_city_osm import _apply_import, _normalize_osm_object, _save_source_observation, parse_args as import_args
from services.import_job_service import create_batch
from data.scripts.import_cron_config import load_targets, select_targets, split_csv
from data.scripts.run_due_import_jobs import parse_args as cron_args
from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from models.place_source_presence import PlaceSourcePresence
from models.source_observation import SourceObservation
from services.import_profiles import import_profile_tags, production_profile


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_import_city_osm_accepts_city_scope_profile_and_dry_run():
    args = import_args(["--city", "kutaisi", "--scope", "tourist_core", "--profile", "tourist_core", "--dry-run"])
    assert (args.city, args.scope, args.profile, args.dry_run) == ("kutaisi", "tourist_core", "tourist_core", True)


def test_city_coverage_report_accepts_scope():
    args = coverage_args(["--city", "yerevan", "--scope", "center"])
    assert (args.city, args.scope) == ("yerevan", "center")


def test_full_osm_is_not_production_profile():
    assert import_profile_tags("full_osm") == ("debug_only",)
    assert production_profile("full_osm") is False


def test_cron_import_args_accept_city_scope_and_apply():
    args = cron_args(["--city", "kutaisi,yerevan", "--scope", "tourist_core", "--apply"])
    assert split_csv(args.city) == ("kutaisi", "yerevan")
    assert split_csv(args.scope) == ("tourist_core",)
    assert args.apply is True


def test_import_target_config_contains_only_planned_cities():
    targets = load_targets()
    cities = {target["city"] for target in targets}
    selected = select_targets(targets, ("khanty-mansiysk",), ())
    assert cities == {
        "zelenogradsk",
        "kutaisi",
        "yerevan",
        "khanty-mansiysk",
        "kaliningrad",
        "almaty",
        "rostov-on-don",
        "astrakhan",
        "arkhangelsk",
    }
    assert {target["city"] for target in selected} == {"khanty-mansiysk"}


def test_apply_import_marks_scope_sources_missing(db_session):
    city = City(slug="zelenogradsk", name="Зеленоградск", country="Россия")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled")
    db_session.add(scope)
    db_session.commit()
    old_place = Place(city_id=city.id, slug="old", title="Old", lat=54.95, lng=20.48)
    db_session.add(old_place)
    db_session.commit()
    db_session.add(PlaceScopeLink(place_id=old_place.id, scope_id=scope.id, relation_type="imported_from_scope"))
    db_session.add(PlaceSourcePresence(place_id=old_place.id, source_type="osm", source_external_id="osm:node:old"))
    db_session.commit()

    raw = [{"type": "node", "id": 1, "lat": 54.96, "lon": 20.49, "tags": {"name": "Кофе", "amenity": "cafe"}}]
    result = _apply_import(db_session, city, scope, "tourist_core", raw, [_normalize_osm_object(raw[0], city.slug)])
    missing = db_session.query(PlaceSourcePresence).filter_by(source_external_id="osm:node:old").first()

    assert result["missing_from_source"] == 1
    assert missing.presence_status == "missing_once"


def _city_scope_batch(db_session, *, mode="apply"):
    city = City(slug="gdansk", name="Гданьск", country="Польша")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled")
    db_session.add(scope)
    db_session.commit()
    batch = create_batch(db_session, scope, mode=mode)
    return city, scope, batch


def _osm_item(source_external_id="osm:node:1"):
    return {
        "source_external_id": source_external_id,
        "source_url": "https://www.openstreetmap.org/node/1",
        "raw_name": "Cafe",
        "raw_category": "cafe",
        "raw_lat": 54.35,
        "raw_lng": 18.65,
        "raw_payload": {"tags": {"amenity": "cafe"}},
        "payload_hash": "hash1",
        "accepted": True,
        "rejection_reason": None,
    }


def test_save_source_observation_same_batch_same_item_produces_one_row_new(db_session):
    city, scope, batch = _city_scope_batch(db_session)
    item = _osm_item()

    first = _save_source_observation(db_session, city, scope, batch, item)
    second = _save_source_observation(db_session, city, scope, batch, item)
    db_session.commit()

    assert first.id == second.id
    rows = db_session.query(SourceObservation).filter_by(import_batch_id=batch.id).all()
    assert len(rows) == 1


def test_save_source_observation_different_batches_produce_two_rows_new(db_session):
    city, scope, batch_one = _city_scope_batch(db_session)
    batch_two = create_batch(db_session, scope, mode="apply")
    item = _osm_item()

    first = _save_source_observation(db_session, city, scope, batch_one, item)
    second = _save_source_observation(db_session, city, scope, batch_two, item)
    db_session.commit()

    assert first.id != second.id
    rows = db_session.query(SourceObservation).filter(
        SourceObservation.source_external_id == item["source_external_id"]
    ).all()
    assert len(rows) == 2


def test_save_source_observation_sets_correct_idempotency_key_new(db_session):
    city, scope, batch = _city_scope_batch(db_session)
    item = _osm_item()

    observation = _save_source_observation(db_session, city, scope, batch, item)
    db_session.commit()

    assert observation.idempotency_key == f"{batch.id}:{item['source_external_id']}"


def test_save_source_observation_duplicate_conflict_does_not_crash_new(db_session, monkeypatch):
    """Simulates a concurrent writer winning the race: the pre-insert lookup
    misses (as it would under real concurrency), a row with the same
    idempotency_key is already committed by the time the insert executes,
    and the IntegrityError path must recover instead of propagating."""
    city, scope, batch = _city_scope_batch(db_session)
    item = _osm_item()
    key = f"{batch.id}:{item['source_external_id']}"

    winner = SourceObservation(
        import_batch_id=batch.id,
        city_id=city.id,
        scope_id=scope.id,
        source_type="osm",
        source_external_id=item["source_external_id"],
        idempotency_key=key,
        payload_hash="concurrent-writer-hash",
        match_status="new_source_object",
        normalization_status="raw_only",
    )
    db_session.add(winner)
    db_session.commit()

    import data.scripts.import_city_osm as import_city_osm

    real_query = db_session.query
    call_count = {"n": 0}

    def _query_that_misses_once(model, *args, **kwargs):
        call_count["n"] += 1
        query = real_query(model, *args, **kwargs)
        if model is import_city_osm.SourceObservation and call_count["n"] == 1:
            return query.filter(SourceObservation.id == -1)
        return query

    monkeypatch.setattr(db_session, "query", _query_that_misses_once)

    result = _save_source_observation(db_session, city, scope, batch, item)
    db_session.commit()

    assert result.id == winner.id
    rows = db_session.query(SourceObservation).filter_by(idempotency_key=key).all()
    assert len(rows) == 1


def test_apply_import_never_fabricates_visit_duration_or_price_level_new(db_session):
    """CITYGO-265: a newly created place must never get a category-derived
    average_visit_duration_minutes/price_level -- OSM does not provide either
    of these for this item, and the former _visit_duration()/_price_level()
    per-category lookup tables fabricated them regardless, persisted as if
    they were real evidence. average_visit_duration_minutes specifically fed
    a real quality-score component (route_base_quality_score.base_quality_score)
    and a coverage predicate (place_coverage_counts.has_visit_duration), both
    unconditionally satisfied for every place as a result."""
    city, scope, batch = _city_scope_batch(db_session)
    raw = [{"type": "node", "id": 200, "lat": 54.35, "lon": 18.65, "tags": {"name": "No Fabrication Cafe", "amenity": "cafe"}}]
    normalized = [_normalize_osm_object(raw[0], city.slug)]

    _apply_import(db_session, city, scope, "tourist_core", raw, normalized)

    place = db_session.query(Place).filter_by(slug=normalized[0]["slug"]).one()
    assert place.average_visit_duration_minutes is None
    assert place.price_level is None


def test_apply_import_sets_created_outcome_for_new_place_new(db_session):
    city, scope, batch = _city_scope_batch(db_session)
    raw = [{"type": "node", "id": 100, "lat": 54.35, "lon": 18.65, "tags": {"name": "New Cafe", "amenity": "cafe"}}]
    normalized = [_normalize_osm_object(raw[0], city.slug)]

    _apply_import(db_session, city, scope, "tourist_core", raw, normalized)

    observation = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:100"
    ).first()
    assert observation.processing_outcome == "created"


def test_apply_import_sets_unchanged_outcome_on_second_identical_run_new(db_session):
    city, scope, batch = _city_scope_batch(db_session)
    raw = [{"type": "node", "id": 101, "lat": 54.35, "lon": 18.65, "tags": {"name": "Same Cafe", "amenity": "cafe"}}]
    normalized = [_normalize_osm_object(raw[0], city.slug)]

    _apply_import(db_session, city, scope, "tourist_core", raw, normalized)
    _apply_import(db_session, city, scope, "tourist_core", raw, [_normalize_osm_object(raw[0], city.slug)])

    observation = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:101"
    ).order_by(SourceObservation.id.desc()).first()
    assert observation.processing_outcome == "unchanged"


def test_apply_import_sets_rejected_outcome_new(db_session):
    city, scope, batch = _city_scope_batch(db_session)
    raw = [{"type": "node", "id": 102, "lat": 54.35, "lon": 18.65, "tags": {}}]
    normalized = [_normalize_osm_object(raw[0], city.slug)]
    assert normalized[0]["accepted"] is False

    _apply_import(db_session, city, scope, "tourist_core", raw, normalized)

    observation = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:102"
    ).first()
    assert observation.processing_outcome == "rejected"


def test_completed_item_has_non_null_outcome_new(db_session):
    city, scope, batch = _city_scope_batch(db_session)
    raw = [{"type": "node", "id": 103, "lat": 54.35, "lon": 18.65, "tags": {"name": "Complete Cafe", "amenity": "cafe"}}]
    normalized = [_normalize_osm_object(raw[0], city.slug)]

    _apply_import(db_session, city, scope, "tourist_core", raw, normalized)

    observation = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:103"
    ).first()
    assert observation.processing_outcome is not None
    assert observation.canonical_place_id is not None


def test_crash_after_source_observation_creation_leaves_outcome_null_new(db_session, monkeypatch):
    city, scope, batch = _city_scope_batch(db_session)
    item = _osm_item(source_external_id="osm:node:104")

    observation = _save_source_observation(db_session, city, scope, batch, item)
    db_session.commit()

    assert observation.processing_outcome is None
    assert observation.canonical_place_id is None


def test_apply_import_sets_hidden_rejected_outcome_new(db_session):
    """Rejected item (e.g. closed source) whose existing matching Place gets
    hidden must persist the distinct hidden_rejected outcome, not the
    ambiguous legacy 'hidden' value."""
    city, scope, batch = _city_scope_batch(db_session)
    raw_first = [{"type": "node", "id": 105, "lat": 54.35, "lon": 18.65, "tags": {"name": "Closing Cafe", "amenity": "cafe"}}]
    _apply_import(db_session, city, scope, "tourist_core", raw_first, [_normalize_osm_object(raw_first[0], city.slug)])

    raw_closed = [{"type": "node", "id": 105, "lat": 54.35, "lon": 18.65, "tags": {"name": "Closing Cafe", "amenity": "cafe", "disused:amenity": "cafe"}}]
    normalized_closed = [_normalize_osm_object(raw_closed[0], city.slug)]
    assert normalized_closed[0]["accepted"] is False

    _apply_import(db_session, city, scope, "tourist_core", raw_closed, normalized_closed)

    observation = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:105"
    ).order_by(SourceObservation.id.desc()).first()
    assert observation.processing_outcome == "hidden_rejected"


def test_apply_import_sets_hidden_needs_review_outcome_new(db_session, monkeypatch):
    """decision.action == 'hidden' for an accepted item matched to an
    existing Place (e.g. bad incoming title, source_closed, etc.) must
    persist the distinct hidden_needs_review outcome, not the ambiguous
    legacy 'hidden' value. apply_accepted_import_to_place's own 'hidden'
    triggers are unreachable through this OSM caller today (normalization
    already filters bad titles/closed lifecycle before this point — same
    latent-unreachable-branch pattern as the 'duplicate' outcome), so this
    test forces the decision via monkeypatch to prove _apply_import's own
    outcome-mapping is correct independent of that upstream reachability gap."""
    city, scope, batch = _city_scope_batch(db_session)
    raw_first = [{"type": "node", "id": 106, "lat": 54.35, "lon": 18.65, "tags": {"name": "Real Cafe Name", "amenity": "cafe"}}]
    _apply_import(db_session, city, scope, "tourist_core", raw_first, [_normalize_osm_object(raw_first[0], city.slug)])

    raw_second = [{"type": "node", "id": 106, "lat": 54.35, "lon": 18.65, "tags": {"name": "Real Cafe Name Updated", "amenity": "cafe"}}]
    normalized_second = [_normalize_osm_object(raw_second[0], city.slug)]
    assert normalized_second[0]["accepted"] is True

    import data.scripts.import_city_osm as import_city_osm
    from services.place_import_lifecycle_service import PlaceImportDecision

    def _force_hidden_decision(*, place, item, category_id):
        return PlaceImportDecision(
            action="hidden",
            status="draft",
            is_active=False,
            changed_fields=["title"],
            review_reasons=["forced_for_test"],
        )

    monkeypatch.setattr(import_city_osm, "apply_accepted_import_to_place", _force_hidden_decision)

    _apply_import(db_session, city, scope, "tourist_core", raw_second, normalized_second)

    observation = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:106"
    ).order_by(SourceObservation.id.desc()).first()
    assert observation.processing_outcome == "hidden_needs_review"


def test_hidden_outcomes_are_distinguishable_and_map_to_correct_counters_new(db_session, monkeypatch):
    """Exact counter mapping must be able to tell the two hidden paths apart:
    hidden_rejected contributes to rejected_count semantics, hidden_needs_review
    contributes to published/needs_review semantics — never the ambiguous
    ex-'hidden' value for either."""
    city, scope, batch = _city_scope_batch(db_session)

    raw_a = [{"type": "node", "id": 107, "lat": 54.35, "lon": 18.65, "tags": {"name": "Cafe A", "amenity": "cafe"}}]
    _apply_import(db_session, city, scope, "tourist_core", raw_a, [_normalize_osm_object(raw_a[0], city.slug)])
    raw_a_closed = [{"type": "node", "id": 107, "lat": 54.35, "lon": 18.65, "tags": {"name": "Cafe A", "amenity": "cafe", "disused:amenity": "cafe"}}]
    _apply_import(db_session, city, scope, "tourist_core", raw_a_closed, [_normalize_osm_object(raw_a_closed[0], city.slug)])

    raw_b = [{"type": "node", "id": 108, "lat": 54.36, "lon": 18.66, "tags": {"name": "Cafe B", "amenity": "cafe"}}]
    _apply_import(db_session, city, scope, "tourist_core", raw_b, [_normalize_osm_object(raw_b[0], city.slug)])
    raw_b_updated = [{"type": "node", "id": 108, "lat": 54.36, "lon": 18.66, "tags": {"name": "Cafe B Updated", "amenity": "cafe"}}]
    normalized_b_updated = [_normalize_osm_object(raw_b_updated[0], city.slug)]

    import data.scripts.import_city_osm as import_city_osm
    from services.place_import_lifecycle_service import PlaceImportDecision

    def _force_hidden_decision(*, place, item, category_id):
        return PlaceImportDecision(
            action="hidden",
            status="draft",
            is_active=False,
            changed_fields=["title"],
            review_reasons=["forced_for_test"],
        )

    monkeypatch.setattr(import_city_osm, "apply_accepted_import_to_place", _force_hidden_decision)
    _apply_import(db_session, city, scope, "tourist_core", raw_b_updated, normalized_b_updated)

    hidden_rejected_count = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:107", processing_outcome="hidden_rejected"
    ).count()
    hidden_needs_review_count = db_session.query(SourceObservation).filter_by(
        source_external_id="osm:node:108", processing_outcome="hidden_needs_review"
    ).count()
    ambiguous_legacy_count = db_session.query(SourceObservation).filter(
        SourceObservation.processing_outcome == "hidden"
    ).count()

    assert hidden_rejected_count == 1
    assert hidden_needs_review_count == 1
    assert ambiguous_legacy_count == 0


def test_legacy_ambiguous_hidden_rows_do_not_crash_readers_new(db_session):
    """A pre-existing row with the old ambiguous 'hidden' value (written
    before this disambiguation) must remain readable without error."""
    city, scope, batch = _city_scope_batch(db_session)
    legacy = SourceObservation(
        import_batch_id=batch.id,
        city_id=city.id,
        scope_id=scope.id,
        source_type="osm",
        source_external_id="osm:node:legacy",
        idempotency_key=f"{batch.id}:osm:node:legacy",
        payload_hash="legacy-hash",
        match_status="matched_existing_place",
        normalization_status="linked_to_place",
        processing_outcome="hidden",
    )
    db_session.add(legacy)
    db_session.commit()

    reread = db_session.query(SourceObservation).filter_by(source_external_id="osm:node:legacy").first()
    assert reread.processing_outcome == "hidden"


def test_osm_import_creates_private_park_with_safe_name_without_photo_or_address_new(db_session):
    city = City(slug="park-city", name="Park City", country="Россия")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled")
    db_session.add(scope)
    db_session.commit()
    raw = [{"type": "way", "id": 11, "center": {"lat": 54.96, "lon": 20.49}, "tags": {"leisure": "park"}}]

    result = _apply_import(db_session, city, scope, "tourist_core", raw, [_normalize_osm_object(raw[0], city.slug)])
    place = db_session.query(Place).filter_by(city_id=city.id).one()

    assert result["created"] == 1
    assert place.title.startswith("Парк OSM")
    assert place.address is None
    assert place.image_url is None
    assert place.is_published is False
    assert place.publication_status == "needs_review"


def test_osm_import_rejects_unnamed_cafe_but_keeps_source_observation_new(db_session):
    city = City(slug="cafe-city", name="Cafe City", country="Россия")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="food_area", name="Food", enabled=True, status="enabled")
    db_session.add(scope)
    db_session.commit()
    raw = [{"type": "node", "id": 12, "lat": 54.96, "lon": 20.49, "tags": {"amenity": "cafe"}}]

    result = _apply_import(db_session, city, scope, "food_and_coffee", raw, [_normalize_osm_object(raw[0], city.slug)])
    observation = db_session.query(SourceObservation).filter_by(city_id=city.id).one()

    assert result["created"] == 0
    assert result["rejection_reasons"]["missing_name"] == 1
    assert db_session.query(Place).filter_by(city_id=city.id).count() == 0
    assert observation.rejection_reason == "missing_name"


def test_cron_lock_keeps_paused_scope_paused(db_session, monkeypatch):
    city = City(slug="kutaisi", name="Кутаиси", country="Грузия")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="paused")
    db_session.add(scope)
    db_session.commit()
    monkeypatch.setattr(import_cron_db, "SessionLocal", lambda: _SessionContext(db_session))

    result = import_cron_db.lock_target(
        {"city": "kutaisi", "scope": "tourist_core", "profile": "tourist_core", "bbox": {}, "refresh_interval_hours": 168},
        datetime.utcnow(),
        True,
    )

    assert result == {"status": "skipped", "reason": "scope_disabled"}
    assert scope.status == "paused"
