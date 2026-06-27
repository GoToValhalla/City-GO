"""Small immutable payloads for data quality services."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueDraft:
    place_id: int | None
    city_id: int | None
    issue_type: str
    severity: str
    reason: str
    source: str
    evidence: dict[str, object]
    fingerprint: str


@dataclass(frozen=True)
class RefreshSummary:
    scanned: int
    created: int
    updated: int
    unchanged: int
    resolved: int
    by_issue_type: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        return {
            "scanned": self.scanned,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "resolved": self.resolved,
            "by_issue_type": self.by_issue_type,
        }
