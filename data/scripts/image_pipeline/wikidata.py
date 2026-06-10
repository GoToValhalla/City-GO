from __future__ import annotations

import re
from typing import Any

from data.scripts.image_pipeline.http_client import get_json

SPARQL_URL = "https://query.wikidata.org/sparql"
QID_RE = re.compile(r"Q\d+")


def direct_qid(tags: dict[str, str]) -> str | None:
    value = tags.get("wikidata") or ""
    match = QID_RE.search(value)
    return match.group(0) if match else None


def wikipedia_title(tags: dict[str, str]) -> str | None:
    value = tags.get("wikipedia") or ""
    return value.split(":", 1)[1] if ":" in value else None


def match_place(place: dict[str, Any], tags: dict[str, str]) -> dict[str, Any] | None:
    qid = direct_qid(tags)
    if qid:
        return build_match(place, qid, "osm_wikidata_tag", "high")
    title = wikipedia_title(tags)
    if title:
        return {**build_match(place, "", "osm_wikipedia_tag", "high"), "wikipedia_title": title}
    return None


def build_match(place: dict[str, Any], qid: str, method: str, confidence: str) -> dict[str, Any]:
    return {"slug": place["slug"], "wikidata_id": qid, "method": method, "confidence": confidence}


def p18_query(qid: str) -> str:
    return f"SELECT ?image ?website WHERE {{ OPTIONAL {{ wd:{qid} wdt:P18 ?image. }} OPTIONAL {{ wd:{qid} wdt:P856 ?website. }} }}"


def fetch_p18_and_website(qid: str) -> dict[str, str | None]:
    data = get_json(SPARQL_URL, {"query": p18_query(qid), "format": "json"})
    bindings = data.get("results", {}).get("bindings", [{}])
    first = bindings[0] if bindings else {}
    return {"image": binding_value(first, "image"), "website": binding_value(first, "website")}


def binding_value(binding: dict[str, Any], key: str) -> str | None:
    value = binding.get(key, {})
    return value.get("value") if isinstance(value, dict) else None
