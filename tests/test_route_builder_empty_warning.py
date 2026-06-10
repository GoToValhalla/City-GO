from unittest.mock import MagicMock, patch

from services.candidate_retrieval_service import CandidateRetrievalService
from services.context_merge_service import RequestContext
from services.route_builder_service import RouteBuilderService


def _empty_candidates(self, db, ctx):  # noqa: ARG002
    return []


def test_empty_candidate_pool_returns_warning() -> None:
    with patch.object(CandidateRetrievalService, "get_candidates", _empty_candidates):
        result = RouteBuilderService().build_route(
            db=MagicMock(),
            request=RequestContext(
                location=(54.96, 20.48),
                time_budget_minutes=120,
            ),
            profile=None,
        )

    assert result.points == []
    assert result.has_warnings is True
    assert "Не нашли мест рядом" in result.warnings[0]
