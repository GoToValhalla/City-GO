from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


_LOGGER = logging.getLogger("city_go.route_pipeline")


@dataclass
class RoutePipelineTrace:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, stage: str, **payload: Any) -> None:
        self.entries.append({"stage": stage, **payload})

    def snapshot(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.entries]


def top_scores(scored: list[object], limit: int = 3) -> list[float]:
    return [round(float(getattr(item, "score", 0.0) or 0.0), 4) for item in scored[:limit]]


def timed_trace(trace: RoutePipelineTrace, stage: str, started: float, **payload: Any) -> None:
    trace.add(stage, duration_ms=int((perf_counter() - started) * 1000), **payload)


def log_route_trace(route_id: str, trace: RoutePipelineTrace) -> None:
    payload = {"route_id": route_id, "trace": trace.snapshot()}
    _LOGGER.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
