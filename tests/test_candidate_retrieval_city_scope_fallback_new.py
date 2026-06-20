from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.candidate_retrieval_service import CandidateRetrievalService


def test_get_candidates_new_expands_radius_when_few_results_new() -> None:
    service = CandidateRetrievalService()
    db = MagicMock()
    ctx = SimpleNamespace(city_id="khanty-mansiysk", location=(55.0, 20.0))
    expanded_places = [SimpleNamespace(id=1, category="restaurant", lat=55.0, lng=20.0)]

    with patch.object(service, "_safe_spatial_density", return_value={"city_wide_eligible": None}), patch.object(
        service, "_query_places", return_value=[]
    ) as query_places, patch.object(
        service,
        "_fallback_expand_radius",
        return_value=expanded_places,
    ) as expand_radius, patch.object(
        service,
        "_fallback_city_wide",
        return_value=[],
    ) as city_wide, patch(
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
    city_wide.assert_called_once_with(db, ctx)


def test_get_candidates_new_skips_radius_expand_when_enough_results_new() -> None:
    service = CandidateRetrievalService()
    db = MagicMock()
    ctx = SimpleNamespace(city_id=None, location=(55.0, 20.0))
    enough = [SimpleNamespace(id=index, category="restaurant", lat=55.0, lng=20.0) for index in range(40)]

    with patch.object(service, "_safe_spatial_density", return_value={"city_wide_eligible": None}), patch.object(
        service, "_query_places", return_value=enough
    ) as query_places, patch.object(
        service,
        "_fallback_expand_radius",
        return_value=[],
    ) as expand_radius, patch.object(
        service,
        "_fallback_city_wide",
        return_value=[],
    ) as city_wide, patch(
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
    city_wide.assert_not_called()


def test_get_candidates_uses_city_wide_when_radius_coverage_is_too_low_new() -> None:
    service = CandidateRetrievalService()
    db = MagicMock()
    ctx = SimpleNamespace(city_id="khanty-mansiysk", location=(61.0042, 69.0019))
    radius_candidates = [SimpleNamespace(id=index, category="park", lat=61.0, lng=69.0) for index in range(19)]
    city_wide_candidates = [SimpleNamespace(id=index, category="park", lat=61.0, lng=69.0) for index in range(80)]

    with patch.object(service, "_safe_spatial_density", return_value={"city_wide_eligible": 215}), patch.object(
        service, "_query_places", return_value=radius_candidates
    ), patch.object(
        service,
        "_fallback_expand_radius",
        return_value=radius_candidates,
    ), patch.object(
        service,
        "_fallback_city_wide",
        return_value=city_wide_candidates,
    ) as city_wide, patch(
        "services.candidate_retrieval_service.attach_public_images",
        side_effect=lambda _db, places: places,
    ), patch(
        "services.candidate_retrieval_service.balance_candidates_by_category",
        side_effect=lambda places, _limit: places,
    ):
        result = service.get_candidates(db, ctx)

    assert result == city_wide_candidates
    city_wide.assert_called_once_with(db, ctx)
    assert service.last_debug["fallback_city_wide_used"] is True
    assert service.last_debug["retrieval_strategy_used"] == "city_wide_fallback"
    assert service.last_debug["final_candidates_count"] == 80
    assert service.last_debug["retrieval_coverage_pct"] == 37.21


def test_get_candidates_keeps_sql_candidates_when_balancing_returns_empty_new() -> None:
    service = CandidateRetrievalService()
    db = MagicMock()
    ctx = SimpleNamespace(city_id="almaty", location=(43.238, 76.945))
    sql_candidates = [SimpleNamespace(id=index, category="cafe", lat=43.238, lng=76.945) for index in range(40)]

    with patch.object(service, "_safe_spatial_density", return_value={"city_wide_eligible": None}), patch.object(
        service, "_query_places", return_value=sql_candidates
    ), patch(
        "services.candidate_retrieval_service.attach_public_images",
        side_effect=lambda _db, places: places,
    ), patch(
        "services.candidate_retrieval_service.balance_candidates_by_category",
        return_value=[],
    ):
        result = service.get_candidates(db, ctx)

    assert result == sql_candidates


def test_get_candidates_keeps_sql_candidates_when_image_attach_fails_new() -> None:
    service = CandidateRetrievalService()
    db = MagicMock()
    ctx = SimpleNamespace(city_id="almaty", location=(43.238, 76.945))
    sql_candidates = [SimpleNamespace(id=index, category="museum", lat=43.238, lng=76.945) for index in range(40)]

    with patch.object(service, "_safe_spatial_density", return_value={"city_wide_eligible": None}), patch.object(
        service, "_query_places", return_value=sql_candidates
    ), patch(
        "services.candidate_retrieval_service.attach_public_images",
        side_effect=RuntimeError("image lookup failed"),
    ), patch(
        "services.candidate_retrieval_service.balance_candidates_by_category",
        side_effect=lambda places, _limit: places,
    ):
        result = service.get_candidates(db, ctx)

    assert result == sql_candidates
