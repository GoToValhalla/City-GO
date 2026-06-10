from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.candidate_retrieval_service import CandidateRetrievalService


def test_get_candidates_new_expands_radius_when_few_results_new() -> None:
    service = CandidateRetrievalService()
    db = MagicMock()
    ctx = SimpleNamespace(city_id="khanty-mansiysk")
    expanded_places = [SimpleNamespace(id=1, category="restaurant")]

    with patch.object(service, "_query_places", return_value=[]) as query_places, patch.object(
        service,
        "_fallback_expand_radius",
        return_value=expanded_places,
    ) as expand_radius, patch(
        "services.candidate_retrieval_service.attach_public_images",
        side_effect=lambda _db, places: places,
    ), patch(
        "services.candidate_retrieval_service.balance_candidates_by_category",
        side_effect=lambda places, _limit: places,
    ):
        result = service.get_candidates(db, ctx)

    assert result == expanded_places
    query_places.assert_called_once_with(db, ctx)
    expand_radius.assert_called_once_with(db, ctx)


def test_get_candidates_new_skips_radius_expand_when_enough_results_new() -> None:
    service = CandidateRetrievalService()
    db = MagicMock()
    ctx = SimpleNamespace(city_id=None)
    enough = [SimpleNamespace(id=index, category="restaurant") for index in range(20)]

    with patch.object(service, "_query_places", return_value=enough) as query_places, patch.object(
        service,
        "_fallback_expand_radius",
        return_value=[],
    ) as expand_radius, patch(
        "services.candidate_retrieval_service.attach_public_images",
        side_effect=lambda _db, places: places,
    ), patch(
        "services.candidate_retrieval_service.balance_candidates_by_category",
        side_effect=lambda places, _limit: places,
    ):
        result = service.get_candidates(db, ctx)

    assert result == enough
    query_places.assert_called_once_with(db, ctx)
    expand_radius.assert_not_called()
