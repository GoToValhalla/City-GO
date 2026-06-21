from collections import defaultdict


def balance_candidates_by_category(candidates: list[object], limit: int) -> list[object]:
    """Interleave categories without ever dropping a usable non-empty pool to zero."""
    if limit <= 0 or not candidates:
        return []

    grouped: dict[str, list[object]] = defaultdict(list)
    for candidate in candidates:
        grouped[_category(candidate)].append(candidate)

    categories = sorted(grouped.keys(), key=lambda key: len(grouped[key]), reverse=True)
    balanced: list[object] = []
    offset = 0

    while len(balanced) < limit:
        picked_this_round = False
        for category in categories:
            items = grouped[category]
            if offset >= len(items):
                continue
            balanced.append(items[offset])
            picked_this_round = True
            if len(balanced) >= limit:
                break

        if not picked_this_round:
            break
        offset += 1

    if balanced:
        return balanced[:limit]

    return candidates[:limit]


def _category(candidate: object) -> str:
    return str(getattr(candidate, "category", "") or "unknown").strip().casefold() or "unknown"
