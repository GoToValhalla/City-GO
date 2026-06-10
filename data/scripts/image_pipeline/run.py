from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from data.scripts.image_pipeline.commons import fetch_depicts_images
from data.scripts.image_pipeline.io import catalog_items, raw_by_osm_url, raw_tags, read_json, write_json
from data.scripts.image_pipeline.mapillary import fetch_area_images
from data.scripts.image_pipeline.official import fetch_og_image
from data.scripts.image_pipeline.selector import choose_image
from data.scripts.image_pipeline.verification import verification_queue
from data.scripts.image_pipeline.wikidata import fetch_p18_and_website, match_place

CATALOG = Path("frontend/public/data/zelenogradsk_places.json")
RAW = Path("data/raw/zelenogradsk_osm.json")
OUT = Path("data/enrichment/zelenogradsk_image_enrichment.json")
QUEUE = Path("data/enrichment/zelenogradsk_image_verification_queue.json")


def run_pipeline(
    catalog_path: Path = CATALOG,
    raw_path: Path = RAW,
    out_path: Path = OUT,
    queue_path: Path = QUEUE,
    live: bool = False,
    mapillary_token: str | None = None,
) -> dict[str, int]:
    payload = read_json(catalog_path)
    raw_index = raw_by_osm_url(read_json(raw_path))
    items = tuple(map(lambda place: enrich_place(place, raw_index, live, mapillary_token), catalog_items(payload)))
    write_json(catalog_path, {**payload, "schema_version": "1.3", "items": items})
    write_json(out_path, {"items": tuple(map(artifact, items))})
    write_json(queue_path, {"items": verification_queue(items)})
    return status_counts(items)


def enrich_place(
    place: dict[str, Any],
    raw_index: dict[str, dict[str, Any]],
    live: bool = False,
    mapillary_token: str | None = None,
) -> dict[str, Any]:
    tags = raw_tags(place, raw_index)
    match = match_place(place, tags)
    qid = (match or {}).get("wikidata_id")
    candidates = fetch_candidates(place, tags, qid, live, mapillary_token)
    image = choose_image({**place, "wikidata_id": qid}, candidates)
    return {**place, "wikidata_id": (match or {}).get("wikidata_id"), "image": image,
            "image_source": image["source"], "image_is_exact": image["match_status"] == "exact_place_photo"}


def fetch_candidates(place: dict[str, Any], tags: dict[str, str], qid: str | None,
                     live: bool, mapillary_token: str | None) -> dict[str, Any]:
    if not live:
        return {}
    wikidata = fetch_wikidata_candidates(qid)
    website = tags.get("website") or wikidata.get("wikidata_website")
    return {**wikidata, "official_og": tuple(filter(None, (safe_og(website),))),
            "mapillary_area": fetch_area_images(place, mapillary_token)}


def fetch_wikidata_candidates(qid: str | None) -> dict[str, Any]:
    if not qid:
        return {}
    data = fetch_p18_and_website(qid)
    p18 = ({"image": data.get("image"), "source_url": f"https://www.wikidata.org/wiki/{qid}"},) \
        if data.get("image") else ()
    return {"wikidata_p18": p18, "commons_depicts": fetch_depicts_images(qid), "wikidata_website": data.get("website")}


def safe_og(website: str | None) -> dict[str, str] | None:
    if not website:
        return None
    try:
        return fetch_og_image(website)
    except Exception:
        return None


def artifact(place: dict[str, Any]) -> dict[str, Any]:
    return {"slug": place.get("slug"), "wikidata_id": place.get("wikidata_id"), "image": place.get("image")}


def status_counts(items: tuple[dict[str, Any], ...]) -> dict[str, int]:
    return dict(map(lambda status: (status, sum(1 for item in items if item["image"]["match_status"] == status)),
                    sorted({item["image"]["match_status"] for item in items})))


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--live", action="store_true"); parser.add_argument("--mapillary-token", default=None)
    args = parser.parse_args()
    print(json.dumps(run_pipeline(live=args.live, mapillary_token=args.mapillary_token), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
