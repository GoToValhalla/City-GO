"""Authoritative Stage 5 source queries."""

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.place_published_snapshot import PublishedPlaceSnapshot


def latest_published_snapshots(
    db: Session, *, city_id: int | None
) -> list[PublishedPlaceSnapshot]:
    latest = db.query(
        PublishedPlaceSnapshot.place_id,
        func.max(PublishedPlaceSnapshot.snapshot_version).label("version"),
    ).filter(PublishedPlaceSnapshot.is_public.is_(True))
    if city_id is not None:
        latest = latest.filter(PublishedPlaceSnapshot.city_id == city_id)
    versions = latest.group_by(PublishedPlaceSnapshot.place_id).subquery()
    query = db.query(PublishedPlaceSnapshot).join(
        versions,
        and_(
            PublishedPlaceSnapshot.place_id == versions.c.place_id,
            PublishedPlaceSnapshot.snapshot_version == versions.c.version,
        ),
    )
    return list(query.order_by(PublishedPlaceSnapshot.place_id.asc()).all())


def source_version(rows: list[PublishedPlaceSnapshot]) -> int | None:
    return max((int(row.snapshot_version) for row in rows), default=None)
