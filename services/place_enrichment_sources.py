"""Legal place enrichment providers for source-first City GO data quality.

This module deliberately avoids scraping Yandex/2GIS. It uses sources that are suitable
for ingestion or source observation workflows: Geoapify when configured, Wikidata, and
official public pages referenced by the place itself.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from core.config import settings
from models.city import City
from models.import_batch import ImportBatch
from models.place import Place
from models.source_observation import SourceObservation
from services.place_field_confidence_service import upsert_field_confidence
from services.place_photo_candidate_service import add_photo_candidate
from services.review_queue_service import ensure_review_item

HTTP_TIMEOUT_SECONDS = 8
MAX_DESCRIPTION_LENGTH = 420
ENRICHMENT_FIELDS = ("address", "website", "phone", "opening_hours", "description", "photo")


@dataclass(frozen=True)
class ProviderObservation:
    source_type: str
    source_external_id: str
    source_url: str | None
    raw_payload: dict[str, Any]
    confidence: float


@dataclass(frozen=True)
class CandidateProfile:
    address: str | None = None
    website: str | None = None
    phone: str | None = None
    opening_hours: str | dict[str, Any] | None = None
    description: str | None = None
    image_url: str | None = None
    image_source_url: str | None = None
    atmosphere: str | None = None
    inside: str | None = None
    best_for: str | None = None


def enrich_places_from_sources(
    db: Session,
    *,
    city: City,
    batch: ImportBatch,
    places: list[Place],
    job_id: int | None,
    counters: dict[str, int],
) -> None:
    """Run external enrichment providers and apply only safe, missing fields."""
    counters.setdefault("source_observations", 0)
    counters.setdefault("fields_enriched", 0)
    counters.setdefault("source_conflicts", 0)
    counters.setdefault("provider_errors", 0)

    for place in places:
        provider_profiles = _collect_profiles(place, counters)
        for observation, profile in provider_profiles:
            _record_observation(db, city=city, batch=batch, place=place, observation=observation)
            counters["source_observations"] += 1
            _apply_profile(db, city=city, place=place, profile=profile, observation=observation, job_id=job_id, counters=counters)
        _apply_category_profile(db, city=city, place=place, job_id=job_id, counters=counters)
        _queue_missing_fields(db, city=city, place=place, job_id=job_id)


def _collect_profiles(place: Place, counters: dict[str, int]) -> list[tuple[ProviderObservation, CandidateProfile]]:
    profiles: list[tuple[ProviderObservation, CandidateProfile]] = []
    for collector in (_collect_geoapify, _collect_wikidata, _collect_official_site):
        try:
            result = collector(place)
        except Exception:
            counters["provider_errors"] += 1
            continue
        if result is not None:
            profiles.append(result)
    return profiles


def _collect_geoapify(place: Place) -> tuple[ProviderObservation, CandidateProfile] | None:
    api_key = settings.geoapify_api_key.strip()
    if not api_key or place.lat is None or place.lng is None:
        return None

    params = urllib.parse.urlencode(
        {
            "categories": _geoapify_categories(place.category),
            "filter": f"circle:{place.lng},{place.lat},120",
            "bias": f"proximity:{place.lng},{place.lat}",
            "limit": 5,
            "apiKey": api_key,
        }
    )
    data = _fetch_json(f"https://api.geoapify.com/v2/places?{params}")
    feature = _best_geoapify_feature(data, place)
    if feature is None:
        return None

    props = feature.get("properties") or {}
    raw = _geoapify_raw(props)
    external_id = str(props.get("place_id") or raw.get("osm_id") or raw.get("wikidata") or _payload_hash(props))
    profile = CandidateProfile(
        address=_first_string(props.get("formatted"), props.get("address_line2"), raw.get("addr:full")),
        website=_first_url(props.get("website"), raw.get("website"), raw.get("contact:website")),
        phone=_first_string(props.get("phone"), raw.get("phone"), raw.get("contact:phone")),
        opening_hours=_first_string(props.get("opening_hours"), raw.get("opening_hours")),
    )
    observation = ProviderObservation(
        source_type="geoapify",
        source_external_id=external_id,
        source_url=None,
        raw_payload=feature,
        confidence=0.72,
    )
    return observation, profile


def _collect_wikidata(place: Place) -> tuple[ProviderObservation, CandidateProfile] | None:
    query = urllib.parse.urlencode(
        {
            "action": "wbsearchentities",
            "format": "json",
            "language": "ru",
            "uselang": "ru",
            "limit": 3,
            "search": place.title,
        }
    )
    data = _fetch_json(f"https://www.wikidata.org/w/api.php?{query}")
    entity = _best_wikidata_result(data, place)
    if entity is None:
        return None

    entity_id = str(entity.get("id"))
    details = _fetch_wikidata_entity(entity_id)
    description = _clean_description(_first_string(entity.get("description"), details.get("description")))
    profile = CandidateProfile(
        website=_first_url(details.get("official_website")),
        description=description,
        image_url=_first_url(details.get("image_url")),
        image_source_url=_first_url(details.get("entity_url")),
    )
    observation = ProviderObservation(
        source_type="wikidata",
        source_external_id=entity_id,
        source_url=_first_url(details.get("entity_url")),
        raw_payload={"search": entity, "entity": details},
        confidence=0.68,
    )
    return observation, profile


def _collect_official_site(place: Place) -> tuple[ProviderObservation, CandidateProfile] | None:
    url = _first_url(getattr(place, "website", None), place.source_url)
    if url is None:
        return None
    page = _fetch_text(url)
    meta = _extract_html_metadata(page, base_url=url)
    if not any(meta.values()):
        return None
    profile = CandidateProfile(
        website=url,
        phone=_first_string(meta.get("phone")),
        opening_hours=meta.get("opening_hours"),
        description=_clean_description(_first_string(meta.get("description"))),
        image_url=_first_url(meta.get("image_url")),
        image_source_url=url,
    )
    observation = ProviderObservation(
        source_type="official_site",
        source_external_id=url,
        source_url=url,
        raw_payload=meta,
        confidence=0.82,
    )
    return observation, profile


def _record_observation(db: Session, *, city: City, batch: ImportBatch, place: Place, observation: ProviderObservation) -> SourceObservation:
    row = (
        db.query(SourceObservation)
        .filter(
            SourceObservation.city_id == city.id,
            SourceObservation.source_type == observation.source_type,
            SourceObservation.source_external_id == observation.source_external_id,
        )
        .first()
    )
    row = row or SourceObservation(
        import_batch_id=batch.id,
        city_id=city.id,
        source_type=observation.source_type,
        source_external_id=observation.source_external_id,
    )
    row.seen_in_batch_id = batch.id
    row.source_url = observation.source_url
    row.raw_name = place.title
    row.raw_category = place.category
    row.raw_lat = place.lat
    row.raw_lng = place.lng
    row.raw_payload = observation.raw_payload
    row.payload_hash = _payload_hash(observation.raw_payload)
    row.canonical_place_id = place.id
    row.confidence = observation.confidence
    row.match_status = "matched_place"
    row.normalization_status = "candidate_fields_extracted"
    row.last_seen_at = datetime.utcnow()
    db.add(row)
    return row


def _apply_profile(
    db: Session,
    *,
    city: City,
    place: Place,
    profile: CandidateProfile,
    observation: ProviderObservation,
    job_id: int | None,
    counters: dict[str, int],
) -> None:
    _apply_text_field(db, city=city, place=place, field_name="address", value=profile.address, observation=observation, job_id=job_id, counters=counters)
    _apply_text_field(db, city=city, place=place, field_name="website", value=profile.website, observation=observation, job_id=job_id, counters=counters)
    _apply_text_field(db, city=city, place=place, field_name="phone", value=profile.phone, observation=observation, job_id=job_id, counters=counters)
    _apply_opening_hours(db, city=city, place=place, value=profile.opening_hours, observation=observation, job_id=job_id, counters=counters)
    _apply_description(db, city=city, place=place, value=profile.description, observation=observation, job_id=job_id, counters=counters)
    _apply_text_field(db, city=city, place=place, field_name="atmosphere", value=profile.atmosphere, observation=observation, job_id=job_id, counters=counters)
    _apply_text_field(db, city=city, place=place, field_name="inside", value=profile.inside, observation=observation, job_id=job_id, counters=counters)
    _apply_text_field(db, city=city, place=place, field_name="best_for", value=profile.best_for, observation=observation, job_id=job_id, counters=counters)
    if profile.image_url:
        candidate = add_photo_candidate(
            db,
            place_id=place.id,
            image_url=profile.image_url,
            source_type=observation.source_type,
            match_type="source_candidate",
            confidence=observation.confidence,
        )
        candidate.source_url = profile.image_source_url or observation.source_url
        counters["fields_enriched"] += 1


def _apply_text_field(
    db: Session,
    *,
    city: City,
    place: Place,
    field_name: str,
    value: str | None,
    observation: ProviderObservation,
    job_id: int | None,
    counters: dict[str, int],
) -> None:
    cleaned = _clean_string(value)
    if not cleaned:
        return
    current = _clean_string(getattr(place, field_name, None))
    if current:
        if _normalize_text(current) != _normalize_text(cleaned):
            counters["source_conflicts"] += 1
            ensure_review_item(
                db,
                city_id=city.id,
                place_id=place.id,
                job_id=job_id,
                field_name=field_name,
                reason="source_conflict",
                severity="medium",
                payload={"current": current, "candidate": cleaned, "source_type": observation.source_type},
            )
        return
    setattr(place, field_name, cleaned)
    _confidence(db, place=place, field_name=field_name, value=cleaned, observation=observation)
    counters["fields_enriched"] += 1


def _apply_opening_hours(
    db: Session,
    *,
    city: City,
    place: Place,
    value: str | dict[str, Any] | None,
    observation: ProviderObservation,
    job_id: int | None,
    counters: dict[str, int],
) -> None:
    if not value:
        return
    candidate = value if isinstance(value, dict) else {"raw": value, "display": value}
    if place.opening_hours:
        if place.opening_hours != candidate:
            counters["source_conflicts"] += 1
            ensure_review_item(
                db,
                city_id=city.id,
                place_id=place.id,
                job_id=job_id,
                field_name="opening_hours",
                reason="source_conflict",
                severity="medium",
                payload={"current": place.opening_hours, "candidate": candidate, "source_type": observation.source_type},
            )
        return
    place.opening_hours = candidate
    _confidence(db, place=place, field_name="opening_hours", value=candidate, observation=observation)
    counters["fields_enriched"] += 1


def _apply_description(
    db: Session,
    *,
    city: City,
    place: Place,
    value: str | None,
    observation: ProviderObservation,
    job_id: int | None,
    counters: dict[str, int],
) -> None:
    cleaned = _clean_description(value)
    if not cleaned:
        return
    if place.short_description:
        if _normalize_text(place.short_description) != _normalize_text(cleaned):
            ensure_review_item(
                db,
                city_id=city.id,
                place_id=place.id,
                job_id=job_id,
                field_name="description",
                reason="source_conflict",
                severity="low",
                payload={"current": place.short_description, "candidate": cleaned, "source_type": observation.source_type},
            )
        return
    place.short_description = cleaned
    _confidence(db, place=place, field_name="description", value=cleaned, observation=observation)
    counters["fields_enriched"] += 1


def _apply_category_profile(db: Session, *, city: City, place: Place, job_id: int | None, counters: dict[str, int]) -> None:
    profile = _category_profile(place)
    synthetic = ProviderObservation(
        source_type="citygo_category_rules",
        source_external_id=f"place:{place.id}:category-profile",
        source_url=None,
        raw_payload={"category": place.category, "canonical_category": place.canonical_category},
        confidence=0.55,
    )
    for field_name, value in profile.items():
        _apply_text_field(db, city=city, place=place, field_name=field_name, value=value, observation=synthetic, job_id=job_id, counters=counters)


def _queue_missing_fields(db: Session, *, city: City, place: Place, job_id: int | None) -> None:
    missing = {
        "address": not _clean_string(place.address),
        "website": not _clean_string(getattr(place, "website", None)),
        "phone": not _clean_string(getattr(place, "phone", None)),
        "opening_hours": not bool(place.opening_hours),
        "description": not _clean_string(place.short_description),
        "photo": not _clean_string(place.image_url),
    }
    for field_name, is_missing in missing.items():
        if is_missing:
            ensure_review_item(
                db,
                city_id=city.id,
                place_id=place.id,
                job_id=job_id,
                field_name=field_name,
                reason="missing_after_enrichment",
                severity="medium" if field_name in {"address", "description", "photo"} else "low",
            )


def _confidence(db: Session, *, place: Place, field_name: str, value: object, observation: ProviderObservation) -> None:
    upsert_field_confidence(
        db,
        place_id=place.id,
        field_name=field_name,
        confidence=observation.confidence,
        source_type=observation.source_type,
        raw_value={"value": value, "source_external_id": observation.source_external_id, "source_url": observation.source_url},
    )


def _geoapify_categories(category: str | None) -> str:
    normalized = (category or "").lower()
    if normalized in {"cafe", "coffee", "restaurant", "food", "bar", "bakery"}:
        return "catering"
    if normalized in {"museum", "culture", "art", "historic", "monument", "architecture"}:
        return "entertainment.museum,tourism.sights"
    if normalized in {"park", "walk", "viewpoint", "beach", "nature"}:
        return "leisure.park,tourism.sights,natural"
    return "tourism.sights,catering,entertainment"


def _best_geoapify_feature(data: dict[str, Any], place: Place) -> dict[str, Any] | None:
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        return None
    scored = []
    for feature in features:
        props = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(props, dict):
            continue
        name = _first_string(props.get("name"), _geoapify_raw(props).get("name"))
        score = _name_score(place.title, name)
        if score >= 0.45:
            scored.append((score, feature))
    if not scored:
        return features[0] if features and isinstance(features[0], dict) else None
    return sorted(scored, key=lambda item: item[0], reverse=True)[0][1]


def _geoapify_raw(props: dict[str, Any]) -> dict[str, Any]:
    datasource = props.get("datasource")
    if isinstance(datasource, dict) and isinstance(datasource.get("raw"), dict):
        return datasource["raw"]
    return {}


def _best_wikidata_result(data: dict[str, Any], place: Place) -> dict[str, Any] | None:
    results = data.get("search") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return None
    scored = []
    for item in results:
        if not isinstance(item, dict):
            continue
        score = max(_name_score(place.title, _first_string(item.get("label"))), _name_score(place.title, _first_string(item.get("match", {}).get("text") if isinstance(item.get("match"), dict) else None)))
        if score >= 0.55:
            scored.append((score, item))
    return sorted(scored, key=lambda item: item[0], reverse=True)[0][1] if scored else None


def _fetch_wikidata_entity(entity_id: str) -> dict[str, Any]:
    params = urllib.parse.urlencode({"action": "wbgetentities", "format": "json", "ids": entity_id, "props": "claims|descriptions|sitelinks", "languages": "ru|en"})
    data = _fetch_json(f"https://www.wikidata.org/w/api.php?{params}")
    entity = ((data.get("entities") or {}).get(entity_id) or {}) if isinstance(data, dict) else {}
    descriptions = entity.get("descriptions") if isinstance(entity, dict) else {}
    claims = entity.get("claims") if isinstance(entity, dict) else {}
    description = None
    if isinstance(descriptions, dict):
        ru = descriptions.get("ru") if isinstance(descriptions.get("ru"), dict) else {}
        en = descriptions.get("en") if isinstance(descriptions.get("en"), dict) else {}
        description = _first_string(ru.get("value"), en.get("value"))
    return {
        "entity_url": f"https://www.wikidata.org/wiki/{entity_id}",
        "description": description,
        "official_website": _claim_string(claims, "P856"),
        "image_url": _commons_image_url(_claim_string(claims, "P18")),
    }


def _claim_string(claims: Any, prop: str) -> str | None:
    if not isinstance(claims, dict):
        return None
    values = claims.get(prop)
    if not isinstance(values, list) or not values:
        return None
    mainsnak = values[0].get("mainsnak") if isinstance(values[0], dict) else None
    datavalue = mainsnak.get("datavalue") if isinstance(mainsnak, dict) else None
    value = datavalue.get("value") if isinstance(datavalue, dict) else None
    return value if isinstance(value, str) else None


def _commons_image_url(filename: str | None) -> str | None:
    if not filename:
        return None
    quoted = urllib.parse.quote(filename.replace(" ", "_"))
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quoted}"


def _extract_html_metadata(page: str, *, base_url: str) -> dict[str, Any]:
    json_ld = _extract_json_ld(page)
    description = _first_string(_meta_content(page, "description"), _meta_property(page, "og:description"), json_ld.get("description"))
    image_url = _absolute_url(_first_string(_meta_property(page, "og:image"), json_ld.get("image")), base_url)
    return {
        "description": description,
        "image_url": image_url,
        "phone": _first_string(json_ld.get("telephone"), _phone_from_text(page)),
        "opening_hours": _first_string(json_ld.get("openingHours"), json_ld.get("openingHoursSpecification")),
    }


def _extract_json_ld(page: str) -> dict[str, Any]:
    matches = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, flags=re.I | re.S)
    for raw in matches:
        try:
            parsed = json.loads(html.unescape(raw.strip()))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            parsed = next((item for item in parsed if isinstance(item, dict)), {})
        if isinstance(parsed, dict):
            return parsed
    return {}


def _meta_content(page: str, name: str) -> str | None:
    pattern = rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']'
    match = re.search(pattern, page, flags=re.I)
    return html.unescape(match.group(1)) if match else None


def _meta_property(page: str, prop: str) -> str | None:
    pattern = rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']'
    match = re.search(pattern, page, flags=re.I)
    return html.unescape(match.group(1)) if match else None


def _phone_from_text(page: str) -> str | None:
    text = re.sub(r"<[^>]+>", " ", page)
    match = re.search(r"(?:\+7|8)[\s\-(]?\d{3}[\s\-)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", text)
    return match.group(0).strip() if match else None


def _category_profile(place: Place) -> dict[str, str | None]:
    category = (place.canonical_category or place.category or "").lower()
    if category in {"coffee", "cafe", "restaurant", "food", "bar", "bakery"}:
        return {"atmosphere": "Еда и отдых", "inside": "Зал, меню и возможность сделать паузу", "best_for": "Кофе, перекус или спокойная остановка в маршруте"}
    if category in {"museum", "culture", "art", "historic", "monument", "architecture"}:
        return {"atmosphere": "Культура и история", "inside": "Экспозиции, архитектурные детали или исторический контекст", "best_for": "Первое знакомство с городом и неспешная прогулка"}
    if category in {"park", "walk", "viewpoint", "beach", "nature"}:
        return {"atmosphere": "Прогулка на свежем воздухе", "inside": "Открытое пространство и точки для остановки", "best_for": "Прогулка, фото и спокойный маршрут"}
    return {"atmosphere": None, "inside": None, "best_for": None}


def _fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(_request(url), timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str) -> str:
    with urllib.request.urlopen(_request(url), timeout=HTTP_TIMEOUT_SECONDS) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return ""
        return response.read(750_000).decode("utf-8", errors="ignore")


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": settings.place_address_geocoder_user_agent or "CityGoEnrichment/1.0"})


def _first_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value:
            nested = _first_string(*value)
            if nested:
                return nested
    return None


def _first_url(*values: object) -> str | None:
    for value in values:
        candidate = _clean_string(value)
        if candidate and candidate.startswith(("http://", "https://")):
            return candidate
    return None


def _absolute_url(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    return urllib.parse.urljoin(base_url, value)


def _clean_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _clean_description(value: str | None) -> str | None:
    cleaned = _clean_string(value)
    if not cleaned:
        return None
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > MAX_DESCRIPTION_LENGTH:
        return f"{cleaned[:MAX_DESCRIPTION_LENGTH].rsplit(' ', 1)[0]}..."
    return cleaned


def _normalize_text(value: str) -> str:
    return re.sub(r"\W+", "", value.lower(), flags=re.U)


def _name_score(left: str | None, right: str | None) -> float:
    left_tokens = set(re.findall(r"[\wа-яА-ЯёЁ]+", (left or "").lower()))
    right_tokens = set(re.findall(r"[\wа-яА-ЯёЁ]+", (right or "").lower()))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
