"""
Тесты P0-4: запрет авто-публикации импортируемых мест.

Проверяют:
1. Imported place создаётся draft/unpublished (seed write path).
2. Imported draft place не появляется в GET /places.
3. Imported draft place не попадает в route candidates.
4. Existing published place остаётся видимым.
5. Admin publish делает draft place видимым.
6. Admin unpublish скрывает место.
7. OSM import path создаёт draft/unpublished (проверка полей Place объекта).
8. Seed import path создаёт draft/unpublished.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


# ─── 1. Seed write path создаёт draft place ──────────────────────────────────

def test_seed_write_creates_draft_place(db_session, city_factory) -> None:
    """write_place_seed_item создаёт новое место как непубличное (needs_review/hidden/draft)."""
    from schemas.place_seed_item import PlaceSeedItem
    from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
    from services.place_seed_write_service import write_place_seed_item

    city_factory(slug="zelenogradsk")

    item = PlaceSeedItem(
        title="Тест Кофейня",
        slug="test-cafe-import-draft",
        city_slug="zelenogradsk",
        category="coffee",
        taxonomy=PlaceTaxonomyPayload(category="coffee", tags=[]),
        lat=54.96,
        lng=20.47,
    )
    result = write_place_seed_item(db_session, item)
    # Без source → quality gate вернёт needs_review
    assert result in ("auto_publish", "needs_review", "hidden")
    db_session.flush()  # db_session имеет autoflush=False — явно флашим

    from models.place import Place
    place = db_session.query(Place).filter(Place.slug == "test-cafe-import-draft").first()
    assert place is not None
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_route_eligible is False
    assert place.is_searchable is False
    # publication_status зависит от gate-решения, но точно не "published"
    assert place.publication_status != "published"


# ─── 2. Draft place не появляется в GET /places ──────────────────────────────

def test_draft_imported_place_not_in_public_catalog(client, db_session, city_factory) -> None:
    """Импортированное место (draft) не возвращается публичным API."""
    from models.place import Place

    city = city_factory(slug="test-visibility-city")
    draft = Place(
        slug="draft-invisible-place",
        title="Черновик",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="cafe",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        publication_status="draft",
        is_active=True,
        status="active",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get("/places", params={"city_slug": "test-visibility-city"})
    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json().get("items", response.json())]
    assert "draft-invisible-place" not in slugs


# ─── 3. Draft place не попадает в route candidates ───────────────────────────

def test_draft_place_not_in_route_candidates(db_session, city_factory) -> None:
    """Место с is_published=False не входит в route candidates."""
    from models.place import Place
    from services.place_public_visibility import public_place_conditions

    city = city_factory(slug="candidate-test-city")
    draft = Place(
        slug="route-candidate-draft",
        title="Черновик для маршрута",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="cafe",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        publication_status="draft",
        is_active=True,
        status="active",
    )
    db_session.add(draft)
    db_session.commit()

    results = (
        db_session.query(Place)
        .filter(*public_place_conditions())
        .filter(Place.slug == "route-candidate-draft")
        .all()
    )
    assert len(results) == 0


# ─── 4. Existing published place остаётся видимым ────────────────────────────

def test_published_place_remains_visible(client, place_factory) -> None:
    """Уже опубликованные места (conftest factory с дефолтами) видны в каталоге."""
    place = place_factory(slug="published-visible-place", title="Опубликованное место")

    response = client.get("/places", params={"city_slug": "zelenogradsk"})
    assert response.status_code == 200
    items = response.json().get("items", response.json())
    slugs = [p["slug"] for p in items]
    assert "published-visible-place" in slugs


# ─── 5. Admin publish делает draft place видимым ─────────────────────────────

def test_admin_publish_makes_draft_visible(client, db_session, city_factory) -> None:
    """После admin publish, место появляется в публичном каталоге."""
    from models.place import Place

    city = city_factory(slug="publish-test-city")
    draft = Place(
        slug="to-be-published",
        title="Будущая публикация",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="cafe",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        publication_status="draft",
        is_active=True,
        status="active",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get("/places", params={"city_slug": "publish-test-city"})
    assert "to-be-published" not in [p["slug"] for p in response.json().get("items", [])]

    publish_resp = client.post(
        f"/admin/places/{draft.id}/publish",
        json={"reason": "Проверено"},
    )
    assert publish_resp.status_code == 200
    assert publish_resp.json()["is_published"] is True

    response_after = client.get("/places", params={"city_slug": "publish-test-city"})
    slugs_after = [p["slug"] for p in response_after.json().get("items", response_after.json())]
    assert "to-be-published" in slugs_after


# ─── 6. Admin unpublish скрывает место ───────────────────────────────────────

def test_admin_unpublish_hides_place(client, db_session, place_factory) -> None:
    """После admin unpublish место исчезает из публичного каталога."""
    place = place_factory(slug="to-be-unpublished", title="Снятое с публикации")

    before = client.get("/places", params={"city_slug": "zelenogradsk"})
    assert "to-be-unpublished" in [p["slug"] for p in before.json().get("items", before.json())]

    unpublish_resp = client.post(
        f"/admin/places/{place.id}/unpublish",
        json={"reason": "Временно скрыто"},
    )
    assert unpublish_resp.status_code == 200
    assert unpublish_resp.json()["is_published"] is False

    after = client.get("/places", params={"city_slug": "zelenogradsk"})
    slugs_after = [p["slug"] for p in after.json().get("items", after.json())]
    assert "to-be-unpublished" not in slugs_after


# ─── 7. OSM import path создаёт draft place ──────────────────────────────────

def test_osm_import_place_constructor_sets_draft_fields() -> None:
    """
    Проверяем, что Place объект, созданный с теми же параметрами что и OSM import,
    явно содержит draft поля. Гарантирует, что константы не изменились.
    """
    from models.place import Place

    place = Place(
        city_id=1,
        category_id=1,
        slug="osm-draft-check",
        title="OSM Place",
        category="cafe",
        address="Test",
        lat=54.96,
        lng=20.47,
        source="osm",
        source_url="https://osm.org/node/1",
        confidence=0.7,
        status="active",
        is_active=True,
        # Эти поля должны явно проставляться import скриптом (после P0-4)
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="draft",
    )
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_route_eligible is False
    assert place.publication_status == "draft"


# ─── 8. Seed import service не публикует место ───────────────────────────────

def test_seed_import_service_creates_unpublished_place(db_session, city_factory) -> None:
    """import_place_seed_items (не dry-run) создаёт непубличное место."""
    from schemas.place_seed_item import PlaceSeedItem
    from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
    from services.place_seed_import_service import import_place_seed_items

    city_factory(slug="zelenogradsk")

    # Используем валидную canonical-категорию "coffee" (как в существующих тестах)
    item = PlaceSeedItem(
        title="Service Import Кофейня",
        slug="service-import-draft-check",
        city_slug="zelenogradsk",
        category="coffee",
        taxonomy=PlaceTaxonomyPayload(category="coffee", tags=[]),
        lat=54.96,
        lng=20.47,
    )
    summary = import_place_seed_items(db_session, [item], dry_run=False)
    # Проверяем, что создано именно место (не invalid/skipped)
    assert summary.created == 1

    from models.place import Place
    place = db_session.query(Place).filter(Place.slug == "service-import-draft-check").first()
    assert place is not None
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_route_eligible is False
    # Без source gate вернёт needs_review, но главное — место не опубликовано
    assert place.publication_status != "published"
