from services.explainability_text import point_phrase, warning_phrase
from services.route_finalize_service import FinalRoute
from services.route_explanation_reasons import data_notes, point_reason, score_components


class ExplainabilityService:
    def build_route_summary(self, route: FinalRoute) -> str:
        if not route.points:
            return "Маршрут не найден."

        total_places = route.total_places
        total_distance = route.estimated_distance
        duration_minutes = self._summary_duration_minutes(route)
        warning_count = int(getattr(route, "warning_count", 0) or 0)
        point_warning_count = len(getattr(route, "places_with_warnings", []) or [])

        stem = f"Маршрут на {point_phrase(total_places)}"

        if warning_count == 0:
            return f"{stem}, примерно {duration_minutes} мин и {total_distance} км."

        return (
            f"{stem} (~{duration_minutes} мин, {total_distance} км). "
            f"{warning_phrase(point_warning_count, warning_count)}"
        )

    def _summary_duration_minutes(self, route: FinalRoute) -> int:
        te = getattr(route, "total_estimated_minutes", None)
        if te is not None and int(te) > 0:
            return int(te)
        return int(route.total_minutes)

    def build_point_reason(self, point) -> str:
        reason, _match_type = point_reason(point)
        if reason:
            return reason
        category = getattr(point, "category", None)

        if category == "cafe":
            return "Подходит как остановка для кофе или короткого отдыха."

        if category == "restaurant":
            return "Подходит как остановка для еды."

        if category == "museum":
            return "Добавлено как культурная точка маршрута."

        if category == "park":
            return "Добавлено как спокойная прогулочная точка."

        if category == "walk":
            return "Добавлено как часть прогулочного сценария."

        return "Подходит под общий сценарий маршрута."

    def build_point_warning(self, point) -> str | None:
        tw = getattr(point, "time_warning", None)
        if tw:
            return tw

        hours_status = getattr(point, "hours_status", None)

        if hours_status == "closed":
            return "Место может быть закрыто к моменту визита."

        if hours_status == "closes_soon":
            return "Место может скоро закрыться."

        if hours_status == "unknown":
            return "Часы работы не удалось проверить."

        return None

    def build_route_explanation(self, route: FinalRoute) -> dict[str, object]:
        warnings = list(getattr(route, "warnings", []) or [])
        notes = data_notes(route)
        return {
            "route_id": route.route_id,
            "summary": self.build_route_summary(route),
            "has_warnings": bool(getattr(route, "has_warnings", False)),
            "warning_count": int(getattr(route, "warning_count", 0) or 0),
            "quality_score": float(getattr(route, "quality_score", 0.0) or 0.0),
            "quality_breakdown": dict(getattr(route, "quality_breakdown", {}) or {}),
            "warnings": warnings,
            "data_limitations": notes,
            "data_notes": notes,
            "points": [self._point_payload(point) for point in route.points],
        }

    def _point_payload(self, point: object) -> dict[str, object]:
        reason, match_type = point_reason(point)
        return {
            "place_id": point.place_id,
            "reason": reason,
            "match_type": match_type,
            "score_components": score_components(point),
            "warning": self.build_point_warning(point),
            "time_status": getattr(point, "time_status", None),
        }
