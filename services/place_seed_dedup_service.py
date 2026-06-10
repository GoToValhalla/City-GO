from dataclasses import dataclass
from functools import reduce

from schemas.place_seed_item import PlaceSeedItem


@dataclass(frozen=True)
class DedupResult:
    unique_items: list[PlaceSeedItem]
    duplicate_slugs: list[str]


def deduplicate_place_seed_items(items: list[PlaceSeedItem]) -> DedupResult:
    unique, _seen, duplicates = reduce(_append_unique, items, ([], set(), []))
    return DedupResult(unique_items=unique, duplicate_slugs=duplicates)


def _append_unique(
    state: tuple[list[PlaceSeedItem], set[str], list[str]],
    item: PlaceSeedItem,
) -> tuple[list[PlaceSeedItem], set[str], list[str]]:
    unique, seen, duplicates = state
    slug = item.slug
    if slug in seen:
        return unique, seen, [*duplicates, slug]
    return [*unique, item], {*seen, slug}, duplicates
