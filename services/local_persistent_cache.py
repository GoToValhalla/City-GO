"""Best-effort local persistent cache for import/enrichment I/O.

This cache is intentionally local to a container/host. It is not a source of truth and must not be
used for route sessions, locks, or distributed state. Its job is to reduce repeated external calls
while keeping callers correct when the cache is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from core.config import settings

_LOGGER = logging.getLogger(__name__)
_CACHE: Any | None = None
_CACHE_INIT_FAILED = False


def cache_enabled() -> bool:
    return bool(getattr(settings, "local_cache_enabled", True))


def stable_cache_key(namespace: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def get_cached_json(key: str) -> tuple[bool, Any | None]:
    cache = _cache()
    if cache is None:
        return False, None
    value = cache.get(key, default=_MISS)
    if value is _MISS:
        return False, None
    return True, value


def set_cached_json(key: str, value: Any, *, expire: int | None = None, tag: str | None = None) -> None:
    cache = _cache()
    if cache is None:
        return
    ttl = _ttl(expire)
    try:
        cache.set(key, value, expire=ttl, tag=tag)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("local cache set failed key=%s error=%s", key, exc)


def get_cached_text(key: str) -> tuple[bool, str | None]:
    found, value = get_cached_json(key)
    return found, value if isinstance(value, str) else None


def set_cached_text(key: str, value: str, *, expire: int | None = None, tag: str | None = None) -> None:
    if value:
        set_cached_json(key, value, expire=expire, tag=tag)


def cache_stats() -> dict[str, Any]:
    cache = _cache()
    if cache is None:
        return {"enabled": cache_enabled(), "available": False}
    try:
        hits, misses = cache.stats(enable=True)
        return {
            "enabled": True,
            "available": True,
            "directory": getattr(cache, "directory", None),
            "volume_bytes": cache.volume(),
            "hits": hits,
            "misses": misses,
        }
    except Exception as exc:  # noqa: BLE001
        return {"enabled": True, "available": False, "error": str(exc)}


def _ttl(expire: int | None) -> int | None:
    if expire is not None:
        return expire
    default_ttl = int(getattr(settings, "local_cache_default_ttl_seconds", 2_592_000) or 0)
    return default_ttl if default_ttl > 0 else None


def _cache() -> Any | None:
    global _CACHE, _CACHE_INIT_FAILED
    if not cache_enabled() or _CACHE_INIT_FAILED:
        return None
    if _CACHE is not None:
        return _CACHE
    try:
        from diskcache import FanoutCache

        _CACHE = FanoutCache(
            directory=str(getattr(settings, "local_cache_dir", "/app/.cache/city-go")),
            shards=max(1, int(getattr(settings, "local_cache_shards", 8) or 8)),
            timeout=1,
            size_limit=max(1, int(getattr(settings, "local_cache_size_limit_bytes", 1_073_741_824) or 1_073_741_824)),
        )
        _CACHE.stats(enable=True)
        return _CACHE
    except Exception as exc:  # noqa: BLE001
        try:
            _CACHE = _JsonFileCache(Path(str(getattr(settings, "local_cache_dir", "/app/.cache/city-go"))))
            return _CACHE
        except Exception as fallback_exc:  # noqa: BLE001
            _CACHE_INIT_FAILED = True
            _LOGGER.warning("local persistent cache disabled: %s; fallback failed: %s", exc, fallback_exc)
            return None


class _Miss:
    pass


_MISS = _Miss()


class _JsonFileCache:
    """Tiny disk fallback used when optional diskcache is unavailable in tests/dev."""

    def __init__(self, directory: Path) -> None:
        self.directory = str(directory)
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        path = self._path(key)
        if not path.exists():
            return default
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return default
        expire_at = payload.get("expire_at")
        if isinstance(expire_at, (int, float)) and expire_at <= time.time():
            path.unlink(missing_ok=True)
            return default
        return payload.get("value", default)

    def set(self, key: str, value: Any, *, expire: int | None = None, tag: str | None = None) -> None:
        expire_at = time.time() + expire if expire else None
        payload = {"value": value, "expire_at": expire_at, "tag": tag}
        self._path(key).write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")

    def stats(self, enable: bool = True) -> tuple[int, int]:
        return 0, 0

    def volume(self) -> int:
        return sum(path.stat().st_size for path in self._directory.glob("*.json"))

    def close(self) -> None:
        return None

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._directory / f"{digest}.json"
