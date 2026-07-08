"""Typed dark-launch feature flag registry.

All flags in this module default to OFF through core.config.Settings.
New dark-launch user/account/review functionality must check these helpers
instead of scattering ad-hoc string checks across routers/services.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from fastapi import HTTPException

from core.config import settings


class FeatureFlag(StrEnum):
    AUTH_ENABLED = "auth.enabled"
    PROFILE_ENABLED = "profile.enabled"
    FAVORITES_ENABLED = "favorites.enabled"
    SAVED_ROUTES_ENABLED = "saved_routes.enabled"
    ROUTE_HISTORY_ENABLED = "route_history.enabled"
    REVIEWS_ENABLED = "reviews.enabled"
    PUBLIC_REVIEWS_ENABLED = "public_reviews.enabled"
    REVIEW_VOTES_ENABLED = "review_votes.enabled"
    USER_PHOTOS_ENABLED = "user_photos.enabled"
    SUGGESTIONS_ENABLED = "suggestions.enabled"
    MODERATION_ENABLED = "moderation.enabled"
    TELEGRAM_IDENTITY_ENABLED = "telegram_identity.enabled"
    ACCOUNT_LINKING_ENABLED = "account_linking.enabled"


_FLAG_SETTING_ATTRS: dict[FeatureFlag, str] = {
    FeatureFlag.AUTH_ENABLED: "feature_auth_enabled",
    FeatureFlag.PROFILE_ENABLED: "feature_profile_enabled",
    FeatureFlag.FAVORITES_ENABLED: "feature_favorites_enabled",
    FeatureFlag.SAVED_ROUTES_ENABLED: "feature_saved_routes_enabled",
    FeatureFlag.ROUTE_HISTORY_ENABLED: "feature_route_history_enabled",
    FeatureFlag.REVIEWS_ENABLED: "feature_reviews_enabled",
    FeatureFlag.PUBLIC_REVIEWS_ENABLED: "feature_public_reviews_enabled",
    FeatureFlag.REVIEW_VOTES_ENABLED: "feature_review_votes_enabled",
    FeatureFlag.USER_PHOTOS_ENABLED: "feature_user_photos_enabled",
    FeatureFlag.SUGGESTIONS_ENABLED: "feature_suggestions_enabled",
    FeatureFlag.MODERATION_ENABLED: "feature_moderation_enabled",
    FeatureFlag.TELEGRAM_IDENTITY_ENABLED: "feature_telegram_identity_enabled",
    FeatureFlag.ACCOUNT_LINKING_ENABLED: "feature_account_linking_enabled",
}

_FLAG_DEPENDENCIES: dict[FeatureFlag, tuple[FeatureFlag, ...]] = {
    FeatureFlag.PUBLIC_REVIEWS_ENABLED: (FeatureFlag.REVIEWS_ENABLED, FeatureFlag.MODERATION_ENABLED),
    FeatureFlag.REVIEW_VOTES_ENABLED: (FeatureFlag.PUBLIC_REVIEWS_ENABLED,),
    FeatureFlag.USER_PHOTOS_ENABLED: (FeatureFlag.MODERATION_ENABLED,),
    FeatureFlag.ACCOUNT_LINKING_ENABLED: (FeatureFlag.TELEGRAM_IDENTITY_ENABLED,),
    # The platform does not have live auth yet. Profile may later work against an explicit
    # anonymous identity strategy, but until that is implemented it depends on auth.enabled.
    FeatureFlag.PROFILE_ENABLED: (FeatureFlag.AUTH_ENABLED,),
    # Route history is privacy-sensitive and must remain blocked until explicit consent exists.
    FeatureFlag.ROUTE_HISTORY_ENABLED: (FeatureFlag.AUTH_ENABLED,),
}


def all_feature_flags() -> tuple[FeatureFlag, ...]:
    return tuple(FeatureFlag)


def feature_flag_setting_name(flag: FeatureFlag | str) -> str:
    resolved = FeatureFlag(flag)
    return _FLAG_SETTING_ATTRS[resolved]


def feature_flag_dependencies(flag: FeatureFlag | str) -> tuple[FeatureFlag, ...]:
    return _FLAG_DEPENDENCIES.get(FeatureFlag(flag), ())


def is_feature_enabled(flag: FeatureFlag | str, *, _seen: frozenset[FeatureFlag] | None = None) -> bool:
    """Return effective flag state including dependency gates."""

    resolved = FeatureFlag(flag)
    seen = _seen or frozenset()
    if resolved in seen:
        return False
    configured = bool(getattr(settings, feature_flag_setting_name(resolved), False))
    if not configured:
        return False
    return all(is_feature_enabled(dependency, _seen=seen | {resolved}) for dependency in feature_flag_dependencies(resolved))


def disabled_feature_detail(flag: FeatureFlag | str) -> dict[str, str]:
    return {"code": "feature_disabled", "feature": FeatureFlag(flag).value}


def raise_feature_disabled(flag: FeatureFlag | str) -> None:
    raise HTTPException(status_code=404, detail=disabled_feature_detail(flag))


def require_feature(flag: FeatureFlag | str) -> None:
    if not is_feature_enabled(flag):
        raise_feature_disabled(flag)


def effective_feature_matrix(flags: Iterable[FeatureFlag] | None = None) -> dict[str, bool]:
    return {flag.value: is_feature_enabled(flag) for flag in (tuple(flags) if flags is not None else all_feature_flags())}
