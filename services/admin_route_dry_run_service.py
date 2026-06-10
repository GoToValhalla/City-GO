"""Admin dry-run генерации маршрута."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.route_generation_candidate import RouteGenerationCandidate
from models.route_generation_run import RouteGenerationRun
from schemas.admin_route_dry_run import (
    AdminRouteDryRunCandidate,
    AdminRouteDryRunCounts,
    AdminRouteDryRunRequest,
    AdminRouteDryRunResponse,
)
from services.context_merge_service import RequestContext
from services.route_builder_service import RouteBuilderService
from services.route_generation_logging import log_admin_dry_run, log_route_generation_started


class AdminRouteDryRunService:
    def run(self, db: Session, *, request: AdminRouteDryRunRequest, actor_id: str) -> AdminRouteDryRunResponse:
        city = db.query(City).filter(City.slug == request.city_slug).first()
        if city is None:
            raise HTTPException(status_code=404, detail="Город не найден")
        lat, lng = self._resolve_start(city, request)
        route_request = RequestContext(
            location=(lat, lng),
            city_id=city.slug,
            time_budget_minutes=request.duration_min,
            interests=request.interests,
            budget_level=request.budget_level,
        )
        payload = {"source": "admin_dry_run", "actor_id": actor_id, **request.model_dump()}
        log_route_generation_started(db, source="admin_dry_run", city_slug=city.slug, payload=payload)
        final = RouteBuilderService().build_route(db=db, request=route_request, profile=None)
        run_id = getattr(final, "generation_run_id", None)
        if run_id is None:
            raise HTTPException(status_code=500, detail="Не удалось сохранить диагностику")
        run = db.query(RouteGenerationRun).filter(RouteGenerationRun.id == run_id).first()
        if run is None:
            raise HTTPException(status_code=404, detail="generation run не найден")
        selected, rejected = self._split_candidates(db, list(run.candidates), request.limit)
        success = len(selected) > 0
        log_admin_dry_run(
            db, success=success, city_slug=city.slug, actor_id=actor_id,
            generation_run_id=run_id, reason=None if success else "no_selected_places",
        )
        return AdminRouteDryRunResponse(
            request_summary=payload,
            generation_run_id=run_id,
            selected_places=selected,
            rejected_candidates=rejected,
            counts=AdminRouteDryRunCounts(
                total_candidates=run.total_candidates,
                eligible_candidates=run.eligible_candidates,
                rejected_candidates=run.total_candidates - run.eligible_candidates,
                selected_places=run.selected_places,
            ),
            quality=self._quality_payload(final),
        )

    def _resolve_start(self, city: City, request: AdminRouteDryRunRequest) -> tuple[float, float]:
        if request.start_lat is not None and request.start_lng is not None:
            return request.start_lat, request.start_lng
        if city.center_lat is not None and city.center_lng is not None:
            return city.center_lat, city.center_lng
        raise HTTPException(status_code=422, detail="Укажите start_lat/start_lng или задайте центр города")

    def _split_candidates(
        self,
        db: Session,
        candidates: list[RouteGenerationCandidate],
        limit: int | None,
    ) -> tuple[list[AdminRouteDryRunCandidate], list[AdminRouteDryRunCandidate]]:
        place_map = self._place_map(db, [c.place_id for c in candidates])
        rows = [self._to_row(candidate, place_map.get(candidate.place_id)) for candidate in candidates]
        selected = [row for row in rows if row.selected]
        rejected = [row for row in rows if not row.selected or not row.is_eligible]
        if limit is not None:
            selected = selected[:limit]
            rejected = rejected[:limit]
        return selected, rejected

    def _place_map(self, db: Session, place_ids: list[int]) -> dict[int, Place]:
        if not place_ids:
            return {}
        places = db.query(Place).filter(Place.id.in_(place_ids)).all()
        return {place.id: place for place in places}

    def _to_row(self, candidate: RouteGenerationCandidate, place: Place | None) -> AdminRouteDryRunCandidate:
        return AdminRouteDryRunCandidate(
            place_id=candidate.place_id,
            title=place.title if place else None,
            category=place.category if place else None,
            lat=place.lat if place else None,
            lng=place.lng if place else None,
            is_eligible=candidate.is_eligible,
            selected=candidate.selected,
            score=candidate.score,
            rejection_reasons=list(candidate.rejection_reasons or []),
            selection_reasons=list(candidate.selection_reasons or []),
        )

    def _quality_payload(self, final: object) -> dict[str, object]:
        score = float(getattr(final, "quality_score", 0.0) or 0.0)
        breakdown = dict(getattr(final, "quality_breakdown", {}) or {})
        status = str(getattr(final, "quality_status", None) or breakdown.get("status") or "weak")
        warnings = list(getattr(final, "warnings", []) or [])
        return {
            "status": status,
            "score": score,
            "score_percent": int(round(score * 100)),
            "warnings": warnings,
            "breakdown": breakdown,
            "route_status": str(getattr(final, "status", "")),
            "partial_reason": getattr(final, "partial_reason", None),
        }
