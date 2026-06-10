from __future__ import annotations

from datetime import datetime

from models.place import Place
from schemas.user_route import UserRouteIntent, UserRouteState
from services.context_merge_service import ContextMergeService
from services.route_assembly_service import RoutePoint
from services.route_budget_fit_service import RouteBudgetFitService
from services.route_finalize_service import RouteFinalizeService
from services.place_runtime_defaults import effective_opening_hours, effective_visit_duration
from services.time_aware_service import TimeAwareService
from services.user_route_context import to_request_context
from services.user_route_mapper import final_route_to_state

_UPDATED_WARNING = "Маршрут скорректирован по вашему действию."


class UserRouteRecalcService:
    def recalc(
        self,
        places: list[Place],
        intent: UserRouteIntent,
        revision: int,
        extra_warnings: list[str] | None = None,
    ) -> UserRouteState:
        ctx = ContextMergeService().merge(to_request_context(intent), profile=None)
        route = TimeAwareService().apply(_to_points(places), ctx, datetime.utcnow())
        budget_fit = RouteBudgetFitService().fit(route, ctx)
        warnings = [*_default_warning(places), *(extra_warnings or []), *budget_fit.warnings]
        final = RouteFinalizeService().finalize(budget_fit.route, ctx, extra_warnings=warnings)
        status = "empty" if not final.points else "corrected"
        return final_route_to_state(final, intent, revision=revision, status=status)


def _to_points(places: list[Place]) -> list[RoutePoint]:
    return [_to_point(place) for place in places]


def _to_point(place: Place) -> RoutePoint:
    return RoutePoint(
        place_id=str(place.id),
        title=getattr(place, "title", None),
        address=getattr(place, "address", None),
        image_url=getattr(place, "image_url", None),
        short_description=getattr(place, "short_description", None),
        source=getattr(place, "source", None),
        lat=float(place.lat),
        lng=float(place.lng),
        score=0.0,
        category=str(getattr(place, "category", "") or ""),
        visit_minutes=effective_visit_duration(place),
        opening_hours=effective_opening_hours(place),
    )


def _default_warning(places: list[Place]) -> list[str]:
    return [_UPDATED_WARNING] if places else ["В маршруте не осталось точек."]
