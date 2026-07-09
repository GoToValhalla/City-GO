from __future__ import annotations

from fastapi import HTTPException

from core import feature_flags
from core.config import settings
from core.feature_flags import (
    FeatureFlag,
    disabled_feature_detail,
    is_feature_enabled,
    require_feature,
    validate_feature_flag_configuration,
)
import pytest


def test_all_dark_launch_flags_default_false_new() -> None:
    for flag in FeatureFlag:
        assert getattr(settings, feature_flags.feature_flag_setting_name(flag)) is False
        assert is_feature_enabled(flag) is False


def test_feature_disabled_detail_shape_new() -> None:
    assert disabled_feature_detail(FeatureFlag.REVIEWS_ENABLED) == {
        "code": "feature_disabled",
        "feature": "reviews.enabled",
    }


def test_require_feature_raises_structured_404_new() -> None:
    try:
        require_feature(FeatureFlag.REVIEWS_ENABLED)
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == {"code": "feature_disabled", "feature": "reviews.enabled"}
    else:  # pragma: no cover - explicit safety assertion
        raise AssertionError("feature OFF must raise 404 feature_disabled")


def test_public_reviews_requires_reviews_and_moderation_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "feature_public_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_moderation_enabled", False)

    assert is_feature_enabled(FeatureFlag.PUBLIC_REVIEWS_ENABLED) is False

    monkeypatch.setattr(settings, "feature_moderation_enabled", True)
    assert is_feature_enabled(FeatureFlag.PUBLIC_REVIEWS_ENABLED) is True


def test_review_votes_requires_public_reviews_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "feature_review_votes_enabled", True)
    monkeypatch.setattr(settings, "feature_public_reviews_enabled", False)
    monkeypatch.setattr(settings, "feature_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_moderation_enabled", True)

    assert is_feature_enabled(FeatureFlag.REVIEW_VOTES_ENABLED) is False


def test_no_current_public_endpoint_is_gated_by_auth_new(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_validate_feature_flag_configuration_passes_with_all_defaults_new() -> None:
    validate_feature_flag_configuration()


def test_validate_rejects_public_reviews_without_reviews_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "feature_public_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_reviews_enabled", False)
    monkeypatch.setattr(settings, "feature_moderation_enabled", True)

    with pytest.raises(ValueError, match="public_reviews.enabled requires reviews.enabled"):
        validate_feature_flag_configuration()


def test_validate_rejects_public_reviews_without_moderation_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "feature_public_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_moderation_enabled", False)

    with pytest.raises(ValueError, match="public_reviews.enabled requires moderation.enabled"):
        validate_feature_flag_configuration()


def test_validate_rejects_review_votes_without_public_reviews_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "feature_review_votes_enabled", True)
    monkeypatch.setattr(settings, "feature_public_reviews_enabled", False)

    with pytest.raises(ValueError, match="review_votes.enabled requires public_reviews.enabled"):
        validate_feature_flag_configuration()


def test_validate_rejects_account_linking_without_telegram_identity_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "feature_account_linking_enabled", True)
    monkeypatch.setattr(settings, "feature_telegram_identity_enabled", False)

    with pytest.raises(ValueError, match="account_linking.enabled requires telegram_identity.enabled"):
        validate_feature_flag_configuration()


def test_validate_passes_with_fully_satisfied_dependency_chain_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "feature_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_moderation_enabled", True)
    monkeypatch.setattr(settings, "feature_public_reviews_enabled", True)
    monkeypatch.setattr(settings, "feature_review_votes_enabled", True)
    monkeypatch.setattr(settings, "feature_telegram_identity_enabled", True)
    monkeypatch.setattr(settings, "feature_account_linking_enabled", True)
    monkeypatch.setattr(settings, "feature_auth_enabled", True)
    monkeypatch.setattr(settings, "feature_profile_enabled", True)
    monkeypatch.setattr(settings, "feature_route_history_enabled", True)
    monkeypatch.setattr(settings, "feature_user_photos_enabled", True)

    validate_feature_flag_configuration()
