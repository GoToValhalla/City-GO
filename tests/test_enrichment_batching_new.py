from data.scripts.enrich_place_images import _candidate_places_query
from models.place_image import PLACE_IMAGE_STATUS_APPROVED, PlaceImage
from services.import_pipeline import enrichment_only
from services.place_address_backfill import _iter_candidate_places


def test_image_candidate_query_skips_places_with_public_images_new(db_session, city_factory, place_factory):
    city = city_factory(slug="batch-photo-city", name="Batch Photo City")
    covered = place_factory(city_id=city.id, slug="covered", title="Covered Place")
    missing_one = place_factory(city_id=city.id, slug="missing-one", title="Missing One")
    missing_two = place_factory(city_id=city.id, slug="missing-two", title="Missing Two")
    db_session.add(
        PlaceImage(
            place_id=covered.id,
            image_url="https://example.com/covered.jpg",
            source_type="test",
            status=PLACE_IMAGE_STATUS_APPROVED,
            is_primary=True,
        )
    )
    db_session.commit()

    rows = _candidate_places_query(db_session, city, start_after_id=0).limit(10).all()

    assert [row.id for row in rows] == [missing_one.id, missing_two.id]


def test_address_candidate_iterator_uses_start_after_id_new(db_session, city_factory, place_factory):
    city = city_factory(slug="batch-address-city", name="Batch Address City")
    first = place_factory(city_id=city.id, slug="first", title="First", address="")
    second = place_factory(city_id=city.id, slug="second", title="Second", address="")
    place_factory(city_id=city.id, slug="with-address", title="With Address", address="Main Street 10")

    rows = list(_iter_candidate_places(db_session, city.slug, verify_existing=False, start_after_id=first.id))

    assert [row.id for row in rows] == [second.id]


def test_image_batches_advance_cursor_until_city_is_scanned_new(monkeypatch):
    calls: list[int] = []

    def fake_run_image_enrich(argv: list[str]) -> dict[str, object]:
        cursor = int(argv[argv.index("--start-after-id") + 1])
        calls.append(cursor)
        if cursor == 0:
            return {
                "scanned_places": enrichment_only.IMAGE_BATCH_LIMIT,
                "candidates_found": 10,
                "created": 4,
                "auto_approved": 4,
                "place_image_url_synced": 4,
                "skipped_duplicates": 1,
                "skipped_has_approved": 0,
                "skipped_ineligible": 2,
                "skipped_no_source": 43,
                "errors": [],
                "last_scanned_place_id": 2500,
            }
        return {
            "scanned_places": 5,
            "candidates_found": 2,
            "created": 1,
            "auto_approved": 1,
            "place_image_url_synced": 1,
            "skipped_duplicates": 0,
            "skipped_has_approved": 0,
            "skipped_ineligible": 0,
            "skipped_no_source": 4,
            "errors": [],
            "last_scanned_place_id": 2600,
        }

    monkeypatch.setattr(enrichment_only, "run_image_enrich", fake_run_image_enrich)

    result = enrichment_only._run_image_batches("large-city")

    assert calls == [0, 2500]
    assert result["batches"] == 2
    assert result["scanned_places"] == enrichment_only.IMAGE_BATCH_LIMIT + 5
    assert result["created"] == 5
    assert result["last_scanned_place_id"] == 2600


def test_image_batches_send_heartbeat_after_each_batch_new(monkeypatch):
    heartbeat_calls: list[tuple[int, int, int]] = []

    def fake_run_image_enrich(argv: list[str]) -> dict[str, object]:
        cursor = int(argv[argv.index("--start-after-id") + 1])
        if cursor == 0:
            return {
                "scanned_places": enrichment_only.IMAGE_BATCH_LIMIT,
                "candidates_found": 1,
                "created": 1,
                "auto_approved": 1,
                "place_image_url_synced": 1,
                "skipped_duplicates": 0,
                "skipped_has_approved": 0,
                "skipped_ineligible": 0,
                "skipped_no_source": enrichment_only.IMAGE_BATCH_LIMIT - 1,
                "errors": [],
                "last_scanned_place_id": 100,
            }
        return {
            "scanned_places": 1,
            "candidates_found": 0,
            "created": 0,
            "auto_approved": 0,
            "place_image_url_synced": 0,
            "skipped_duplicates": 0,
            "skipped_has_approved": 0,
            "skipped_ineligible": 0,
            "skipped_no_source": 1,
            "errors": [],
            "last_scanned_place_id": 101,
        }

    def heartbeat(totals: dict[str, object], batches: int) -> None:
        heartbeat_calls.append((batches, int(totals["scanned_places"]), int(totals["last_scanned_place_id"])))

    monkeypatch.setattr(enrichment_only, "run_image_enrich", fake_run_image_enrich)

    enrichment_only._run_image_batches("large-city", heartbeat=heartbeat)

    assert heartbeat_calls == [(1, enrichment_only.IMAGE_BATCH_LIMIT, 100), (2, enrichment_only.IMAGE_BATCH_LIMIT + 1, 101)]
