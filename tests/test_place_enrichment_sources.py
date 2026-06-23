from sqlalchemy.orm import Session

from models.city import City
from models.import_batch import ImportBatch
from models.place_field_confidence import PlaceFieldConfidence
from models.place_photo_candidate import PlacePhotoCandidate
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services import place_enrichment_sources as enrichment
from services.import_pipeline_foundation_steps import _confidence
from services.place_field_confidence_service import upsert_field_confidence


def _batch(db: Session, city_id: int) -> ImportBatch:
    batch = ImportBatch(
        city_id=city_id,
        source_type="enrichment",
        mode="pipeline",
        dry_run=False,
        status="running",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def test_enrich_places_from_sources_fills_profile_from_legal_sources(monkeypatch, db_session, place_factory):
    place = place_factory(title="Музей моря", category="museum", address=None)
    city = db_session.get(City, place.city_id)
    batch = _batch(db_session, city.id)
    counters: dict[str, int] = {}

    monkeypatch.setattr(enrichment.settings, "geoapify_api_key", "test-key")

    def fake_fetch_json(url: str):
        if "api.geoapify.com" in url:
            return {
                "features": [
                    {
                        "properties": {
                            "name": "Музей моря",
                            "formatted": "ул. Морская, 1",
                            "website": "https://museum.example",
                            "opening_hours": "10:00-18:00",
                            "place_id": "geoapify-museum-1",
                            "datasource": {"raw": {"osm_id": "123"}},
                        }
                    }
                ]
            }
        if "wbsearchentities" in url:
            return {"search": []}
        raise AssertionError(f"Unexpected JSON request: {url}")

    def fake_fetch_text(url: str):
        assert url == "https://museum.example"
        return """
        <html>
          <head>
            <meta name="description" content="Музей о море и городских историях">
            <meta property="og:image" content="/hero.jpg">
            <script type="application/ld+json">
              {"@type":"Museum","telephone":"+7 999 111-22-33","openingHours":"10:00-18:00"}
            </script>
          </head>
        </html>
        """

    monkeypatch.setattr(enrichment, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(enrichment, "_fetch_text", fake_fetch_text)

    enrichment.enrich_places_from_sources(
        db_session,
        city=city,
        batch=batch,
        places=[place],
        job_id=None,
        counters=counters,
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.address == "ул. Морская, 1"
    assert place.website == "https://museum.example"
    assert place.phone == "+7 999 111-22-33"
    assert place.opening_hours == {"raw": "10:00-18:00", "display": "10:00-18:00"}
    assert place.short_description == "Музей о море и городских историях"
    assert place.atmosphere == "Культура и история"
    assert place.inside
    assert place.best_for

    observations = db_session.query(SourceObservation).filter_by(canonical_place_id=place.id).all()
    assert {item.source_type for item in observations} == {"geoapify", "official_site"}
    assert counters["source_observations"] == 2
    assert counters["provider_errors"] == 0
    assert counters["fields_enriched"] >= 8

    confidence_fields = {
        item.field_name: item.source_type
        for item in db_session.query(PlaceFieldConfidence).filter_by(place_id=place.id).all()
    }
    assert confidence_fields["address"] == "geoapify"
    assert confidence_fields["website"] == "geoapify"
    assert confidence_fields["phone"] == "official_site"
    assert confidence_fields["description"] == "official_site"

    photo = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).one()
    assert photo.image_url == "https://museum.example/hero.jpg"
    assert photo.source_type == "official_site"
    assert photo.source_url == "https://museum.example"

    review_fields = {
        (item.field_name, item.reason)
        for item in db_session.query(ReviewQueueItem).filter_by(place_id=place.id).all()
    }
    assert ("address", "missing_after_enrichment") not in review_fields
    assert ("website", "missing_after_enrichment") not in review_fields
    assert ("phone", "missing_after_enrichment") not in review_fields
    assert ("description", "missing_after_enrichment") not in review_fields
    assert ("photo", "missing_after_enrichment") in review_fields


def test_enrich_places_from_sources_keeps_existing_fields_and_queues_conflict(monkeypatch, db_session, place_factory):
    place = place_factory(title="Кофейня Берег", category="cafe", address="Старая улица, 5")
    place.website = "https://coffee.example"
    place.phone = "+7 000 000-00-00"
    db_session.commit()
    city = db_session.get(City, place.city_id)
    batch = _batch(db_session, city.id)
    counters: dict[str, int] = {}

    monkeypatch.setattr(enrichment.settings, "geoapify_api_key", "")
    monkeypatch.setattr(enrichment, "_fetch_json", lambda url: {"search": []})
    monkeypatch.setattr(
        enrichment,
        "_fetch_text",
        lambda url: """
        <html>
          <head>
            <meta name="description" content="Кофейня у набережной">
            <script type="application/ld+json">{"telephone":"+7 999 222-33-44"}</script>
          </head>
        </html>
        """,
    )

    enrichment.enrich_places_from_sources(
        db_session,
        city=city,
        batch=batch,
        places=[place],
        job_id=None,
        counters=counters,
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.phone == "+7 000 000-00-00"
    assert place.short_description == "Кофейня у набережной"
    assert counters["source_conflicts"] == 1

    conflict = (
        db_session.query(ReviewQueueItem)
        .filter_by(place_id=place.id, field_name="phone", reason="source_conflict")
        .one()
    )
    assert conflict.payload["current"] == "+7 000 000-00-00"
    assert conflict.payload["candidate"] == "+7 999 222-33-44"


def test_pipeline_confidence_keeps_enrichment_source(db_session, place_factory):
    place = place_factory(title="Кофейня Берег", category="cafe")
    place.phone = "+7 999 111-22-33"
    db_session.commit()

    upsert_field_confidence(
        db_session,
        place_id=place.id,
        field_name="phone",
        confidence=0.82,
        source_type="official_site",
        raw_value={"value": place.phone},
    )
    db_session.commit()

    _confidence(db_session, place, job_id=None)
    db_session.commit()

    row = db_session.query(PlaceFieldConfidence).filter_by(place_id=place.id, field_name="phone").one()
    assert row.source_type == "official_site"
    assert row.confidence == 0.82
