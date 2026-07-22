"""Stage 5 search projection live path: toggle OFF/ON and failure contracts."""

from __future__ import annotations

import models.place_published_snapshot  # noqa: F401
import models.search_routing_stage5  # noqa: F401
from models.place_published_snapshot import PublishedPlaceSnapshot
from models.search_routing_stage5 import SearchPlaceDocument
from models.feature_toggle import FeatureToggle
from services.data_foundation_projection_service import build_snapshot_from_place
from services.feature_toggle_service import update_toggle
from services.public_read_projection_service import (
    REASON_EMPTY,
    REASON_MISSING,
    REASON_STALE,
    REASON_VERSION,
)
from services.search_projection_rebuild_service import rebuild_search_place_documents
from services.search_projection_read_service import SEARCH_PROJECTION_TOGGLE
from tests.allure_support import title


def _enable_projection_reads(db_session) -> None:
    update_toggle(
        db_session,
        key=SEARCH_PROJECTION_TOGGLE,
        scope="global",
        scope_id=None,
        value_bool=True,
        actor="test",
    )


def _force_unsafe_projection_reads(db_session) -> None:
    db_session.add(FeatureToggle(key=SEARCH_PROJECTION_TOGGLE, scope="global", scope_id=None, value_bool=True))
    db_session.commit()


def _seed_published_searchable(db_session, place_factory, *, title: str = "Coffee Point"):
    place = place_factory(title=title, slug="coffee-point")
    snapshot = build_snapshot_from_place(place, snapshot_version=1)
    db_session.add(snapshot)
    db_session.commit()
    return place, snapshot


@title("Toggle OFF keeps legacy Place search path")
def test_search_projection_toggle_off_uses_legacy_path(client, db_session, place_factory) -> None:
    place_factory(title="Coffee Point", slug="coffee-point")
    response = client.get("/places/search/", params={"q": "Coffee", "city_slug": "zelenogradsk"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["slug"] == "coffee-point"


@title("Toggle ON with fresh projection returns search hits")
def test_search_projection_toggle_on_fresh_projection(client, db_session, place_factory) -> None:
    place, _ = _seed_published_searchable(db_session, place_factory)
    rebuild_search_place_documents(db_session)
    db_session.commit()
    _enable_projection_reads(db_session)

    response = client.get("/places/search/", params={"q": "Coffee", "city_slug": "zelenogradsk"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == place.id
    assert payload["items"][0]["title"] == "Coffee Point"


@title("Toggle ON with missing snapshots returns projection_missing")
def test_search_projection_missing_snapshots(client, db_session, place_factory) -> None:
    place_factory(title="Coffee Point", slug="coffee-point")
    _force_unsafe_projection_reads(db_session)
    response = client.get("/places/search/", params={"q": "Coffee", "city_slug": "zelenogradsk"})
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "public_read_projection_unavailable"
    assert detail["reason"] == REASON_MISSING
    assert detail["read_path"] == "search"


@title("Toggle ON with empty projection returns projection_empty")
def test_search_projection_empty(client, db_session, place_factory) -> None:
    place, _ = _seed_published_searchable(db_session, place_factory)
    _force_unsafe_projection_reads(db_session)
    response = client.get(
        "/places/search/",
        params={"q": "Coffee", "city_id": place.city_id},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == REASON_EMPTY


@title("Toggle ON with stale freshness returns projection_stale")
def test_search_projection_stale_status(client, db_session, place_factory) -> None:
    place, snapshot = _seed_published_searchable(db_session, place_factory)
    rebuild_search_place_documents(db_session, city_id=place.city_id)
    db_session.commit()
    doc = db_session.query(SearchPlaceDocument).filter(SearchPlaceDocument.place_id == place.id).one()
    doc.freshness_status = "stale"
    db_session.commit()
    _force_unsafe_projection_reads(db_session)

    response = client.get("/places/search/", params={"q": "Coffee", "city_id": place.city_id})
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == REASON_STALE
    assert snapshot.snapshot_version == 1


@title("Toggle ON with version drift returns projection_version_incompatible")
def test_search_projection_version_incompatible(client, db_session, place_factory) -> None:
    place, _ = _seed_published_searchable(db_session, place_factory)
    rebuild_search_place_documents(db_session, city_id=place.city_id)
    db_session.commit()
    newer = build_snapshot_from_place(place, snapshot_version=2)
    db_session.add(newer)
    db_session.commit()
    _force_unsafe_projection_reads(db_session)

    response = client.get("/places/search/", params={"q": "Coffee", "city_id": place.city_id})
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == REASON_VERSION


@title("Rebuild writes SearchPlaceDocument only from PublishedPlaceSnapshot")
def test_search_projection_rebuild_from_snapshots(db_session, place_factory) -> None:
    place, _ = _seed_published_searchable(db_session, place_factory)
    before_published = place.is_published
    summary = rebuild_search_place_documents(db_session, city_id=place.city_id)
    db_session.commit()
    db_session.refresh(place)
    assert summary["status"] == "succeeded"
    assert summary["rebuilt_count"] == 1
    assert place.is_published is before_published
    assert db_session.query(PublishedPlaceSnapshot).count() == 1
    assert db_session.query(SearchPlaceDocument).count() == 1
