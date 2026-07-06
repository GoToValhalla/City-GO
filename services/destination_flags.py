"""Destination foundation feature flags."""

from __future__ import annotations

from core.config import settings


def destination_foundation_enabled() -> bool:
    return bool(settings.destination_foundation_enabled)


def destination_catalog_reads_enabled() -> bool:
    return destination_foundation_enabled() and bool(settings.destination_catalog_reads_enabled)


def destination_route_reads_enabled() -> bool:
    return destination_foundation_enabled() and bool(settings.destination_route_reads_enabled)


def destination_import_enabled() -> bool:
    return destination_foundation_enabled() and bool(settings.destination_import_enabled)
