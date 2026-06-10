from types import SimpleNamespace

from services.candidate_category_budget import balance_candidates_by_category


def _candidate(category: str, idx: int) -> SimpleNamespace:
    return SimpleNamespace(category=category, idx=idx)


def test_balance_candidates_by_category_interleaves_categories() -> None:
    candidates = [
        _candidate("cafe", 1),
        _candidate("cafe", 2),
        _candidate("museum", 3),
        _candidate("park", 4),
    ]
    result = balance_candidates_by_category(candidates, limit=4)
    assert [item.category for item in result[:3]] == ["cafe", "museum", "park"]


def test_balance_candidates_by_category_respects_limit() -> None:
    candidates = [_candidate("cafe", 1), _candidate("museum", 2), _candidate("park", 3)]
    assert len(balance_candidates_by_category(candidates, limit=2)) == 2


def test_balance_candidates_by_category_handles_empty_list() -> None:
    assert balance_candidates_by_category([], limit=10) == []
