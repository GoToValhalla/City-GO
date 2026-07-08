"""Наполнение place_images кандидатами из проверяемых источников.

Скрипт не использует случайный web image search. Фото берутся только из:
- Place.image_url, если ссылка уже есть, но нет PlaceImage;
- Place.website / Place.source_url -> OpenGraph image;
- OSM image / wikimedia_commons / wikidata P18 / wikipedia / website tags;
- Wikimedia Commons search по названию места и городу;
- Openverse image search по CC/public-domain источникам как последний fallback.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city import City
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_APPROVED, PUBLIC_PLACE_IMAGE_STATUSES, PlaceImage
from models.place_source_presence import PlaceSourcePresence
from models.source_observation import SourceObservation
from services.local_persistent_cache import get_cached_text, set_cached_text, stable_cache_key
from services.place_public_image_service import place_has_public_image
from services.place_public_visibility import is_public_hidden_category

BAD_TITLE_PATTERN = re.compile(r"^(yes|no|unknown|fixme|todo|n/a)$", re.I)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
REQUEST_TIMEOUT_SECONDS = 12
# Hard wall-clock cap for one run() call. Per-request timeouts alone don't
# bound total runtime: up to 4 sequential provider calls per place (website
# OG-image, Wikimedia search, 2x Openverse queries) times up to IMAGE_LIMIT
# places could otherwise run for hours with no result written (prod: a
# Kaliningrad photo enrichment job stalled 1h41m in finding_images with no
# final diagnostics). Hitting the deadline stops scanning further places and
# writes whatever partial summary/diagnostics exist so far.
MAX_RUNTIME_SECONDS = 10 * 60
USER_AGENT = "CityGoImageEnricher/1.0"
HTTP_TEXT_CACHE_NAMESPACE = "image_enrichment_http_text_v1"
OPENVERSE_ACCEPTED_LICENSES = {"cc0", "pdm", "by", "by-sa"}
SOURCE_EVIDENCE_PROVIDERS = (
    "place.image_url",
    "place.website/open_graph",
    "place.source_url/open_graph",
    "source_observation.osm_image",
    "source_observation.wikimedia_commons",
    "source_observation.wikidata_p18",
    "source_observation.wikipedia_page_image",
    "source_observation.website_open_graph",
    "wikimedia_commons_search",
    "openverse_licensed_image_search",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-approve place image candidates from trusted source evidence.")
    parser.add_argument("--city", required=True, help="City slug, e.g. zelenogradsk")
    parser.add_argument("--limit", type=int, default=100, help="Max places to scan")
    parser.add_argument("--start-after-id", type=int, default=0, help="Only scan places with id greater than this value.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    if args.dry_run == args.apply:
        raise SystemExit("Choose exactly one of --dry-run or --apply")

    with SessionLocal() as db:
        city = db.query(City).filter(City.slug == args.city).first()
        if city is None:
            raise SystemExit(f"City not found: {args.city}")

        query = _candidate_places_query(db, city, start_after_id=int(args.start_after_id or 0))
        total_without_public_image = query.count()
        places = query.limit(args.limit).all()
        summary: dict[str, Any] = {
            "city_slug": args.city,
            "start_after_id": int(args.start_after_id or 0),
            "last_scanned_place_id": int(args.start_after_id or 0),
            "places_without_public_image_total": int(total_without_public_image),
            "scanned_places": 0,
            "candidates_found": 0,
            "created": 0,
            "auto_approved": 0,
            "place_image_url_synced": 0,
            "skipped_duplicates": 0,
            "skipped_has_approved": 0,
            "skipped_ineligible": 0,
            "skipped_no_source": 0,
            "errors": [],
            "warnings": [],
            "provider_mode": "trusted_source_evidence_plus_commons_and_openverse_search",
            "source_evidence_providers": list(SOURCE_EVIDENCE_PROVIDERS),
            "dry_run": args.dry_run,
            "preview": [],
            "deadline_exceeded": False,
        }

        deadline = time.monotonic() + MAX_RUNTIME_SECONDS
        for place in places:
            if time.monotonic() >= deadline:
                summary["deadline_exceeded"] = True
                summary["warnings"].append(f"Stopped after exceeding max runtime of {MAX_RUNTIME_SECONDS}s; scanned {summary['scanned_places']} of {len(places)} places.")
                break
            summary["scanned_places"] += 1
            summary["last_scanned_place_id"] = int(place.id)
            if not _is_eligible_place(place):
                summary["skipped_ineligible"] += 1
                continue
            if place_has_public_image(db, place.id):
                summary["skipped_has_approved"] += 1
                continue
            try:
                candidates = _collect_candidates_for_place(db, place, city)
            except Exception as exc:  # noqa: BLE001
                summary["errors"].append({"place_id": place.id, "place_title": place.title, "error": str(exc)[:500]})
                continue
            if not candidates:
                summary["skipped_no_source"] += 1
                continue
            best_candidate = candidates[0]
            summary["candidates_found"] += len(candidates)
            if _image_exists(db, place.id, best_candidate["image_url"]):
                summary["skipped_duplicates"] += 1
                continue
            preview_item = {
                "place_id": place.id,
                "place_slug": place.slug,
                "place_title": place.title,
                **best_candidate,
                "status": PLACE_IMAGE_STATUS_APPROVED,
                "is_primary": True,
                "manual_confirmation_required": True,
            }
            summary["preview"].append(preview_item)
            if args.apply:
                db.add(
                    PlaceImage(
                        place_id=place.id,
                        image_url=best_candidate["image_url"],
                        thumbnail_url=best_candidate.get("thumbnail_url"),
                        source_type=best_candidate["source_type"],
                        source_url=best_candidate.get("source_url"),
                        attribution=best_candidate.get("attribution"),
                        license=best_candidate.get("license"),
                        confidence=best_candidate.get("confidence"),
                        status=PLACE_IMAGE_STATUS_APPROVED,
                        is_primary=True,
                        reviewed_by=None,
                        reviewed_at=None,
                        review_comment="Auto-approved from source evidence/search; still requires manual confirmation.",
                    )
                )
                place.image_url = best_candidate["image_url"]
                summary["created"] += 1
                summary["auto_approved"] += 1
                summary["place_image_url_synced"] += 1
                # Commit incrementally so progress survives a kill/deadline mid-scan
                # instead of holding one long-lived open transaction for the whole run.
                db.commit()

        if summary["deadline_exceeded"]:
            summary["provider_status"] = "max_runtime_exceeded"
            summary["zero_result_reason"] = "max_runtime_exceeded"
        elif int(summary["created"] or 0) == 0 and int(summary["candidates_found"] or 0) == 0:
            summary["warnings"].append("No image candidates found from trusted sources, Wikimedia Commons, or Openverse.")
            summary["provider_status"] = "source_evidence_exhausted"
            summary["zero_result_reason"] = "source_evidence_exhausted"
        else:
            summary["provider_status"] = "candidates_found"
        if args.apply:
            db.commit()
        from services.photo_enrichment_diagnostics import attach_photo_diagnostics_to_summary

        return attach_photo_diagnostics_to_summary(db, city, summary, scan_limit=int(args.limit))


def _candidate_places_query(db: Session, city: City, *, start_after_id: int = 0):
    public_image_exists = db.query(PlaceImage.id).filter(PlaceImage.place_id == Place.id, PlaceImage.status.in_(tuple(PUBLIC_PLACE_IMAGE_STATUSES))).exists()
    return (
        db.query(Place)
        .filter(Place.city_id == city.id, Place.id > int(start_after_id or 0), Place.status == "active", ~public_image_exists)
        .order_by(Place.is_published.desc(), Place.is_visible_in_catalog.desc(), Place.tourist_eligible.desc(), Place.id.asc())
    )


def _is_eligible_place(place: Place) -> bool:
    title = (place.title or "").strip()
    if len(title) < 2 or BAD_TITLE_PATTERN.match(title):
        return False
    if is_public_hidden_category(place.category):
        return False
    if place.status != "active":
        return False
    if getattr(place, "is_spam_poi", False):
        return False
    return True


def _collect_candidates_for_place(db: Session, place: Place, city: City) -> list[dict[str, Any]]:
    candidates = _candidates_from_place_fields(place)
    for observation in _latest_observations_for_place(db, place.id):
        payload = observation.raw_payload or {}
        tags = payload.get("tags") if isinstance(payload.get("tags"), dict) else {}
        if not tags and isinstance(payload, dict):
            tags = {key: value for key, value in payload.items() if isinstance(key, str)}
        candidates.extend(_candidates_from_tags(tags, observation.source_url))
    if not candidates:
        commons_candidate = _candidate_from_wikimedia_search(place, city)
        if commons_candidate:
            candidates.append(commons_candidate)
    if not candidates:
        openverse_candidate = _candidate_from_openverse_search(place, city)
        if openverse_candidate:
            candidates.append(openverse_candidate)
    return _deduplicate_candidates(candidates)


def _candidates_from_place_fields(place: Place) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    image_url = _clean_tag(place.image_url)
    if image_url and _is_reviewable_image_url(image_url):
        candidates.append(_candidate(image_url=image_url, source_type="existing_place_image_url", source_url=place.source_url or place.website, confidence=0.88))
    source_url = _clean_tag(place.source_url)
    if source_url and _is_reviewable_image_url(source_url) and _looks_like_file_name(urllib.parse.urlparse(source_url).path):
        candidates.append(_candidate(image_url=source_url, source_type="place_source_image_url", source_url=source_url, confidence=0.82))
    website_urls: list[str] = []
    for value in (_clean_tag(place.website), source_url):
        if value and _looks_like_url(value) and value not in website_urls:
            website_urls.append(value)
    for website_url in website_urls:
        website_candidate = _candidate_from_website_og_image(website_url)
        if website_candidate:
            candidates.append(website_candidate)
    return candidates


def _latest_observations_for_place(db: Session, place_id: int) -> list[SourceObservation]:
    presence_rows = db.query(PlaceSourcePresence).filter(PlaceSourcePresence.place_id == place_id).order_by(PlaceSourcePresence.last_seen_at.desc()).limit(5).all()
    observation_ids = [row.source_observation_id for row in presence_rows if row.source_observation_id]
    if observation_ids:
        return db.query(SourceObservation).filter(SourceObservation.id.in_(observation_ids)).order_by(SourceObservation.last_seen_at.desc()).all()
    return db.query(SourceObservation).filter(SourceObservation.canonical_place_id == place_id).order_by(SourceObservation.last_seen_at.desc()).limit(5).all()


def _candidates_from_tags(tags: dict[str, Any], observation_source_url: str | None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    image_value = _clean_tag(tags.get("image"))
    if image_value and _looks_like_url(image_value):
        candidates.append(_candidate(image_url=image_value, source_type="osm_image", source_url=observation_source_url, confidence=0.92))
    commons_value = _clean_tag(tags.get("wikimedia_commons"))
    if commons_value:
        candidates.extend(_candidates_from_wikimedia_commons(commons_value))
    wikidata_value = _clean_tag(tags.get("wikidata"))
    if wikidata_value:
        wikidata_candidate = _candidate_from_wikidata(wikidata_value, observation_source_url)
        if wikidata_candidate:
            candidates.append(wikidata_candidate)
    wikipedia_value = _clean_tag(tags.get("wikipedia"))
    if wikipedia_value:
        wikipedia_candidate = _candidate_from_wikipedia(wikipedia_value)
        if wikipedia_candidate:
            candidates.append(wikipedia_candidate)
    website_value = _clean_tag(tags.get("website")) or _clean_tag(tags.get("contact:website"))
    if website_value:
        website_candidate = _candidate_from_website_og_image(website_value)
        if website_candidate:
            candidates.append(website_candidate)
    return [candidate for candidate in candidates if _is_reviewable_image_url(candidate.get("image_url"))]


def _candidates_from_wikimedia_commons(value: str) -> list[dict[str, Any]]:
    title = _normalize_commons_title(value)
    if _is_commons_file_title(title):
        return [_candidate(image_url=_wikimedia_file_url(title), source_type="wikimedia_commons", source_url=_wikimedia_page_url(title), attribution="Wikimedia Commons contributors", confidence=0.90)]
    if title.startswith("Category:"):
        category_candidate = _candidate_from_wikimedia_category(title)
        if category_candidate:
            return [category_candidate]
    return []


def _candidate_from_wikidata(qid: str, observation_source_url: str | None) -> dict[str, Any] | None:
    if not re.fullmatch(r"Q\d+", qid.strip(), re.I):
        return None
    qid = qid.strip().upper()
    data = _fetch_json(f"https://www.wikidata.org/wiki/Special:EntityData/{urllib.parse.quote(qid)}.json")
    if not data:
        return None
    try:
        entity = data["entities"][qid]
        p18_claims = (entity.get("claims") or {}).get("P18") or []
        filename = ((p18_claims[0].get("mainsnak") or {}).get("datavalue") or {}).get("value")
    except (KeyError, TypeError, IndexError):
        return None
    if not isinstance(filename, str) or not filename.strip():
        return None
    return _candidate(image_url=_wikimedia_file_url(filename), source_type="wikidata_p18", source_url=observation_source_url or f"https://www.wikidata.org/wiki/{qid}", attribution="Wikimedia Commons contributors", confidence=0.95)


def _candidate_from_wikipedia(value: str) -> dict[str, Any] | None:
    article_url = _wikipedia_article_url(value)
    parsed = urllib.parse.urlparse(article_url)
    if not parsed.netloc.endswith("wikipedia.org"):
        return None
    lang = parsed.netloc.split(".")[0]
    title = urllib.parse.unquote(parsed.path.removeprefix("/wiki/"))
    if not lang or not title:
        return None
    data = _fetch_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}")
    if not data:
        return None
    original = data.get("originalimage")
    thumbnail = data.get("thumbnail")
    image_url = original.get("source") if isinstance(original, dict) else None
    if not image_url and isinstance(thumbnail, dict):
        image_url = thumbnail.get("source")
    if not isinstance(image_url, str) or not image_url.strip():
        return None
    return _candidate(image_url=image_url, source_type="wikipedia_page_image", source_url=article_url, attribution="Wikipedia contributors", confidence=0.85)


def _candidate_from_wikimedia_category(category_title: str) -> dict[str, Any] | None:
    params = {"action": "query", "generator": "categorymembers", "gcmtitle": category_title, "gcmtype": "file", "gcmlimit": "1", "prop": "imageinfo", "iiprop": "url", "format": "json", "formatversion": "2"}
    data = _fetch_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    pages = ((data or {}).get("query") or {}).get("pages") if isinstance((data or {}).get("query"), dict) else None
    if not isinstance(pages, list) or not pages:
        return None
    imageinfo = pages[0].get("imageinfo") if isinstance(pages[0], dict) else None
    if not isinstance(imageinfo, list) or not imageinfo:
        return None
    image_url = imageinfo[0].get("url")
    if not isinstance(image_url, str):
        return None
    return _candidate(image_url=image_url, source_type="wikimedia_commons_category", source_url=_wikimedia_page_url(category_title), attribution="Wikimedia Commons contributors", confidence=0.82)


def _candidate_from_wikimedia_search(place: Place, city: City) -> dict[str, Any] | None:
    title = (place.title or "").strip()
    city_name = (city.name or city.slug or "").strip()
    if not title or len(title) < 3 or BAD_TITLE_PATTERN.match(title):
        return None
    search_query = f"{title} {city_name}".strip()
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": search_query,
        "gsrnamespace": "6",
        "gsrlimit": "3",
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json",
        "formatversion": "2",
    }
    data = _fetch_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    pages = ((data or {}).get("query") or {}).get("pages") if isinstance((data or {}).get("query"), dict) else None
    if not isinstance(pages, list):
        return None
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_title = str(page.get("title") or "")
        imageinfo = page.get("imageinfo")
        if not isinstance(imageinfo, list) or not imageinfo:
            continue
        info = imageinfo[0]
        if not isinstance(info, dict):
            continue
        image_url = info.get("url")
        mime = str(info.get("mime") or "")
        if not isinstance(image_url, str) or not _is_reviewable_image_url(image_url):
            continue
        if mime and not mime.startswith("image/"):
            continue
        return _candidate(
            image_url=image_url,
            source_type="wikimedia_commons_search",
            source_url=_wikimedia_page_url(page_title),
            attribution="Wikimedia Commons contributors",
            confidence=0.68,
        )
    return None


def _candidate_from_openverse_search(place: Place, city: City) -> dict[str, Any] | None:
    title = (place.title or "").strip()
    city_name = (city.name or city.slug or "").strip()
    if not title or len(title) < 3 or BAD_TITLE_PATTERN.match(title):
        return None
    queries = [f"{title} {city_name}".strip(), title]
    for query in queries:
        params = {
            "q": query,
            "page_size": "3",
            "license": "cc0,pdm,by,by-sa",
        }
        data = _fetch_json("https://api.openverse.engineering/v1/images/?" + urllib.parse.urlencode(params))
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            continue
        for item in results:
            if not isinstance(item, dict):
                continue
            image_url = item.get("url")
            if not isinstance(image_url, str) or not _is_reviewable_image_url(image_url):
                continue
            license_code = str(item.get("license") or "").lower().strip()
            if license_code and license_code not in OPENVERSE_ACCEPTED_LICENSES:
                continue
            source_url = item.get("foreign_landing_url") if isinstance(item.get("foreign_landing_url"), str) else None
            creator = item.get("creator") if isinstance(item.get("creator"), str) else None
            provider = item.get("source") if isinstance(item.get("source"), str) else "Openverse"
            attribution = creator or f"{provider} via Openverse"
            license_label = license_code.upper() if license_code else None
            return _candidate(
                image_url=image_url,
                source_type="openverse_licensed_image_search",
                source_url=source_url,
                attribution=attribution,
                license=license_label,
                confidence=0.56,
            )
    return None


def _candidate_from_website_og_image(website_url: str) -> dict[str, Any] | None:
    if not _looks_like_url(website_url):
        return None
    html_text = _fetch_text(website_url)
    if not html_text:
        return None
    image_url = _extract_og_image(html_text)
    if not image_url:
        return None
    image_url = urllib.parse.urljoin(website_url, image_url)
    if not _looks_like_url(image_url):
        return None
    return _candidate(image_url=image_url, source_type="official_website_og_image", source_url=website_url, confidence=0.72)


def _extract_og_image(html_text: str) -> str | None:
    patterns = (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, html_text, re.I)
        if match:
            return html.unescape(match.group(1).strip())
    return None


def _candidate(*, image_url: str, source_type: str, source_url: str | None, confidence: float, attribution: str | None = None, license: str | None = None) -> dict[str, Any]:
    return {"image_url": image_url, "thumbnail_url": None, "source_type": source_type, "source_url": source_url, "attribution": attribution, "license": license, "confidence": confidence}


def _deduplicate_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in sorted(candidates, key=lambda item: float(item.get("confidence") or 0), reverse=True):
        image_url = str(candidate.get("image_url") or "").strip()
        if image_url and image_url not in seen:
            seen.add(image_url)
            result.append(candidate)
    return result


def _clean_tag(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _looks_like_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _normalize_commons_title(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        parsed = urllib.parse.urlparse(cleaned)
        if "/wiki/" in parsed.path:
            cleaned = urllib.parse.unquote(parsed.path.split("/wiki/", 1)[1])
    cleaned = cleaned.replace("_", " ").strip()
    if cleaned.lower().startswith("commons:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    if not cleaned.startswith(("File:", "Category:")) and _looks_like_file_name(cleaned):
        cleaned = f"File:{cleaned}"
    return cleaned


def _is_commons_file_title(value: str) -> bool:
    return value.startswith("File:") or _looks_like_file_name(value)


def _looks_like_file_name(value: str) -> bool:
    return value.lower().endswith(IMAGE_EXTENSIONS)


def _wikimedia_file_url(value: str) -> str:
    filename = value.removeprefix("File:").strip()
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(filename)}"


def _wikimedia_page_url(value: str) -> str:
    title = value
    if not title.startswith(("File:", "Category:")) and _looks_like_file_name(title):
        title = f"File:{title}"
    return f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'), safe=':/')}"


def _is_reviewable_image_url(value: Any) -> bool:
    if not isinstance(value, str) or not _looks_like_url(value):
        return False
    return bool(urllib.parse.urlparse(value).netloc)


def _image_exists(db: Session, place_id: int, image_url: str) -> bool:
    return db.query(PlaceImage.id).filter(PlaceImage.place_id == place_id, PlaceImage.image_url == image_url).first() is not None


def _fetch_json(url: str) -> dict[str, Any] | None:
    text = _fetch_text(url)
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _fetch_text(url: str) -> str | None:
    cache_key = stable_cache_key(HTTP_TEXT_CACHE_NAMESPACE, url)
    found, cached = get_cached_text(cache_key)
    if found and cached is not None:
        return cached
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text" not in content_type and "json" not in content_type and "html" not in content_type:
                return None
            raw = response.read()
    except Exception:
        return None
    text = raw.decode("utf-8", errors="ignore")
    set_cached_text(cache_key, text, expire=7 * 24 * 60 * 60, tag="provider:image_enrichment")
    return text


def _wikipedia_article_url(value: str) -> str:
    value = value.strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if ":" in value:
        lang, title = value.split(":", 1)
        return f"https://{(lang.strip() or 'ru')}.wikipedia.org/wiki/{urllib.parse.quote(title.strip().replace(' ', '_'))}"
    return f"https://ru.wikipedia.org/wiki/{urllib.parse.quote(value.replace(' ', '_'))}"


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
