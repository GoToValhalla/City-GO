from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.place_import_event import PlaceImportEvent
from schemas.place_seed_import_summary import PlaceSeedImportSummary
from schemas.place_seed_item import PlaceSeedItem


def record_place_import(
    db: Session,
    items: list[PlaceSeedItem],
    summary: PlaceSeedImportSummary,
    *,
    dry_run: bool,
    source: str | None = None,
) -> bool:
    try:
        db.add(_event(items, summary, dry_run, source))
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        return False


def place_import_summary(db: Session) -> dict[str, object]:
    events = db.query(PlaceImportEvent).all()
    return {
        "total_imports": len(events),
        "total_created": _sum(events, "created"),
        "total_updated": _sum(events, "updated"),
        "total_invalid": _sum(events, "invalid"),
        "dry_run_count": _count(events, lambda event: bool(event.dry_run)),
        "last_import_at": events[-1].created_at.isoformat() if events else None,
    }


def _event(
    items: list[PlaceSeedItem],
    summary: PlaceSeedImportSummary,
    dry_run: bool,
    source: str | None,
) -> PlaceImportEvent:
    return PlaceImportEvent(
        dry_run=dry_run,
        total=summary.total,
        created=summary.created,
        updated=summary.updated,
        skipped=summary.skipped,
        invalid=summary.invalid,
        city_slugs=_city_slugs(items),
        errors=list(summary.errors),
        source=source,
    )


def _city_slugs(items: list[PlaceSeedItem]) -> list[str]:
    return sorted({item.city_slug for item in items if item.city_slug})


def _sum(events: list[PlaceImportEvent], field: str) -> int:
    return sum(map(lambda event: int(getattr(event, field, 0) or 0), events))


def _count(events: list[PlaceImportEvent], predicate: Callable[[PlaceImportEvent], bool]) -> int:
    return sum(map(lambda event: 1 if predicate(event) else 0, events))
