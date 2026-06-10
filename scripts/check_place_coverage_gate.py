import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.place_coverage_gate_service import CoverageGateThresholds, evaluate_coverage_gate


def main() -> int:
    payload = _load_coverage_payload(_coverage_url())
    if payload is None:
        return 1
    result = evaluate_coverage_gate(payload, _thresholds_from_env())
    tuple(map(lambda failure: print(f"coverage gate failed: {failure}"), result.failures))
    return 0 if result.passed else 1


def _coverage_url() -> str:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    city_slug = os.getenv("COVERAGE_GATE_CITY_SLUG", "zelenogradsk")
    return f"{base_url}/place-coverage/{city_slug}"


def _thresholds_from_env() -> CoverageGateThresholds:
    return CoverageGateThresholds(
        min_total_places=_int_env("COVERAGE_GATE_MIN_TOTAL_PLACES", 80),
        min_coordinates_ratio=_float_env("COVERAGE_GATE_MIN_COORDINATES_RATIO", 0.95),
        min_opening_hours_ratio=_float_env("COVERAGE_GATE_MIN_OPENING_HOURS_RATIO", 0.70),
        min_visit_duration_ratio=_float_env("COVERAGE_GATE_MIN_VISIT_DURATION_RATIO", 0.80),
        required_categories=_categories_env(),
    )


def _load_coverage_payload(url: str) -> Mapping[str, object] | None:
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        print(f"coverage gate failed: cannot load {url}: {exc}")
        return None
    if not isinstance(payload, dict):
        print("coverage gate failed: endpoint response is not an object")
        return None
    return payload


def _categories_env() -> tuple[str, ...]:
    raw = os.getenv("COVERAGE_GATE_REQUIRED_CATEGORIES", "coffee,food,walk,park,culture,evening")
    return tuple(filter(None, map(str.strip, raw.split(","))))


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


if __name__ == "__main__":
    sys.exit(main())
