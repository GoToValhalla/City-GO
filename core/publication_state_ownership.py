"""Canonical ownership registry for Place publication state."""

from __future__ import annotations

PUBLICATION_OWNED_FIELDS = frozenset(
    {
        "publication_status",
        "publication_reason_code",
        "publication_reason_details",
        "publication_comment",
        "is_active",
        "is_published",
        "is_visible_in_catalog",
        "is_searchable",
        "is_route_eligible",
        "published_at",
        "unpublished_at",
    }
)

PUBLICATION_API_ALIASES = frozenset(
    {
        "visible_to_users",
        "searchable",
        "route_enabled",
    }
)

PUBLICATION_CONTROLLED_INPUT_FIELDS = PUBLICATION_OWNED_FIELDS | PUBLICATION_API_ALIASES
