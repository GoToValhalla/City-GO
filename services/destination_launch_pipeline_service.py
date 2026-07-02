from __future__ import annotations


class DestinationLaunchTransitionError(ValueError):
    pass


class DestinationPublishGateError(ValueError):
    pass


class DestinationRouteReadyError(ValueError):
    pass


ALLOWED_DESTINATION_LAUNCH_TRANSITIONS: set[tuple[str, str]] = {
    ("created", "import_pending"),
    ("import_pending", "importing"),
    ("importing", "enrichment_pending"),
    ("enrichment_pending", "enriching"),
    ("enriching", "readiness_pending"),
    ("readiness_pending", "review_required"),
    ("review_required", "publishable"),
    ("publishable", "published"),
    ("published", "projections_pending"),
    ("projections_pending", "route_ready"),
    ("created", "failed"),
    ("import_pending", "failed"),
    ("importing", "failed"),
    ("enrichment_pending", "failed"),
    ("enriching", "failed"),
    ("readiness_pending", "failed"),
    ("review_required", "blocked"),
    ("publishable", "blocked"),
    ("failed", "import_pending"),
    ("blocked", "review_required"),
}


def assert_launch_transition_allowed(*, from_status: str, to_status: str) -> None:
    if (from_status, to_status) not in ALLOWED_DESTINATION_LAUNCH_TRANSITIONS:
        raise DestinationLaunchTransitionError(f"Destination launch transition is not allowed: {from_status} -> {to_status}")


def assert_destination_publishable(
    *,
    launch_status: str,
    readiness_score: float,
    is_publishable: bool,
    blocking_issues: dict[str, object] | None = None,
) -> None:
    if launch_status not in {"publishable", "published"}:
        raise DestinationPublishGateError(f"Destination is not in publishable state: {launch_status}")
    if not is_publishable:
        raise DestinationPublishGateError("Destination readiness summary is not publishable")
    if readiness_score < 70:
        raise DestinationPublishGateError("Destination readiness score is below publication threshold")
    if blocking_issues:
        raise DestinationPublishGateError("Destination has blocking readiness issues")


def assert_destination_route_ready(
    *,
    launch_status: str,
    is_published: bool,
    search_projection_ready: bool,
    routing_projection_ready: bool,
    route_eligible_places: int,
) -> None:
    if launch_status not in {"projections_pending", "route_ready"}:
        raise DestinationRouteReadyError(f"Destination cannot become route ready from state: {launch_status}")
    if not is_published:
        raise DestinationRouteReadyError("Destination must be published before route readiness")
    if not search_projection_ready:
        raise DestinationRouteReadyError("Search projection is not ready")
    if not routing_projection_ready:
        raise DestinationRouteReadyError("Routing projection is not ready")
    if route_eligible_places < 3:
        raise DestinationRouteReadyError("Destination needs at least 3 route eligible places")
