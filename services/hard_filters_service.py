from datetime import datetime

from models.place import Place
from schemas.merged_context import MergedContext
from services.itinerary_time_service import is_place_open_at_time
from services.place_runtime_defaults import effective_opening_hours
from services.route_filter_policy import FilterReport, filter_places
from services.route_start_time import effective_route_start
from services.route_timezone import ensure_local_datetime, local_now


class HardFiltersService:
    """Hard filters before scoring; fallback relaxes only budget, never safety."""

    MIN_POOL_SIZE = 15

    def apply(self, places: list[Place], ctx: MergedContext, now: datetime) -> list[Place]:
        return list(self.apply_with_report(places, ctx, now).kept)

    def apply_with_report(
        self,
        places: list[Place],
        ctx: MergedContext,
        now: datetime,
    ) -> FilterReport:
        route_now = self._route_now(ctx, now)
        return filter_places(
            list(places),
            ctx,
            route_now,
            self.MIN_POOL_SIZE,
            lambda place, dt: self._check_open_now(place, dt),
        )

    def _route_now(self, ctx: MergedContext, now: datetime) -> datetime:
        if getattr(ctx, "time_of_day", None):
            return effective_route_start(local_now(ctx), getattr(ctx, "time_of_day", None))
        return ensure_local_datetime(now, ctx)

    def _check_open_now(self, place: Place, now: datetime) -> str:
        """Return open/closed/unknown using the shared opening-hours parser."""

        open_state = is_place_open_at(place, now)

        if open_state is True:
            return "open"

        if open_state is False:
            return "closed"

        return "unknown"


def is_place_open_at(place: Place, dt: datetime) -> bool | None:
    return is_place_open_at_time(effective_opening_hours(place), dt)