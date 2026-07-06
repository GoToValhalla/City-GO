"""Bulk create destinations from discovery candidates."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationScope
from models.destination_discovery import DestinationDiscoveryCandidate
from schemas.destination_discovery import (
    BulkCreateOptions,
    BulkCreateRequest,
    BulkCreateResult,
    CandidateCreateResult,
    DiscoveryWarning,
    RecommendedScope,
)
from services.admin_audit_service import write_admin_audit_log
from services.destination_discovery.slug import suggest_slug
from services.destination_service import create_destination


def bulk_create_from_job(db: Session, job_id: str, payload: BulkCreateRequest, *, actor_id: str) -> BulkCreateResult:
    warnings: list[DiscoveryWarning] = []
    if payload.options.queue_import:
        warnings.append(DiscoveryWarning(code="QUEUE_IMPORT_UNSUPPORTED", severity="info", message="Очередь импорта не запускается автоматически."))
    items: list[CandidateCreateResult] = []
    created = skipped = conflicts = errors = 0
    for candidate_id in payload.candidate_ids:
        result = _create_one(db, job_id, candidate_id, payload.options, actor_id=actor_id)
        items.append(result)
        if result.status == "created":
            created += 1
        elif result.status == "skipped_existing":
            skipped += 1
        elif result.status == "conflict":
            conflicts += 1
        else:
            errors += 1
    db.commit()
    write_admin_audit_log(
        db,
        actor=actor_id,
        action="destination_discovery_bulk_create",
        entity_type="destination_discovery_job",
        entity_id=None,
        new_value={"job_id": job_id, "created": created, "skipped": skipped, "conflicts": conflicts, "errors": errors},
    )
    db.commit()
    return BulkCreateResult(
        total_requested=len(payload.candidate_ids),
        created=created,
        skipped_existing=skipped,
        conflicts=conflicts,
        errors=errors,
        items=items,
        warnings=warnings,
    )


def _create_one(db: Session, job_id: str, candidate_id: str, options: BulkCreateOptions, *, actor_id: str) -> CandidateCreateResult:
    row = db.query(DestinationDiscoveryCandidate).filter_by(id=candidate_id, job_id=job_id).first()
    if row is None:
        return CandidateCreateResult(candidate_id=candidate_id, status="error", message="Candidate not found")
    slug = suggest_slug(row.english_name or row.name)
    existing = db.query(Destination).filter(Destination.slug == slug).first()
    if existing is not None:
        row.created_destination_slug = existing.slug
        if options.update_existing_scopes and options.create_default_scopes:
            created_scopes = _create_scopes(db, existing, row, options)
            if created_scopes:
                return CandidateCreateResult(
                    candidate_id=candidate_id,
                    destination_slug=existing.slug,
                    status="created",
                    message="Scopes updated on existing destination.",
                    created_scopes=created_scopes,
                )
        return CandidateCreateResult(candidate_id=candidate_id, destination_slug=existing.slug, status="skipped_existing", message="Destination already exists.")
    if row.created_destination_slug:
        dest = db.query(Destination).filter_by(slug=row.created_destination_slug).first()
        if dest is not None:
            return CandidateCreateResult(candidate_id=candidate_id, destination_slug=dest.slug, status="skipped_existing", message="Already created from this job.")
    try:
        dest = create_destination(
            db,
            {
                "slug": slug,
                "name": row.name,
                "destination_type": _map_type(row.destination_type),
                "center_lat": row.center_lat,
                "center_lng": row.center_lng,
                "bbox": row.bbox_json,
            },
        )
        created_scopes: list[str] = []
        if options.create_default_scopes:
            created_scopes = _create_scopes(db, dest, row, options)
        row.created_destination_slug = dest.slug
        write_admin_audit_log(db, actor=actor_id, action="destination_created_from_discovery", entity_type="destination", entity_id=dest.id, new_value={"slug": slug, "candidate_id": candidate_id})
        return CandidateCreateResult(candidate_id=candidate_id, destination_slug=slug, status="created", message="Destination created.", created_scopes=created_scopes)
    except Exception as exc:  # noqa: BLE001
        return CandidateCreateResult(candidate_id=candidate_id, status="error", message=str(exc))


def _create_scopes(db: Session, dest: Destination, row: DestinationDiscoveryCandidate, options: BulkCreateOptions) -> list[str]:
    scopes_data = row.recommended_scopes_json or []
    created: list[str] = []
    for raw in scopes_data:
        scope = RecommendedScope.model_validate(raw)
        if scope.code == "border_buffer" and not options.include_boundary_buffer_scope:
            continue
        existing = db.query(DestinationScope).filter_by(destination_id=dest.id, code=scope.code).first()
        if existing is not None:
            if options.update_existing_scopes:
                existing.name = scope.name
                existing.bbox = scope.bbox.model_dump() if scope.bbox else existing.bbox
                existing.import_profile = scope.import_profile
                created.append(scope.code)
            continue
        db.add(
            DestinationScope(
                destination_id=dest.id,
                code=scope.code,
                name=scope.name,
                scope_type=scope.scope_type,
                import_strategy="single_bbox" if scope.bbox else "center_radius",
                bbox=scope.bbox.model_dump() if scope.bbox else None,
                import_profile=scope.import_profile,
                priority=scope.priority,
                enabled=True,
            ),
        )
        created.append(scope.code)
    return created


def _map_type(value: str) -> str:
    if value in {"city", "region", "natural_region", "national_park", "tourist_cluster", "route_corridor", "remote_area"}:
        return value
    return "city" if value in {"town", "village", "resort"} else "tourist_cluster"
