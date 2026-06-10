from schemas.merged_context import MergedContext


def personalization_score(place: object, ctx: MergedContext) -> float:
    place_id = str(getattr(place, "id", ""))
    category = str(getattr(place, "category", "") or "").strip().casefold()
    score = 0.5
    if place_id in set(map(str, ctx.liked_place_ids)):
        score += 0.30
    if place_id in set(map(str, ctx.visited_place_ids)):
        score -= 0.12
    score += min(0.20, max(0.0, float(ctx.category_affinity.get(category, 0.0)) * 0.2))
    return max(0.0, min(1.0, score))
