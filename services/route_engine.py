from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from schemas.user_profile import UserProfile
from services.context_merge_service import RequestContext
from services.route_builder_flow import build_dynamic_route


@dataclass(frozen=True)
class RouteExecutionRequest:
    """Runtime input passed from the orchestrator to a concrete route strategy."""

    db: Session
    request: RequestContext
    profile: UserProfile | None = None


class RouteStrategy(Protocol):
    """Contract for route build modes such as instant, planned, and recompute."""

    mode: str

    def build(self, deps: object, execution: RouteExecutionRequest) -> object:
        """Build a route using shared pipeline dependencies."""


class InstantRouteStrategy:
    """Current production route build strategy.

    It intentionally delegates to the existing dynamic route pipeline. This keeps the public
    `/v1/user-routes/build` behavior stable while giving us a clean extension point for
    planned and recompute strategies.
    """

    mode = "instant"

    def build(self, deps: object, execution: RouteExecutionRequest) -> object:
        return build_dynamic_route(
            deps=deps,
            db=execution.db,
            request=execution.request,
            profile=execution.profile,
        )


class RouteStrategySelector:
    """Selects a route strategy from the request context.

    Only the instant strategy is active today. Planned/recompute modes should be added here
    after their request contracts and session model are introduced.
    """

    def __init__(self, instant: RouteStrategy | None = None) -> None:
        self.instant = instant or InstantRouteStrategy()

    def select(self, request: RequestContext) -> RouteStrategy:
        return self.instant


class RouteEngine:
    """Small orchestration layer for route strategy execution."""

    def __init__(self, selector: RouteStrategySelector | None = None) -> None:
        self.selector = selector or RouteStrategySelector()

    def build(
        self,
        deps: object,
        db: Session,
        request: RequestContext,
        profile: UserProfile | None = None,
    ) -> object:
        strategy = self.selector.select(request)
        return strategy.build(deps, RouteExecutionRequest(db=db, request=request, profile=profile))
