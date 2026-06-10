from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

SIGNAL_VIEW_PLACE = "view_place"
SIGNAL_FAVORITE_PLACE = "favorite_place"
SIGNAL_LIKE_PLACE = "like_place"
SIGNAL_DISLIKE_PLACE = "dislike_place"
SIGNAL_VISITED_PLACE = "visited_place"
SIGNAL_COMPLETED_ROUTE = "completed_route"

POSITIVE_PLACE_SIGNALS = frozenset((SIGNAL_FAVORITE_PLACE, SIGNAL_LIKE_PLACE))
NEGATIVE_PLACE_SIGNALS = frozenset((SIGNAL_DISLIKE_PLACE,))
VISIT_PLACE_SIGNALS = frozenset((SIGNAL_VISITED_PLACE,))


class UserSignalCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    signal_type: str = Field(min_length=1, max_length=100)
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: str = Field(min_length=1, max_length=100)
    payload: dict[str, object] | None = None


class UserSignalRead(UserSignalCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSignalSummary(BaseModel):
    user_id: str
    total: int = 0
    by_signal_type: dict[str, int] = Field(default_factory=dict)
    by_entity_type: dict[str, int] = Field(default_factory=dict)


class UserDerivedProfile(BaseModel):
    user_id: str
    total_signals: int = 0
    preferred_categories: dict[str, int] = Field(default_factory=dict)
    action_counts: dict[str, int] = Field(default_factory=dict)
    favorite_place_ids: list[str] = Field(default_factory=list)
    liked_place_ids: list[str] = Field(default_factory=list)
    disliked_place_ids: list[str] = Field(default_factory=list)
    visited_place_ids: list[str] = Field(default_factory=list)
    completed_routes_count: int = 0
    last_activity_at: datetime | None = None
