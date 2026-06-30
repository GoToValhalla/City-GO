from __future__ import annotations

from pathlib import Path

from services.route_pipeline_trace import compact_route_trace, route_debug_summary

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_local_disk_cache_is_non_authoritative_and_persisted_new() -> None:
    cache_service = read("services/local_persistent_cache.py")
    compose = read("docker-compose.yml")
    settings = read("core/config.py")

    assert "not a source of truth" in cache_service
    assert "FanoutCache" in cache_service
    assert "local_cache:" in compose
    assert "- local_cache:/app/.cache/city-go" in compose
    assert "local_cache_enabled" in settings
    assert "local_cache_default_ttl_seconds" in settings


def test_external_enrichment_calls_use_read_through_cache_new() -> None:
    geocode = read("services/place_address_geocode.py")
    images = read("data/scripts/enrich_place_images.py")

    assert "CACHE_NAMESPACE = \"nominatim_reverse_v1\"" in geocode
    assert "get_cached_json(cache_key)" in geocode
    assert "set_cached_json(cache_key, payload, tag=\"provider:nominatim\")" in geocode
    assert "HTTP_TEXT_CACHE_NAMESPACE = \"image_enrichment_http_text_v1\"" in images
    assert "get_cached_text(cache_key)" in images
    assert "set_cached_text(cache_key, text" in images


def test_route_trace_compaction_preserves_decision_fields_new() -> None:
    entry = {
        "stage": "final",
        "request_id": "r1",
        "city_slug": "zelenogradsk",
        "selected_ids": [1, 2],
        "warnings": ["low_data"],
        "fallbacks": ["relax_photo"],
        "candidates": [{"id": 1, "score": 0.9, "reason": "museum"}],
        "debug_payload": {"large": list(range(100))},
    }
    compact = compact_route_trace([entry])[0]
    summary = route_debug_summary("r1", [entry])
    assert compact["request_id"] == "r1"
    assert compact["selected_ids"] == [1, 2]
    assert "debug_payload" not in compact
    assert summary["important"]["warnings"] == ["low_data"]
