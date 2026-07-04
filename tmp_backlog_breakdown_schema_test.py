from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminBacklogSummary(BaseModel):
    unique_problem_places: int
    total_problem_signals: int
    route_blocker_places: int
    auto_fixable_places: int
    manual_places: int
    verification_backlog_places: int
    content_gap_places: int
