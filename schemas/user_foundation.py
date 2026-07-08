from __future__ import annotations

from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    user_id: str
    status: str


class ProfilePatchRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    locale: str | None = Field(default=None, max_length=32)
    avatar_ref: str | None = Field(default=None, max_length=1000)


class TelegramVerifyRequest(BaseModel):
    init_data: str = Field(min_length=1)


class IdentityLinkRequest(BaseModel):
    from_identity_type: str = Field(min_length=1, max_length=64)
    from_identity_id: str = Field(min_length=1, max_length=64)
    to_identity_type: str = Field(min_length=1, max_length=64)
    to_identity_id: str = Field(min_length=1, max_length=64)
    method: str = Field(min_length=1, max_length=64)


class FavoritePlaceRequest(BaseModel):
    anonymous_device_id: str | None = Field(default=None, max_length=255)


class SavedRouteRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    route_snapshot_json: dict[str, object]
    source_route_id: int | None = None


class ReviewCreateRequest(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, max_length=5000)
    lang: str | None = Field(default=None, max_length=16)
    client_generated_id: str | None = Field(default=None, max_length=128)


class ReviewVoteRequest(BaseModel):
    value: int = Field(ge=-1, le=1)


class SuggestionCreateRequest(BaseModel):
    kind: str = Field(pattern="^(new_place|edit_place|report_problem)$")
    payload_json: dict[str, object]
    client_generated_id: str | None = Field(default=None, max_length=128)


class ModerationDecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
