from sqlalchemy.orm import Session

from services.context_merge_service import ContextMergeService, RequestContext
from services.resilient_candidate_retrieval_service import ResilientCandidateRetrievalService
from services.hard_filters_service import HardFiltersService
from services.scoring_service import ScoringService
from services.route_assembly_service import RouteAssemblyService
from services.route_time_ordering_service import RouteTimeOrderingService
from services.time_aware_service import TimeAwareService
from services.route_budget_fit_service import RouteBudgetFitService
from services.route_finalize_service import RouteFinalizeService
from services.route_builder_flow import build_dynamic_route
from schemas.user_profile import UserProfile


class RouteBuilderService:
    def __init__(self):
        self.context_merge = ContextMergeService()
        self.retrieval = ResilientCandidateRetrievalService()
        self.filters = HardFiltersService()
        self.scoring = ScoringService()
        self.assembly = RouteAssemblyService()
        self.time_ordering = RouteTimeOrderingService()
        self.time = TimeAwareService()
        self.budget_fit = RouteBudgetFitService()
        self.finalize = RouteFinalizeService()

    def build_route(
        self,
        db: Session,
        request: RequestContext,
        profile: UserProfile | None = None,
    ):
        return build_dynamic_route(self, db, request, profile)
