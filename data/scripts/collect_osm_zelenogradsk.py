import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from data.scripts.osm_seed_builder import build_seed

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RAW_PATH = Path("data/raw/zelenogradsk_osm.json")
SEED_PATH = Path("data/seeds/place_import/zelenogradsk_osm.json")
SELECTORS = (
    'nwr["amenity"~"cafe|restaurant|bar|pub|fast_food|ice_cream|marketplace"]',
    'nwr["tourism"~"museum|gallery|attraction|viewpoint|artwork|hotel|picnic_site"]',
    'nwr["leisure"~"park|garden|playground|fitness_station|sports_centre"]',
    'nwr["shop"~"bakery|pastry|coffee|books|confectionery"]',
    'nwr["natural"~"beach"]',
    'nwr["historic"~"monument|memorial"]',
    'nwr["man_made"~"pier|tower"]',
    'nwr["highway"~"pedestrian|footway"]["name"]',
)


def overpass_query() -> str:
    body = "\n  ".join(map(lambda selector: f"{selector}(area.city);", SELECTORS))
    return f"""
[out:json][timeout:60];
area["name"="Зеленоградск"]["admin_level"="8"]->.city;
(
  {body}
);
out center tags;
"""


def fetch_overpass(query: str, opener=urlopen) -> dict[str, Any]:
    payload = urlencode({"data": query}).encode("utf-8")
    try:
        with opener(OVERPASS_URL, data=payload, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"overpass request failed: {exc}") from exc


def collect_places(
    raw_path: Path = RAW_PATH,
    seed_path: Path = SEED_PATH,
    opener=urlopen,
    now: datetime | None = None,
) -> dict[str, object]:
    raw = fetch_overpass(overpass_query(), opener)
    seed = build_seed(raw, now or datetime.now(timezone.utc))
    write_json(raw_path, raw)
    write_json(seed_path, seed)
    return {"raw_elements": len(raw.get("elements", [])), "seed_items": len(seed["items"])}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    result = collect_places()
    print(f"Collected raw={result['raw_elements']} seed={result['seed_items']}")


if __name__ == "__main__":
    main()
