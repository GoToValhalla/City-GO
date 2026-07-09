from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path

from core.feature_flags import FeatureFlag, require_feature
from schemas.user_foundation import (
    FavoritePlaceRequest,
    IdentityLinkRequest,
    ModerationDecisionRequest,
    ProfilePatchRequest,
    ReviewCreateRequest,
    ReviewVoteRequest,
    SavedRouteRequest,
    SuggestionCreateRequest,
    TelegramVerifyRequest,
)

# Dark-launch endpoints must not appear in /openapi.json or /docs while the
# corresponding feature flags are OFF by default. include_in_schema=False hides
# them from schema generation; require_feature() still gates every handler at
# call time regardless of schema visibility, so a direct request still returns
# a structured 404 (feature_disabled).
router = APIRouter(tags=["user-foundation"], include_in_schema=False)


def _auth_not_implemented() -> None:
    raise HTTPException(status_code=401, detail={"code": "auth_not_implemented"})


def _forbidden_until_live_moderation() -> None:
    raise HTTPException(status_code=403, detail={"code": "moderation_not_implemented"})


@router.get("/me")
def get_me() -> dict[str, object]:
    require_feature(FeatureFlag.PROFILE_ENABLED)
    _auth_not_implemented()


@router.patch("/me/profile")
def patch_me_profile(payload: ProfilePatchRequest) -> dict[str, object]:
    require_feature(FeatureFlag.PROFILE_ENABLED)
    _auth_not_implemented()


@router.post("/identity/telegram/verify")
def verify_telegram_identity(payload: TelegramVerifyRequest) -> dict[str, object]:
    require_feature(FeatureFlag.TELEGRAM_IDENTITY_ENABLED)
    # Live validation must use the official Telegram WebApp initData signature pattern.
    # It is intentionally not implemented while the flag is OFF by default.
    _auth_not_implemented()


@router.post("/identity/link")
def link_identity(payload: IdentityLinkRequest) -> dict[str, object]:
    require_feature(FeatureFlag.ACCOUNT_LINKING_ENABLED)
    _auth_not_implemented()


@router.get("/identity/links")
def list_identity_links() -> dict[str, object]:
    require_feature(FeatureFlag.ACCOUNT_LINKING_ENABLED)
    _auth_not_implemented()


@router.get("/me/favorites")
def list_my_favorites() -> dict[str, object]:
    require_feature(FeatureFlag.FAVORITES_ENABLED)
    _auth_not_implemented()


@router.post("/me/favorites/places/{place_id}")
def add_favorite_place(
    payload: FavoritePlaceRequest,
    place_id: int = Path(gt=0),
) -> dict[str, object]:
    require_feature(FeatureFlag.FAVORITES_ENABLED)
    _auth_not_implemented()


@router.delete("/me/favorites/places/{place_id}")
def delete_favorite_place(place_id: int = Path(gt=0)) -> dict[str, object]:
    require_feature(FeatureFlag.FAVORITES_ENABLED)
    _auth_not_implemented()


@router.get("/me/saved-routes")
def list_saved_routes() -> dict[str, object]:
    require_feature(FeatureFlag.SAVED_ROUTES_ENABLED)
    _auth_not_implemented()


@router.post("/me/saved-routes")
def create_saved_route(payload: SavedRouteRequest) -> dict[str, object]:
    require_feature(FeatureFlag.SAVED_ROUTES_ENABLED)
    _auth_not_implemented()


@router.get("/places/{place_id}/reviews")
def list_place_reviews(place_id: int = Path(gt=0)) -> dict[str, object]:
    require_feature(FeatureFlag.PUBLIC_REVIEWS_ENABLED)
    return {"items": [], "total": 0, "place_id": place_id}


@router.post("/places/{place_id}/reviews")
def create_place_review(
    payload: ReviewCreateRequest,
    place_id: int = Path(gt=0),
) -> dict[str, object]:
    require_feature(FeatureFlag.REVIEWS_ENABLED)
    _auth_not_implemented()


@router.post("/reviews/{review_id}/vote")
def vote_review(
    payload: ReviewVoteRequest,
    review_id: str,
) -> dict[str, object]:
    require_feature(FeatureFlag.REVIEW_VOTES_ENABLED)
    _auth_not_implemented()


@router.post("/places/{place_id}/suggestions")
def create_place_suggestion(
    payload: SuggestionCreateRequest,
    place_id: int = Path(gt=0),
) -> dict[str, object]:
    require_feature(FeatureFlag.SUGGESTIONS_ENABLED)
    _auth_not_implemented()


@router.get("/admin/moderation")
def list_admin_moderation() -> dict[str, object]:
    require_feature(FeatureFlag.MODERATION_ENABLED)
    _forbidden_until_live_moderation()


@router.post("/admin/moderation/{id}/approve")
def approve_moderation_item(
    payload: ModerationDecisionRequest,
    id: str,
) -> dict[str, object]:
    require_feature(FeatureFlag.MODERATION_ENABLED)
    _forbidden_until_live_moderation()


@router.post("/admin/moderation/{id}/reject")
def reject_moderation_item(
    payload: ModerationDecisionRequest,
    id: str,
) -> dict[str, object]:
    require_feature(FeatureFlag.MODERATION_ENABLED)
    _forbidden_until_live_moderation()
