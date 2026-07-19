"""Canonical ownership registries for controlled Place state.

Generic create/update paths must reject these fields. Dedicated mutation services
own each state machine and tests import these registries to prevent drift.
"""

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
        "route_exclusion_reason",
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

VERIFICATION_OWNED_FIELDS = frozenset(
    {
        "verification_status",
        "verification_source",
        "verification_method",
        "verified_at",
        "verified_by",
        "needs_recheck_at",
        "verification_comment",
        "existence_confidence_score",
        "existence_confidence_level",
    }
)

CONTROLLED_PLACE_INPUT_FIELDS = PUBLICATION_CONTROLLED_INPUT_FIELDS | VERIFICATION_OWNED_FIELDS
