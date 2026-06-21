from __future__ import annotations

from pathlib import Path

from services.local_persistent_cache import stable_cache_key


def test_stable_cache_key_is_deterministic_new() -> None:
    left = stable_cache_key("namespace", {"b": 2, "a": 1})
    right = stable_cache_key("namespace", {"a": 1, "b": 2})

    assert left == right
    assert left.startswith("namespace:")


def test_diskcache_dependency_is_pinned_new() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "diskcache==5.6.3" in requirements


def test_compose_mounts_local_cache_volume_new() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "local_cache:" in compose
    assert "LOCAL_CACHE_DIR: /app/.cache/city-go" in compose
    assert "- local_cache:/app/.cache/city-go" in compose


def test_import_enrichment_uses_cache_layer_new() -> None:
    geocode = Path("services/place_address_geocode.py").read_text(encoding="utf-8")
    images = Path("data/scripts/enrich_place_images.py").read_text(encoding="utf-8")

    assert "get_cached_json" in geocode
    assert "set_cached_json" in geocode
    assert "provider:nominatim" in geocode
    assert "get_cached_text" in images
    assert "set_cached_text" in images
    assert "image_enrichment_http_text_v1" in images
