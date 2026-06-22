"""
Наполнение place_images кандидатами из OSM/source_observations.

Скрипт не использует случайный web image search.
Фото берутся только из source evidence:
- OSM image
- OSM wikimedia_commons
- OSM wikidata -> Wikidata P18 image
- OSM wikipedia -> Wikipedia lead image
- OSM website/contact:website -> OpenGraph image

Новые записи сразу публикуются как approved, чтобы фото появлялись в каталоге.
При этом reviewed_at остаётся пустым: такие фото остаются в очереди ручного подтверждения.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city import City
from models.place import Place
from models.place_image import (
    PLACE_IMAGE_STATUS_APPROVED,
    PUBLIC_PLACE_IMAGE_STATUSES,
    PlaceImage,
)
from models.place_source_presence import PlaceSourcePresence
from models.source_observation import SourceObservation
from services.local_persistent_cache import get_cached_text, set_cached_text, stable_cache_key
from services.place_public_image_service import place_has_public_image
from services.place_public_visibility import is_public_hidden_category

BAD_TITLE_PATTERN = re.compile(r"^(yes|no|unknown|fixme|todo|n/a)$", re.I)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = "CityGoImageEnricher/1.0"
HTTP_TEXT_CACHE_NAMESPACE = "image_enrichment_http_text_v1"


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

        places = (
            _candidate_places_query(db, city, start_after_id=int(args.start_after_id or 0))
            .limit(args.limit)
            .all()
        )

        summary: dict[str, Any] = {
            "city_slug": args.city,
            "start_after_id": int(args.start_after_id or 0),
            "last_scanned_place_id": int(args.start_after_id or 0),
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
            "dry_run": args.dry_run,
            "preview": [],
        }

        for place in places:
            summary["scanned_places"] += 1
            summary["last_scanned_place_id"] = int(place.id)

            if not _is_eligible_place(place):
                summary["skipped_ineligible"] += 1
                continue

            if place_has_public_image(db, place.id):
                summary["skipped_has_approved"] += 1
                continue

            try:
                candidates = _collect_candidates_for_place(db, place)
            except Exception as exc:
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
                        review_comment="Auto-approved from source evidence; still requires manual confirmation.",
                    )
                )
                place.image_url = best_candidate["image_url"]
                summary["created"] += 1
                summary["auto_approved"] += 1
                summary["place_image_url_synced"] += 1

        if args.apply:
            db.commit()

        return summary


def _candidate_places_query(db: Session, city: City, *, start_after_id: int = 0):
    public_image_exists = (
        db.query(PlaceImage.id)
        .filter(
            PlaceImage.place_id == Place.id,
            PlaceImage.status.in_(tuple(PUBLIC_PLACE_IMAGE_STATUSES)),
        )
        .exists()
    )
    return (
        db.query(Place)
        .filter(
            Place.city_id == city.id,
            Place.id > int(start_after_id or 0),
            Place.is_active.is_(True),
            Place.status == "active",
            ~public_image_exists,
        )
        .order_by(Place.id.asc())
    )


def _is_eligible_place(place: Place) -> bool:
    title = (place.title or "").strip()
    if len(title) < 2 or BAD_TITLE_PATTERN.match(title):
        return False
    if is_public_hidden_category(place.category):
        return False
    if place.status != "active" or not place.is_active:
        return False
    return True


def _collect_candidates_for_place(db: Session, place: Place) -> list[dict[str, Any]]:
    observations = _latest_observations_for_place(db, place.id)
    candidates: list[dict[str, Any]] = []

    for observation in observations:
        payload = observation.raw_payload or {}
        tags = payload.get("tags") if isinstance(payload.get("tags"), dict) else {}
        if not tags and isinstance(payload, dict):
            tags = {key: value for key, value in payload.items() if isinstance(key, str)}

        candidates.extend(_candidates_from_tags(tags, observation.source_url))

    return _deduplicate_candidates(candidates)


def _latest_observations_for_place(db: Session, place_id: int) -> list[SourceObservation]:
    presence_rows = (
        db.query(PlaceSourcePresence)
        .filter(PlaceSourcePresence.place_id == place_id)
        .order_by(PlaceSourcePresence.last_seen_at.desc())
        .limit(5)
        .all()
    )

    observation_ids = [row.source_observation_id for row in presence_rows if row.source_observation_id]
    if observation_ids:
        return (
            db.query(SourceObservation)
            .filter(SourceObservation.id.in_(observation_ids))
            .order_by(SourceObservation.last_seen_at.desc())
            .all()
        )

    return (
        db.query(SourceObservation)
        .filter(SourceObservation.canonical_place_id == place_id)
        .order_by(SourceObservation.last_seen_at.desc())
        .limit(5)
        .all()
    )


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
        return [
            _candidate(
                image_url=_wikimedia_file_url(title),
                source_type="wikimedia_commons",
                source_url=_wikimedia_page_url(title),
                attribution="Wikimedia Commons contributors",
                confidence=0.90,
            )
        ]

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
        if not p18_claims:
            return None
        filename = ((p18_claims[0].get("mainsnak") or {}).get("datavalue") or {}).get("value")
    except (KeyError, TypeError, IndexError):
        return None

    if not isinstance(filename, str) or not filename.strip():
        return None

    return _candidate(
        image_url=_wikimedia_file_url(filename),
        source_type="wikidata_p18",
        source_url=observation_source_url or f"https://www.wikidata.org/wiki/{qid}",
        attribution="Wikimedia Commons contributors",
        confidence=0.95,
    )


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

    image_url = None
    original = data.get("originalimage")
    thumbnail = data.get("thumbnail")

    if isinstance(original, dict):
        image_url = original.get("source")
    if not image_url and isinstance(thumbnail, dict):
        image_url = thumbnail.get("source")

    if not isinstance(image_url, str) or not image_url.strip():
        return None

    return _candidate(
        image_url=image_url,
        source_type="wikipedia_page_image",
        source_url=article_url,
        attribution="Wikipedia contributors",
        confidence=0.85,
    )


def _candidate_from_wikimedia_category(category_title: str) -> dict[str, Any] | None:
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": category_title,
        "gcmtype": "file",
        "gcmlimit": "1",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "formatversion": "2",
    }
    data = _fetch_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    if not data:
        return None

    pages = (data.get("query") or {}).get("pages") if isinstance(data.get("query"), dict) else None
    if not isinstance(pages, list) or not pages:
        return None

    imageinfo = pages[0].get("imageinfo") if isinstance(pages[0], dict) else None
    if not isinstance(imageinfo, list) or not imageinfo:
        return None

    image_url = imageinfo[0].get("url")
    if not isinstance(image_url, str):
        return None

    return _candidate(
        image_url=image_url,
        source_type="wikimedia_commons_category",
        source_url=_wikimedia_page_url(category_title),
        attribution="Wikimedia Commons contributors",
        confidence=0.82,
    )


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


def _candidate(
    *,
    image_url: str,
    source_type: str,
    source_url: str | None,
    confidence: float,
    attribution: str | None = None,
    license: str | None = None,
) -> dict[str, Any]:
    return {
        "image_url": image_url,
        "thumbnail_url": None,
        "source_type": source_type,
        "source_url": source_url,
        "attribution": attribution,
        "license": license,
        "confidence": confidence,
    }


def _deduplicate_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    for candidate in sorted(candidates, key=lambda item: float(item.get("confidence") or 0), reverse=True):
        image_url = str(candidate.get("image_url") or "").strip()
        if not image_url or image_url in seen:
            continue
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

    lower = value.lower()
    if "wikipedia.org/wiki/" in lower:
        return False
    if "wikidata.org/wiki/" in lower:
        return False
    if lower.endswith(".svg"):
        return False

    return True


def _wikipedia_article_url(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if ":" in value:
        lang, title = value.split(":", 1)
        return f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
    return f"https://en.wikipedia.org/wiki/{urllib.parse.quote(value.replace(' ', '_'))}"


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
    cache_key = stable_cache_key(HTTP_TEXT_CACHE_NAMESPACE, {"url": url})
    found, cached = get_cached_text(cache_key)
    if found:
        return cached

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html,*/*",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip()
            text = response.read().decode(charset or "utf-8", errors="replace")
            if text:
                host = urllib.parse.urlparse(url).netloc or "unknown"
                set_cached_text(cache_key, text, tag=f"provider:{host}")
            return text
    except Exception:
        return None


def _image_exists(db: Session, place_id: int, image_url: str) -> bool:
    return (
        db.query(PlaceImage.id)
        .filter(PlaceImage.place_id == place_id, PlaceImage.image_url == image_url)
        .first()
        is not None
    )


def main() -> None:
    print(json.dumps(run(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
