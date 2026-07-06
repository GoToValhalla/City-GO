"""Destination discovery orchestration."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationScope
from models.destination_discovery import DestinationDiscoveryCandidate, DestinationDiscoveryJob
from schemas.destination_discovery import (
    ConfidenceScore,
    DestinationDiscoveryCandidate as CandidateRead,
    DiscoverRegionRequest,
    DiscoverRegionResponse,
    DiscoveryOptions,
    DiscoveryWarning,
    ExistingDestinationMatch,
    GeoBbox,
    GeoPoint,
    JobDetailResponse,
    RecommendedScope,
    RegionCandidate,
    RegionDiscoveryJob,
    RegionDiscoveryPreview,
    ScopeOverlap,
    TierSummary,
)
from services.destination_discovery.providers import get_region, raw_candidates_for_region, search_regions as provider_search
from services.destination_discovery.ranking import score_candidate
from services.destination_discovery.scopes import recommend_scopes
from services.destination_discovery.slug import suggest_slug


def search_region_candidates(query: str, *, limit: int = 5) -> list[RegionCandidate]:
    return provider_search(query, limit=limit)


def start_discovery(db: Session, region_id: str, payload: DiscoverRegionRequest, *, actor_id: str | None) -> DiscoverRegionResponse:
    region = get_region(region_id)
    if region is None:
        raise ValueError("Region not found")
    job = DestinationDiscoveryJob(
        status="running",
        region_id=region_id,
        provider=payload.provider if payload.provider != "auto" else "deterministic",
        region_snapshot=region.model_dump(),
        options=payload.options.model_dump(),
        progress_percent=10,
        created_by=actor_id,
    )
    db.add(job)
    db.flush()
    try:
        preview = _build_preview(db, job, region, payload.options)
        job.status = "completed"
        job.progress_percent = 100
        job.result_summary = {
            "total_candidates": preview.total_candidates,
            "tiers": preview.tiers.model_dump(),
            "warnings": [w.model_dump() for w in preview.warnings],
        }
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
        job.progress_percent = 0
        db.commit()
        raise
    db.commit()
    db.refresh(job)
    return DiscoverRegionResponse(job=_job_read(job), preview=preview)


def get_job(db: Session, job_id: str) -> JobDetailResponse:
    job = db.query(DestinationDiscoveryJob).filter_by(id=job_id).first()
    if job is None:
        raise ValueError("Job not found")
    preview = _preview_from_job(db, job) if job.status == "completed" else None
    return JobDetailResponse(job=_job_read(job), preview=preview)


def list_job_candidates(db: Session, job_id: str) -> list[CandidateRead]:
    rows = db.query(DestinationDiscoveryCandidate).filter_by(job_id=job_id).order_by(DestinationDiscoveryCandidate.ranking_score.desc()).all()
    return [_candidate_read(row) for row in rows]


def get_candidate(db: Session, candidate_id: str) -> CandidateRead:
    row = db.query(DestinationDiscoveryCandidate).filter_by(id=candidate_id).first()
    if row is None:
        raise ValueError("Candidate not found")
    return _candidate_read(row)


def _build_preview(db: Session, job: DestinationDiscoveryJob, region: RegionCandidate, options: DiscoveryOptions) -> RegionDiscoveryPreview:
    raw_rows = raw_candidates_for_region(region.id)
    warnings = list(region.warnings)
    if not raw_rows:
        warnings.append(DiscoveryWarning(code="CATEGORY_DATA_UNKNOWN", severity="warning", message="Кандидаты для региона недоступны в текущем провайдере."))
    tiers = TierSummary()
    persisted: list[DestinationDiscoveryCandidate] = []
    for raw in raw_rows[: options.max_candidates]:
        if not options.include_towns and str(raw.get("type")) == "town":
            continue
        candidate_warnings = _raw_warnings(raw, options)
        slug = suggest_slug(str(raw.get("english_name") or raw.get("name")))
        existing = _existing_match(db, slug, str(raw.get("name")))
        existing_boost = 0.15 if existing else 0.0
        ranking, confidence, tier, reasons = score_candidate(raw, existing_boost=existing_boost)
        overlaps = _scope_overlaps(db, raw)
        scopes = recommend_scopes(raw, include_buffer=options.include_border_candidates)
        row = DestinationDiscoveryCandidate(
            job_id=job.id,
            external_id=str(raw["external_id"]),
            provider=region.provider,
            name=str(raw["name"]),
            native_name=str(raw.get("name")),
            english_name=str(raw.get("english_name")) if raw.get("english_name") else None,
            destination_type=str(raw.get("type") or "city"),
            parent_region=region.name,
            center_lat=float(raw["lat"]) if raw.get("lat") is not None else None,
            center_lng=float(raw["lon"]) if raw.get("lon") is not None else None,
            bbox_json=raw.get("bbox"),
            population=int(raw["population"]) if raw.get("population") else None,
            confidence_json=confidence.model_dump(),
            ranking_score=ranking,
            tier=tier,
            warnings_json=[w.model_dump() for w in candidate_warnings],
            existing_match_json=existing.model_dump() if existing else None,
            scope_overlaps_json=[o.model_dump() for o in overlaps],
            recommended_scopes_json=[s.model_dump() for s in scopes],
            reasons_json=reasons,
            created_destination_slug=existing.slug if existing else None,
        )
        db.add(row)
        persisted.append(row)
        _inc_tier(tiers, tier)
    db.flush()
    return RegionDiscoveryPreview(region=region, total_candidates=len(persisted), tiers=tiers, warnings=warnings, candidates=[_candidate_read(r) for r in persisted])


def _preview_from_job(db: Session, job: DestinationDiscoveryJob) -> RegionDiscoveryPreview:
    region = RegionCandidate.model_validate(job.region_snapshot or {})
    summary = job.result_summary or {}
    tiers = TierSummary.model_validate(summary.get("tiers") or {})
    warnings = [DiscoveryWarning.model_validate(w) for w in summary.get("warnings") or []]
    candidates = list_job_candidates(db, job.id)
    return RegionDiscoveryPreview(region=region, total_candidates=len(candidates), tiers=tiers, warnings=warnings, candidates=candidates)


def _raw_warnings(raw: dict[str, object], options: DiscoveryOptions) -> list[DiscoveryWarning]:
    warnings: list[DiscoveryWarning] = []
    if raw.get("border"):
        warnings.append(DiscoveryWarning(code="BORDER_BUFFER_RISK", severity="warning", message="Приграничный населённый пункт."))
    if raw.get("poi_unknown") or not options.include_poi_signals:
        warnings.append(DiscoveryWarning(code="POI_SIGNAL_UNAVAILABLE", severity="info", message="POI-сигнал недоступен — оценка без категорий."))
        warnings.append(DiscoveryWarning(code="CATEGORY_DATA_UNKNOWN", severity="warning", message="Распределение категорий неизвестно."))
    if raw.get("bbox") is None:
        warnings.append(DiscoveryWarning(code="BOUNDARY_MISSING", severity="critical", message="Границы неполные."))
    return warnings


def _existing_match(db: Session, slug: str, name: str) -> ExistingDestinationMatch | None:
    row = db.query(Destination).filter(Destination.slug == slug).first()
    if row is None:
        row = db.query(Destination).filter(Destination.name.ilike(name)).first()
    if row is None:
        return None
    return ExistingDestinationMatch(destination_id=row.id, slug=row.slug, name=row.name, match_type="slug_or_name", confidence=0.9)


def _scope_overlaps(db: Session, raw: dict[str, object]) -> list[ScopeOverlap]:
    bbox = raw.get("bbox")
    if not isinstance(bbox, dict):
        return []
    overlaps: list[ScopeOverlap] = []
    for scope in db.query(DestinationScope).limit(200).all():
        sb = scope.bbox
        if isinstance(sb, dict) and _bbox_intersects(bbox, sb):
            dest = db.query(Destination).filter_by(id=scope.destination_id).first()
            if dest:
                overlaps.append(ScopeOverlap(destination_slug=dest.slug, scope_code=scope.code, scope_name=scope.name, overlap_type="bbox_intersection", message="Пересечение bbox с существующим контуром"))
    return overlaps[:5]


def _bbox_intersects(a: dict[str, object], b: dict[str, object]) -> bool:
    try:
        return float(a["south"]) <= float(b["north"]) and float(a["north"]) >= float(b["south"]) and float(a["west"]) <= float(b["east"]) and float(a["east"]) >= float(b["west"])
    except (KeyError, TypeError, ValueError):
        return False


def _inc_tier(tiers: TierSummary, tier: str) -> None:
    setattr(tiers, tier, getattr(tiers, tier) + 1)


def _job_read(job: DestinationDiscoveryJob) -> RegionDiscoveryJob:
    return RegionDiscoveryJob(id=job.id, status=job.status, progress_percent=job.progress_percent, error=job.error)


def _candidate_read(row: DestinationDiscoveryCandidate) -> CandidateRead:
    center = GeoPoint(lat=row.center_lat, lon=row.center_lng) if row.center_lat is not None and row.center_lng is not None else None
    bbox = GeoBbox.model_validate(row.bbox_json) if isinstance(row.bbox_json, dict) else None
    return CandidateRead(
        id=row.id,
        external_id=row.external_id,
        provider=row.provider,
        name=row.name,
        native_name=row.native_name,
        english_name=row.english_name,
        type=row.destination_type,
        parent_region=row.parent_region,
        center=center,
        bbox=bbox,
        population=row.population,
        confidence=ConfidenceScore.model_validate(row.confidence_json or {}),
        ranking_score=row.ranking_score,
        tier=row.tier,
        reasons=list(row.reasons_json or []),
        warnings=[DiscoveryWarning.model_validate(w) for w in (row.warnings_json or [])],
        existing_match=ExistingDestinationMatch.model_validate(row.existing_match_json) if row.existing_match_json else None,
        scope_overlaps=[ScopeOverlap.model_validate(o) for o in (row.scope_overlaps_json or [])],
        recommended_scopes=[RecommendedScope.model_validate(s) for s in (row.recommended_scopes_json or [])],
        created_destination_slug=row.created_destination_slug,
    )
