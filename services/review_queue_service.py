"""Review queue operations for problematic import fields."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.review_queue_item import ReviewQueueItem
from services.admin_audit_service import write_admin_audit_log

OPEN_STATUS = "open"
RESOLVED_STATUS = "resolved"
# ReviewQueueItem rows created by publication_policy.ensure_review_queue_item
# (field_name="publication") have no dedicated resolution handler that
# re-runs the publication decision -- resolving one of these through the
# generic endpoint must never claim the underlying publication state
# changed, since it did not.
PUBLICATION_FIELD_NAME = "publication"
DISPOSITION_ACKNOWLEDGED_NO_MUTATION = "acknowledged_no_publication_mutation"


class ResolveReviewResult:
    """Outcome of resolve_review_item. `item` is only meaningful when `ok`
    is True -- the freshly locked-and-reloaded row. `already_resolved` is
    True precisely when the item exists but was not in an allowed open
    state (a truthful "someone already decided this" signal), distinct
    from `ok=False, already_resolved=False` (the item does not exist)."""

    __slots__ = ("ok", "item", "already_resolved", "reason")

    def __init__(self, *, ok: bool, item: ReviewQueueItem | None, already_resolved: bool = False, reason: str | None = None):
        self.ok = ok
        self.item = item
        self.already_resolved = already_resolved
        self.reason = reason


class ReviewQueueJobLinkError(ValueError):
    """Raised before DB flush when review queue job_id points to the wrong table."""


def _valid_city_admin_import_job_id(db: Session, job_id: int | None) -> int | None:
    if job_id is None:
        return None
    if db.get(CityAdminImportJob, job_id) is not None:
        return job_id
    raise ReviewQueueJobLinkError(
        "Invalid review_queue_items.job_id: "
        f"city_admin_import_jobs.id={job_id} does not exist. "
        "Pass city_admin_import_job_id, not import_batch_id/enrichment_task_id/run_id."
    )


def safe_import_job_id(db: Session, job_id: int | None) -> tuple[int | None, dict[str, object] | None]:
    """Resolve import job link for review queue without risking FK violations."""
    if job_id is None:
        return None, None
    try:
        return _valid_city_admin_import_job_id(db, job_id), None
    except ReviewQueueJobLinkError as exc:
        return None, {
            "requested_job_id": job_id,
            "job_link_error": str(exc),
            "kind": "data_integrity",
        }


def ensure_review_item(
    db: Session,
    *,
    city_id: int,
    place_id: int,
    field_name: str,
    reason: str,
    job_id: int | None = None,
    severity: str = "medium",
    payload: dict[str, object] | None = None,
) -> ReviewQueueItem:
    """Create or update one active review issue without violating the open-item key.

    The database enforces one open/pending row per ``place_id + field_name +
    reason`` via the partial unique index ``uq_review_queue_items_open_identity``
    (migration a4c6e8f0b2d4). Import/enrichment stages may call this function
    repeatedly for the same issue, or may first create a generic field issue
    and later normalize it to a concrete reason. Always prefer the exact open
    item before mutating any other row; otherwise changing ``reason`` can
    collide with an already existing row.

    The initial SELECT-then-INSERT above is not itself race-safe (two
    concurrent producers can both see no matching row and both attempt an
    insert) -- the actual guarantee comes from attempting the insert inside a
    SAVEPOINT and recovering from the resulting IntegrityError by rolling
    back only that SAVEPOINT and re-selecting the row the winning concurrent
    writer actually created. The caller-owned outer transaction is left
    exactly as it was; this function never commits.

    The SAVEPOINT is opened on the raw Core Connection (``db.connection()
    .begin_nested()``), not via ``db.begin_nested()``: the ORM Session's own
    begin_nested() unconditionally flushes the session's entire pending unit
    of work before establishing the SAVEPOINT, which would prematurely
    persist unrelated in-flight ORM state the caller has not finished
    mutating yet (e.g. a Place mid-way through a field-restore sequence
    elsewhere in the same session). Executing a Core insert() directly on
    the connection avoids that flush, and avoids the ORM Session being
    marked "pending rollback" on the IntegrityError -- keeping the session
    fully usable afterward.

    The NestedTransaction is used as a context manager (``with connection
    .begin_nested(): ...``), not via manual ``.commit()``/``.rollback()``
    calls guarded only by ``except IntegrityError`` -- the context manager
    form guarantees the SAVEPOINT is rolled back on ANY exception raised
    inside the block and released (committed) only on success, so a
    non-IntegrityError failure (e.g. a dropped connection) can never leave
    the SAVEPOINT dangling neither committed nor rolled back.

    ``job_id`` is optional context only, but when provided it must reference
    ``city_admin_import_jobs.id``. This fails before flush so production gets a
    precise application error instead of a database FK crash.
    """
    item = _pending_item(db, place_id=place_id, field_name=field_name, reason=reason)
    item = item or _open_item(db, place_id=place_id, field_name=field_name, reason=reason)
    item = item or _pending_item(db, place_id=place_id, field_name=field_name, reason=None)
    item = item or _open_item(db, place_id=place_id, field_name=field_name, reason=None)
    safe_job_id = _valid_city_admin_import_job_id(db, job_id)
    next_payload = dict(payload or {})

    if item is not None:
        item.city_id = city_id
        item.reason = reason
        item.job_id = safe_job_id
        item.severity = severity
        item.payload = next_payload
        db.add(item)
        return item

    new_values = dict(
        city_id=city_id,
        place_id=place_id,
        field_name=field_name,
        reason=reason,
        job_id=safe_job_id,
        severity=severity,
        status="open",
        payload=next_payload,
    )
    connection = db.connection()
    new_id: int | None = None
    try:
        # NestedTransaction used as a context manager guarantees rollback
        # ("ROLLBACK TO SAVEPOINT") on ANY exception raised inside the
        # block, and commit ("RELEASE SAVEPOINT") on success -- unlike a
        # manual try/except IntegrityError with an explicit
        # savepoint.commit()/savepoint.rollback() call, this leaves no
        # window where a non-IntegrityError failure (a dropped
        # connection, an unrelated driver error) could leave the
        # SAVEPOINT neither committed nor rolled back.
        with connection.begin_nested():
            new_id = connection.execute(insert(ReviewQueueItem).values(**new_values)).inserted_primary_key[0]
    except IntegrityError:
        # A concurrent producer won the race on
        # uq_review_queue_items_open_identity between our SELECTs above and
        # this insert. The SAVEPOINT was already rolled back by the context
        # manager above -- every other pending change in the caller's
        # session survives untouched, and the ORM Session itself never saw
        # the failed flush, so it is never marked "pending rollback".
        winner = _open_item(db, place_id=place_id, field_name=field_name, reason=reason)
        winner = winner or _open_item(db, place_id=place_id, field_name=field_name, reason=None)
        if winner is None:
            # The conflicting row is no longer open/pending (e.g. resolved
            # between our insert attempt and this re-select) -- re-raise
            # rather than silently fabricate a row.
            raise
        return winner
    return db.query(ReviewQueueItem).filter(ReviewQueueItem.id == new_id).one()


def list_review_items(db: Session, *, city_slug: str | None = None, status: str = "open") -> list[ReviewQueueItem]:
    query = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == status)
    if city_slug:
        from models.city import City

        query = query.join(City, City.id == ReviewQueueItem.city_id).filter(City.slug == city_slug)
    return query.order_by(ReviewQueueItem.created_at.asc(), ReviewQueueItem.id.asc()).all()


def resolve_review_item(db: Session, item_id: int, *, actor: str, resolution: str) -> ResolveReviewResult:
    """Resolve one generic review-queue item, exactly once.

    Locks the row (SELECT ... FOR UPDATE + populate_existing) so two
    concurrent resolve requests for the same item cannot both apply --
    only the first to acquire the lock resolves it; the second observes
    the now-resolved row under the same lock and returns a truthful
    already_resolved=True conflict instead of silently overwriting
    resolved_by/resolved_at/resolution.

    This function performs no underlying entity mutation (unlike
    place_change_review_service, which also applies/restores Place
    fields): it must never claim otherwise. For field_name="publication"
    items specifically -- created by publication_policy.
    ensure_review_queue_item, which has no dedicated resolution handler
    that re-runs the publication decision -- the recorded resolution is
    explicitly tagged DISPOSITION_ACKNOWLEDGED_NO_MUTATION so the audit
    trail never implies publication state changed as a result of this
    call.

    Writes one AdminAuditLog row in the same transaction as the resolution
    itself. Never commits; the caller owns the transaction."""
    row = (
        db.query(ReviewQueueItem)
        .filter(ReviewQueueItem.id == item_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if row is None:
        return ResolveReviewResult(ok=False, item=None)
    if row.status != OPEN_STATUS:
        return ResolveReviewResult(ok=False, item=row, already_resolved=True, reason=f"already {row.status}")

    old_value = {"status": row.status, "resolved_by": row.resolved_by, "resolved_at": None, "resolution": row.resolution}
    recorded_resolution = resolution
    audit_new_value = {"status": RESOLVED_STATUS, "resolution": resolution}
    if row.field_name == PUBLICATION_FIELD_NAME:
        recorded_resolution = DISPOSITION_ACKNOWLEDGED_NO_MUTATION
        audit_new_value = {
            "status": RESOLVED_STATUS,
            "resolution": recorded_resolution,
            "requested_resolution": resolution,
            "publication_state_changed": False,
        }

    row.status = RESOLVED_STATUS
    row.resolved_by = actor
    row.resolved_at = datetime.utcnow()
    row.resolution = recorded_resolution
    db.add(row)
    write_admin_audit_log(
        db,
        actor=actor,
        action="resolve_review_item",
        entity_type="review_queue_item",
        entity_id=row.id,
        old_value=old_value,
        new_value=audit_new_value,
        reason=resolution,
    )
    return ResolveReviewResult(ok=True, item=row)


def _open_item(
    db: Session,
    *,
    place_id: int,
    field_name: str,
    reason: str | None,
) -> ReviewQueueItem | None:
    query = db.query(ReviewQueueItem).filter_by(place_id=place_id, field_name=field_name, status="open")
    if reason is not None:
        query = query.filter(ReviewQueueItem.reason == reason)
    return query.order_by(ReviewQueueItem.id.asc()).first()


def _pending_item(
    db: Session,
    *,
    place_id: int,
    field_name: str,
    reason: str | None,
) -> ReviewQueueItem | None:
    for pending in db.new:
        if (
            isinstance(pending, ReviewQueueItem)
            and pending.place_id == place_id
            and pending.field_name == field_name
            and pending.status in {None, "open"}
            and (reason is None or pending.reason == reason)
        ):
            return pending
    return None
