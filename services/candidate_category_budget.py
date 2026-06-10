from functools import reduce


def balance_candidates_by_category(candidates: list[object], limit: int) -> list[object]:
    grouped = reduce(_group_by_category, candidates, {})
    categories = sorted(grouped.keys(), key=lambda key: len(grouped[key]), reverse=True)
    return _round_robin(grouped, categories, limit, 0, [])


def _group_by_category(groups: dict[str, list[object]], candidate: object) -> dict[str, list[object]]:
    category = str(getattr(candidate, "category", "") or "unknown")
    return {**groups, category: [*groups.get(category, []), candidate]}


def _round_robin(
    groups: dict[str, list[object]],
    categories: list[str],
    limit: int,
    offset: int,
    acc: list[object],
) -> list[object]:
    if len(acc) >= limit or not categories:
        return acc[:limit]
    picked = _pick_round(groups, categories, offset)
    if not picked:
        return acc[:limit]
    return _round_robin(groups, categories, limit, offset + 1, [*acc, *picked])


def _pick_round(
    groups: dict[str, list[object]],
    categories: list[str],
    offset: int,
) -> list[object]:
    return list(
        filter(
            None,
            map(lambda category: _item_at(groups[category], offset), categories),
        )
    )


def _item_at(items: list[object], index: int) -> object | None:
    return items[index] if index < len(items) else None
