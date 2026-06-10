"""
City Go — бесплатный preview-парсер обогащения мест.

Назначение:
  Быстро проверить, можно ли без платных API и без записи в БД найти для мест:
  - адрес;
  - сайт;
  - телефон;
  - часы работы;
  - фото-кандидат.

Источники первой версии:
  - входной CSV/JSON;
  - OSM/Nominatim search/reverse;
  - OSM extra tags: website, phone, opening_hours, image, wikidata, wikipedia;
  - Wikidata P18 image;
  - Wikipedia summary thumbnail;
  - официальный сайт: og:image.

Важно:
  Скрипт ничего не пишет в БД и ничего не применяет автоматически.
  На выходе только preview CSV/JSON для ручной оценки качества.

Примеры:
  python data/scripts/place_web_enrichment_probe.py \
    --input data/exports/place_enrichment/active/place_enrichment_алматы_20260608_204651/export.csv \
    --output-dir data/exports/place_web_enrichment_probe/almaty_50 \
    --limit 50

  python data/scripts/place_web_enrichment_probe.py \
    --input places.json \
    --output-dir data/exports/place_web_enrichment_probe/manual_20 \
    --limit 20 \
    --sleep 1.1
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

DEFAULT_USER_AGENT = os.getenv(
    "CITYGO_CRAWLER_USER_AGENT",
    "CityGoBot/0.1 place-web-enrichment-probe (contact: set CITYGO_CRAWLER_USER_AGENT)",
)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
WIKIPEDIA_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"

IMAGE_BAD_WORDS = (
    "logo",
    "icon",
    "avatar",
    "banner",
    "header",
    "sprite",
    "favicon",
    "placeholder",
    "default",
)

WEBSITE_KEYS = ("website", "contact:website", "url", "contact:url")
PHONE_KEYS = ("phone", "contact:phone", "mobile", "contact:mobile")
HOURS_KEYS = ("opening_hours", "opening-hours")
IMAGE_KEYS = ("image", "wikimedia_commons")
WIKIDATA_KEYS = ("wikidata", "brand:wikidata", "operator:wikidata")
WIKIPEDIA_KEYS = ("wikipedia", "brand:wikipedia", "operator:wikipedia")


@dataclass
class SourceHit:
    source: str
    source_url: str | None = None
    confidence: float = 0.0
    reason: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaceInput:
    place_id: str
    title: str
    city: str
    category: str | None = None
    lat: float | None = None
    lng: float | None = None
    current_address: str | None = None
    current_website: str | None = None
    current_phone: str | None = None
    current_opening_hours: str | None = None
    current_image_url: str | None = None
    source_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProbeResult:
    input_place_id: str
    input_title: str
    input_city: str
    input_category: str | None
    current_address: str | None
    current_image_url: str | None
    suggested_address: str | None = None
    suggested_website: str | None = None
    suggested_phone: str | None = None
    suggested_opening_hours: str | None = None
    suggested_image_url: str | None = None
    image_match_status: str | None = None
    suggested_data_source: str | None = None
    suggested_source_url: str | None = None
    suggested_confidence: float = 0.0
    suggested_comment: str = ""
    rejection_reason: str = ""
    debug_sources: list[dict[str, Any]] = field(default_factory=list)


class OpenGraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self._in_title = False
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True
            return
        if tag.lower() != "meta":
            return
        attr = {k.lower(): (v or "") for k, v in attrs}
        key = attr.get("property") or attr.get("name")
        content = attr.get("content")
        if key and content:
            self.meta[key.lower()] = content.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and data.strip():
            self.title = (self.title or "") + data.strip()


def _http_get_json(url: str, *, timeout: int = 12) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def _http_get_text(url: str, *, timeout: int = 12) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace"), content_type


def _safe_get_json(url: str) -> tuple[Any | None, str | None]:
    try:
        return _http_get_json(url), None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _safe_get_text(url: str) -> tuple[str | None, str | None, str | None]:
    try:
        text, content_type = _http_get_text(url)
        return text, content_type, None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def _normalise_url(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    if value.startswith("//"):
        return "https:" + value
    if not re.match(r"^https?://", value, re.I):
        return "https://" + value
    return value


def _first_non_empty(mapping: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_raw_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _address_from_nominatim(result: dict[str, Any]) -> str | None:
    address = result.get("address") or {}
    if not isinstance(address, dict):
        return result.get("display_name")
    road = address.get("road") or address.get("pedestrian") or address.get("footway") or address.get("street")
    house = address.get("house_number")
    city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality")
    parts: list[str] = []
    street = " ".join(str(x) for x in (road, house) if x)
    if street:
        parts.append(street)
    if city and city not in parts:
        parts.append(str(city))
    if parts:
        return ", ".join(parts)
    return result.get("display_name")


def _is_probably_bad_image_url(url: str | None) -> bool:
    if not url:
        return True
    lowered = url.lower()
    if any(word in lowered for word in IMAGE_BAD_WORDS):
        return True
    if lowered.endswith((".svg", ".ico")):
        return True
    return False


def _string_similarity(a: str, b: str) -> float:
    """Cheap token overlap similarity without external dependencies."""
    a_tokens = {t for t in re.split(r"\W+", a.lower()) if len(t) >= 3}
    b_tokens = {t for t in re.split(r"\W+", b.lower()) if len(t) >= 3}
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))


def _valid_site_for_place(place: PlaceInput, page_title: str | None, html: str, website: str) -> tuple[bool, str]:
    city_ok = not place.city or place.city.lower() in html.lower()
    title_text = " ".join([page_title or "", urllib.parse.urlparse(website).netloc])
    name_score = _string_similarity(place.title, title_text)
    if name_score >= 0.45:
        return True, f"site title/domain matches place name ({name_score:.2f})"
    if city_ok and name_score >= 0.2:
        return True, f"site mentions city and partially matches name ({name_score:.2f})"
    return False, f"weak site match: name_score={name_score:.2f}, city_mentioned={city_ok}"


def load_places(input_path: Path, limit: int | None = None) -> list[PlaceInput]:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        rows = raw if isinstance(raw, list) else raw.get("places", [])
    else:
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

    places: list[PlaceInput] = []
    for row in rows[: limit or None]:
        if not isinstance(row, dict):
            continue
        raw_tags = _parse_raw_json(row.get("raw_osm_tags"))
        title = row.get("title") or row.get("name") or row.get("place_name") or ""
        city = row.get("city_name") or row.get("city") or row.get("city_slug") or ""
        place_id = str(row.get("id") or row.get("place_id") or row.get("input_place_id") or len(places) + 1)
        places.append(
            PlaceInput(
                place_id=place_id,
                title=str(title).strip(),
                city=str(city).strip(),
                category=(row.get("category") or row.get("place_category") or None),
                lat=_parse_float(row.get("lat")),
                lng=_parse_float(row.get("lng")),
                current_address=(row.get("current_address") or row.get("address") or None),
                current_website=_normalise_url(row.get("current_website") or row.get("website")),
                current_phone=(row.get("current_phone") or row.get("phone") or None),
                current_opening_hours=(row.get("current_opening_hours") or row.get("opening_hours") or None),
                current_image_url=(row.get("current_image_url") or row.get("image_url") or None),
                source_url=(row.get("source_url") or None),
                raw={**row, "raw_osm_tags_parsed": raw_tags},
            )
        )
    return places


def search_nominatim(place: PlaceInput) -> SourceHit:
    query = f"{place.title}, {place.city}".strip(", ")
    params = {
        "q": query,
        "format": "json",
        "addressdetails": "1",
        "extratags": "1",
        "limit": "1",
    }
    url = NOMINATIM_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    data, error = _safe_get_json(url)
    if error:
        return SourceHit("nominatim_search", url, 0.0, error)
    if not data:
        return SourceHit("nominatim_search", url, 0.0, "not_found")
    item = data[0]
    extratags = item.get("extratags") or {}
    if not isinstance(extratags, dict):
        extratags = {}
    return SourceHit(
        source="nominatim_search",
        source_url=f"https://www.openstreetmap.org/{item.get('osm_type')}/{item.get('osm_id')}",
        confidence=0.75,
        reason="found_by_text_search",
        data={
            "address": _address_from_nominatim(item),
            "website": _normalise_url(_first_non_empty(extratags, WEBSITE_KEYS)),
            "phone": _first_non_empty(extratags, PHONE_KEYS),
            "opening_hours": _first_non_empty(extratags, HOURS_KEYS),
            "image_url": _normalise_url(_first_non_empty(extratags, IMAGE_KEYS)),
            "wikidata": _first_non_empty(extratags, WIKIDATA_KEYS),
            "wikipedia": _first_non_empty(extratags, WIKIPEDIA_KEYS),
            "raw": item,
        },
    )


def reverse_nominatim(place: PlaceInput) -> SourceHit:
    if place.lat is None or place.lng is None:
        return SourceHit("nominatim_reverse", None, 0.0, "missing_coordinates")
    params = {
        "lat": str(place.lat),
        "lon": str(place.lng),
        "format": "json",
        "addressdetails": "1",
        "extratags": "1",
        "zoom": "18",
    }
    url = NOMINATIM_REVERSE_URL + "?" + urllib.parse.urlencode(params)
    item, error = _safe_get_json(url)
    if error:
        return SourceHit("nominatim_reverse", url, 0.0, error)
    if not item or item.get("error"):
        return SourceHit("nominatim_reverse", url, 0.0, item.get("error", "not_found") if isinstance(item, dict) else "not_found")
    extratags = item.get("extratags") or {}
    if not isinstance(extratags, dict):
        extratags = {}
    return SourceHit(
        source="nominatim_reverse",
        source_url=f"https://www.openstreetmap.org/{item.get('osm_type')}/{item.get('osm_id')}",
        confidence=0.65,
        reason="found_by_reverse_geocoding",
        data={
            "address": _address_from_nominatim(item),
            "website": _normalise_url(_first_non_empty(extratags, WEBSITE_KEYS)),
            "phone": _first_non_empty(extratags, PHONE_KEYS),
            "opening_hours": _first_non_empty(extratags, HOURS_KEYS),
            "image_url": _normalise_url(_first_non_empty(extratags, IMAGE_KEYS)),
            "wikidata": _first_non_empty(extratags, WIKIDATA_KEYS),
            "wikipedia": _first_non_empty(extratags, WIKIPEDIA_KEYS),
            "raw": item,
        },
    )


def wikidata_image(qid: str | None) -> SourceHit:
    if not qid or not re.match(r"^Q\d+$", qid.strip(), re.I):
        return SourceHit("wikidata", None, 0.0, "missing_wikidata_qid")
    qid = qid.strip().upper()
    url = WIKIDATA_ENTITY_URL.format(qid=qid)
    data, error = _safe_get_json(url)
    if error:
        return SourceHit("wikidata", url, 0.0, error)
    try:
        entity = data["entities"][qid]
        claims = entity.get("claims", {})
        p18 = claims.get("P18", [])
        if not p18:
            return SourceHit("wikidata", url, 0.0, "p18_not_found")
        filename = p18[0]["mainsnak"]["datavalue"]["value"]
        commons_name = str(filename).replace(" ", "_")
        image_url = "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + urllib.parse.quote(commons_name)
        return SourceHit(
            "wikidata",
            url,
            0.9,
            "wikidata_p18_image",
            {"image_url": image_url, "wikidata": qid},
        )
    except (KeyError, IndexError, TypeError) as exc:
        return SourceHit("wikidata", url, 0.0, f"parse_error: {exc}")


def wikipedia_summary(wikipedia_tag: str | None) -> SourceHit:
    if not wikipedia_tag:
        return SourceHit("wikipedia", None, 0.0, "missing_wikipedia_tag")
    if ":" in wikipedia_tag:
        lang, title = wikipedia_tag.split(":", 1)
    else:
        lang, title = "ru", wikipedia_tag
    lang = lang.strip() or "ru"
    title = title.strip().replace(" ", "_")
    if not title:
        return SourceHit("wikipedia", None, 0.0, "empty_title")
    url = WIKIPEDIA_SUMMARY_URL.format(lang=urllib.parse.quote(lang), title=urllib.parse.quote(title))
    data, error = _safe_get_json(url)
    if error:
        return SourceHit("wikipedia", url, 0.0, error)
    image_url = (data.get("thumbnail") or {}).get("source") if isinstance(data, dict) else None
    extract = data.get("extract") if isinstance(data, dict) else None
    if not image_url and not extract:
        return SourceHit("wikipedia", url, 0.0, "no_summary_data")
    return SourceHit(
        "wikipedia",
        url,
        0.8 if image_url else 0.55,
        "wikipedia_summary",
        {"image_url": image_url, "description": extract},
    )


def site_open_graph(place: PlaceInput, website: str | None) -> SourceHit:
    website = _normalise_url(website)
    if not website:
        return SourceHit("official_site", None, 0.0, "missing_website")
    html, content_type, error = _safe_get_text(website)
    if error:
        return SourceHit("official_site", website, 0.0, error)
    if content_type and "html" not in content_type.lower():
        return SourceHit("official_site", website, 0.0, f"non_html_content_type={content_type}")
    parser = OpenGraphParser()
    try:
        parser.feed(html or "")
    except Exception as exc:  # HTMLParser is tolerant, but keep preview safe.
        return SourceHit("official_site", website, 0.0, f"html_parse_error: {exc}")
    site_ok, site_reason = _valid_site_for_place(place, parser.title, html or "", website)
    if not site_ok:
        return SourceHit("official_site", website, 0.2, site_reason, {"page_title": parser.title})
    og_image = _normalise_url(parser.meta.get("og:image") or parser.meta.get("twitter:image"))
    if og_image:
        og_image = urllib.parse.urljoin(website, og_image)
    if _is_probably_bad_image_url(og_image):
        return SourceHit(
            "official_site",
            website,
            0.45,
            f"site_matched_but_image_rejected: {site_reason}",
            {"page_title": parser.title, "image_url": og_image},
        )
    return SourceHit(
        "official_site",
        website,
        0.7,
        f"og_image_found: {site_reason}",
        {"page_title": parser.title, "image_url": og_image},
    )


def _raw_tag(place: PlaceInput, keys: Iterable[str]) -> str | None:
    raw_tags = place.raw.get("raw_osm_tags_parsed") or {}
    if isinstance(raw_tags, dict):
        return _first_non_empty(raw_tags, keys)
    return None


def enrich_one(place: PlaceInput, *, sleep_seconds: float) -> ProbeResult:
    result = ProbeResult(
        input_place_id=place.place_id,
        input_title=place.title,
        input_city=place.city,
        input_category=place.category,
        current_address=place.current_address,
        current_image_url=place.current_image_url,
    )

    # Existing input data may already contain useful raw tags.
    raw_website = _normalise_url(_raw_tag(place, WEBSITE_KEYS) or place.current_website)
    raw_phone = _raw_tag(place, PHONE_KEYS) or place.current_phone
    raw_hours = _raw_tag(place, HOURS_KEYS) or place.current_opening_hours
    raw_image = _normalise_url(_raw_tag(place, IMAGE_KEYS) or place.current_image_url)
    raw_wikidata = _raw_tag(place, WIKIDATA_KEYS)
    raw_wikipedia = _raw_tag(place, WIKIPEDIA_KEYS)

    if raw_website:
        result.suggested_website = raw_website
    if raw_phone:
        result.suggested_phone = raw_phone
    if raw_hours:
        result.suggested_opening_hours = raw_hours
    if raw_image and not _is_probably_bad_image_url(raw_image):
        result.suggested_image_url = raw_image
        result.image_match_status = "osm_image"
        result.suggested_data_source = "osm_raw_tags"
        result.suggested_confidence = 0.8
        result.suggested_comment = "image from raw OSM tags"

    nominatim_hit = search_nominatim(place)
    result.debug_sources.append(asdict(nominatim_hit))
    time.sleep(sleep_seconds)

    reverse_hit = SourceHit("nominatim_reverse", None, 0.0, "skipped")
    if not nominatim_hit.data.get("address") and place.lat is not None and place.lng is not None:
        reverse_hit = reverse_nominatim(place)
        result.debug_sources.append(asdict(reverse_hit))
        time.sleep(sleep_seconds)

    for hit in (nominatim_hit, reverse_hit):
        data = hit.data or {}
        if not result.suggested_address and data.get("address"):
            result.suggested_address = data["address"]
            result.suggested_source_url = hit.source_url
            result.suggested_data_source = hit.source
            result.suggested_confidence = max(result.suggested_confidence, hit.confidence)
        if not result.suggested_website and data.get("website"):
            result.suggested_website = data["website"]
        if not result.suggested_phone and data.get("phone"):
            result.suggested_phone = data["phone"]
        if not result.suggested_opening_hours and data.get("opening_hours"):
            result.suggested_opening_hours = data["opening_hours"]
        if not result.suggested_image_url and data.get("image_url") and not _is_probably_bad_image_url(data.get("image_url")):
            result.suggested_image_url = data["image_url"]
            result.image_match_status = "osm_image"
            result.suggested_data_source = hit.source
            result.suggested_source_url = hit.source_url
            result.suggested_confidence = max(result.suggested_confidence, 0.8)
        raw_wikidata = raw_wikidata or data.get("wikidata")
        raw_wikipedia = raw_wikipedia or data.get("wikipedia")

    if not result.suggested_image_url and raw_wikidata:
        wikidata_hit = wikidata_image(raw_wikidata)
        result.debug_sources.append(asdict(wikidata_hit))
        if wikidata_hit.data.get("image_url"):
            result.suggested_image_url = wikidata_hit.data["image_url"]
            result.image_match_status = "wikidata_p18"
            result.suggested_data_source = "wikidata"
            result.suggested_source_url = wikidata_hit.source_url
            result.suggested_confidence = max(result.suggested_confidence, wikidata_hit.confidence)

    if not result.suggested_image_url and raw_wikipedia:
        wikipedia_hit = wikipedia_summary(raw_wikipedia)
        result.debug_sources.append(asdict(wikipedia_hit))
        if wikipedia_hit.data.get("image_url"):
            result.suggested_image_url = wikipedia_hit.data["image_url"]
            result.image_match_status = "wikipedia_thumbnail"
            result.suggested_data_source = "wikipedia"
            result.suggested_source_url = wikipedia_hit.source_url
            result.suggested_confidence = max(result.suggested_confidence, wikipedia_hit.confidence)

    if result.suggested_website and not result.suggested_image_url:
        site_hit = site_open_graph(place, result.suggested_website)
        result.debug_sources.append(asdict(site_hit))
        if site_hit.data.get("image_url") and site_hit.confidence >= 0.6:
            result.suggested_image_url = site_hit.data["image_url"]
            result.image_match_status = "site_og_image"
            result.suggested_data_source = "official_site"
            result.suggested_source_url = site_hit.source_url
            result.suggested_confidence = max(result.suggested_confidence, site_hit.confidence)

    if not result.suggested_image_url:
        category = (place.category or "unknown").lower()
        result.suggested_image_url = f"/static/placeholders/{category}.svg"
        result.image_match_status = "category_placeholder"
        if not result.suggested_data_source:
            result.suggested_data_source = "category_placeholder"
        result.suggested_comment = (result.suggested_comment + "; " if result.suggested_comment else "") + "no exact/area image found; placeholder suggested"

    if not result.suggested_address and not result.suggested_image_url:
        result.rejection_reason = "no_address_no_image"
    elif not result.suggested_address:
        result.rejection_reason = "address_not_found"
    elif result.image_match_status == "category_placeholder":
        result.rejection_reason = "real_image_not_found"

    if not result.suggested_comment:
        result.suggested_comment = "preview candidate; manual review required before apply"
    return result


def write_outputs(results: list[ProbeResult], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "preview.json"
    csv_path = output_dir / "preview.csv"
    summary_path = output_dir / "summary.json"

    json_path.write_text(
        json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "input_place_id",
        "input_title",
        "input_city",
        "input_category",
        "current_address",
        "current_image_url",
        "suggested_address",
        "suggested_website",
        "suggested_phone",
        "suggested_opening_hours",
        "suggested_image_url",
        "image_match_status",
        "suggested_data_source",
        "suggested_source_url",
        "suggested_confidence",
        "suggested_comment",
        "rejection_reason",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            data = asdict(item)
            writer.writerow({key: data.get(key) for key in fieldnames})

    total = len(results)
    with_address = sum(1 for item in results if item.suggested_address)
    with_real_image = sum(1 for item in results if item.image_match_status != "category_placeholder")
    with_site = sum(1 for item in results if item.suggested_website)
    by_image_status: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for item in results:
        by_image_status[item.image_match_status or "none"] = by_image_status.get(item.image_match_status or "none", 0) + 1
        by_source[item.suggested_data_source or "none"] = by_source.get(item.suggested_data_source or "none", 0) + 1

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "with_suggested_address": with_address,
        "with_suggested_address_pct": round(with_address / total * 100, 2) if total else 0,
        "with_real_image": with_real_image,
        "with_real_image_pct": round(with_real_image / total * 100, 2) if total else 0,
        "with_website": with_site,
        "with_website_pct": round(with_site / total * 100, 2) if total else 0,
        "by_image_match_status": by_image_status,
        "by_suggested_data_source": by_source,
        "notes": [
            "This is preview only. Nothing was applied to database.",
            "category_placeholder is not a real place photo.",
            "Review source URLs and image relevance before applying results.",
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview web enrichment for City Go places without DB writes")
    parser.add_argument("--input", required=True, help="Input CSV/JSON with places")
    parser.add_argument("--output-dir", required=True, help="Directory for preview.csv/preview.json/summary.json")
    parser.add_argument("--limit", type=int, default=50, help="Max places to process")
    parser.add_argument("--sleep", type=float, default=1.1, help="Delay between Nominatim requests")
    return parser.parse_args()


def main() -> None:
    args = build_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    places = load_places(input_path, limit=args.limit)
    results: list[ProbeResult] = []
    for index, place in enumerate(places, start=1):
        print(f"[{index}/{len(places)}] {place.title} — {place.city}")
        results.append(enrich_one(place, sleep_seconds=args.sleep))
    write_outputs(results, output_dir)
    print(f"\nDone. Output: {output_dir}")
    print(f"- {output_dir / 'preview.csv'}")
    print(f"- {output_dir / 'preview.json'}")
    print(f"- {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
