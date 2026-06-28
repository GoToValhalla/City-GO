"""Shared constants for deterministic data quality checks."""

ISSUE_MISSING_PHOTO = "missing_photo"
ISSUE_MISSING_ADDRESS = "missing_address"
ISSUE_LOW_CONFIDENCE = "low_confidence"
ISSUE_REQUIRES_REVIEW = "requires_review"
ISSUE_ROUTE_SUSPICIOUS = "route_eligibility_suspicious"
ISSUE_CATEGORY_CONFLICT = "category_conflict"
ISSUE_SOURCE_CONFLICT = "source_conflict"
ISSUE_WEAK_DESCRIPTION = "weak_description"
ISSUE_BROKEN_PHOTO = "broken_photo"
ISSUE_POSSIBLE_DUPLICATE = "possible_duplicate"

OPEN_STATUSES = {"open", "candidate_created", "deferred"}

STOPLIST_CATEGORIES = frozenset({
    "pharmacy", "bank", "atm", "bus_stop", "transit_stop", "railway_station",
    "parking", "toilets", "utility", "industrial", "government", "police",
    "hospital", "clinic", "post_office", "service",
})

SUMMARY_KEYS = {
    "published_without_photo": ISSUE_MISSING_PHOTO,
    "without_address": ISSUE_MISSING_ADDRESS,
    "low_confidence": ISSUE_LOW_CONFIDENCE,
    "requires_review": ISSUE_REQUIRES_REVIEW,
    "route_eligibility_suspicious": ISSUE_ROUTE_SUSPICIOUS,
    "possible_duplicates": ISSUE_POSSIBLE_DUPLICATE,
}

BULK_ACTIONS = {
    "propose_exclude_from_routes",
    "propose_duplicate_review",
    "defer_issues",
    "ignore_issues",
    "mark_resolved_if_current_state_ok",
}