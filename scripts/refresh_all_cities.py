#!/usr/bin/env python3
"""LEGACY/SCOPE REFRESH OPERATOR SCRIPT.

Status: historical production-container refresh script for enabled import scopes.

How it worked:
- Runs old OSM import v2 for enabled `CityImportScope` rows.
- Runs Data Coverage Assurance.
- Sends an operations report.

Current source of truth for admin-triggered imports:
- admin city import queue/job services;
- `CityAdminImportJob` and admin import runner;
- publication/product state repair scripts for publication state.

Rules:
- Do not use this script to repair publication state.
- Do not allow failures here to change `City.is_active` or `City.launch_status`.
- Keep only as an operator compatibility script until scope refresh is migrated to
  the current admin import job model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_

from data.scripts.import_city_osm_v2 import run as run_osm_import
from db.session import SessionLocal
from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_image import PUBLIC_PLACE_IMAGE_STATUSES, PlaceImage
from services.data_coverage_assurance import run_data_coverage_assurance


@dataclass
class CityMetrics:
    slug: str
    name: str
    total: int = 0
    active: int = 0
    published: int = 0
    visible: int = 0
    route_eligible: int = 0
    searchable: int = 0
    with_address: int = 0
    with_photo: int = 0
    needs_publication_review: int = 0
    unverified: int = 0
    readiness_score: int = 0
    quality_status: str = "unknown"


@dataclass
class CityRun:
    slug: str
    name: str
    before: CityMetrics
    after: CityMetrics | None = None
    scopes: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    coverage_summary: dict[str, Any] | None = None
    coverage_acceptance: dict[str, Any] | None = None

    def add_scope_result(self, result: dict[str, Any]) -> None:
        self.scopes.append(result)
        assurance = result.get("data_coverage_assurance") if isinstance(result, dict) else None
        if isinstance(assurance, dict):
            summary = assurance.get("summary")
            acceptance = assurance.get("acceptance")
            if isinstance(summary, dict):
                self.coverage_summary = summary
            if isinstance(acceptance, dict):
                self.coverage_acceptance = acceptance

    @property
    def created(self) -> int:
        return _sum_scope_number(self.scopes, "created")

    @property
    def updated(self) -> int:
        return _sum_scope_number(self.scopes, "updated")

    @property
    def candidates(self) -> int:
        return _sum_scope_number(self.scopes, "candidates")

    @property
    def failed(self) -> bool:
        return bool(self.failures)


def _sum_scope_number(scopes: list[dict[str, Any]], key: str) -> int:
    total = 0
    for scope in scopes:
        value = scope.get(key)
        if isinstance(value, int):
            total += value
    return total
