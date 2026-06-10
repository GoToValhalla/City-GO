from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.place_import_event import PlaceImportEvent
from schemas.place_seed_import_summary import PlaceSeedImportSummary
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_import_log_service import place_import_summary, record_place_import


def _db():
    engine = create_engine("sqlite:///:memory:")
    PlaceImportEvent.__table__.create(bind=engine)
    return sessionmaker(bind=engine)()


def _item() -> PlaceSeedItem:
    return PlaceSeedItem(
        title="Coffee",
        slug="coffee",
        city_slug="zelenogradsk",
        category="coffee",
        taxonomy=PlaceTaxonomyPayload(category="coffee"),
        lat=54.96,
        lng=20.48,
    )


def test_record_place_import_persists_summary() -> None:
    db = _db()
    summary = PlaceSeedImportSummary(total=1, created=1, updated=0, skipped=0, invalid=0, errors=[])
    saved = record_place_import(db, [_item()], summary, dry_run=True, source="test")
    event = db.query(PlaceImportEvent).one()
    assert saved is True
    assert event.created == 1
    assert event.city_slugs == ["zelenogradsk"]


def test_place_import_summary_aggregates_events() -> None:
    db = _db()
    summary = PlaceSeedImportSummary(total=1, created=1, updated=0, skipped=0, invalid=0, errors=[])
    record_place_import(db, [_item()], summary, dry_run=True)
    data = place_import_summary(db)
    assert data["total_imports"] == 1
    assert data["total_created"] == 1
    assert data["dry_run_count"] == 1
