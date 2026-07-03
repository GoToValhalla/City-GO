from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


FORBIDDEN_COPY = (
    "published/catalog",
    "route policy",
    "canonical category",
    "taxonomy",
    "enrichment/policy",
    "verification backlog",
    "critical confidence",
    "is_route_eligible",
    "route_builder",
    "backend",
    "sql",
    "bucket",
    "status_",
    "eligible",
    "policy",
)
QUEUE_TYPES = {"route_blocker", "auto_fix", "manual_review", "content_gap", "taxonomy_gap", "verification_backlog", "operation"}
PRIMARY_ACTIONS = {"open_queue", "run_auto_fix", "review_items", "fix_taxonomy", "enrich_content", "open_report"}
OWNERS = {"content", "data", "taxonomy", "automation", "platform"}
MOBILE_PRIORITIES = {"high", "medium", "low"}


def _seed_dirty_dataset(db_session, place_factory) -> dict[str, Any]:
    def make(slug: str, title: str, **updates: Any):
        base = dict(
            slug=slug,
            title=title,
            category=updates.pop("category", "museum"),
            address=updates.pop("address", "ул. Морская, 1"),
            image_url=updates.pop("image_url", "https://img.test/place.jpg"),
            is_active=updates.pop("is_active", True),
            is_published=updates.pop("is_published", True),
            is_visible_in_catalog=updates.pop("is_visible_in_catalog", True),
            is_route_eligible=updates.pop("is_route_eligible", True),
            publication_status=updates.pop("publication_status", "published"),
        )
        place = place_factory(**base)
        defaults = {
            "canonical_category": base["category"],
            "short_description": "Подробное описание места для прогулки и проверки данных оператором.",
            "verification_status": "verified",
            "existence_confidence_level": "high",
            "is_duplicate_suspected": False,
            "is_spam_poi": False,
        }
        for key, value in {**defaults, **updates}.items():
            setattr(place, key, value)
        db_session.commit()
        db_session.refresh(place)
        return place

    places = {
        "ready": make("ready-museum", "Городской музей"),
        "disabled": make("manual-disabled", "Отключённое место", is_route_eligible=False),
        "service": make("service-bank", "Банк у вокзала", category="bank", canonical_category="bank"),
        "unknown": make("unknown-category", "Неразобранное место", category="unknown", canonical_category="unknown"),
        "no_photo": make("no-photo", "Место без фото", image_url=None),
        "no_address": make("no-address", "Место без адреса", address=None),
        "no_desc_null": make("no-desc-null", "Описание NULL", short_description=None),
        "no_desc_empty": make("no-desc-empty", "Описание пустое", short_description=""),
        "no_desc_title": make("no-desc-title", "Описание равно названию", short_description="Описание равно названию"),
        "no_desc_short": make("no-desc-short", "Короткое описание", short_description="Слишком коротко"),
        "no_desc_placeholder": make("no-desc-placeholder", "Заглушка описания", short_description="Описание будет добавлено позже"),
        "manual": make("manual-review", "Ручная очередь", publication_status="needs_review", is_published=False, is_visible_in_catalog=False, is_route_eligible=False),
        "auto": make("auto-backlog", "Автоочередь", publication_status="auto_backlog", is_published=False, is_visible_in_catalog=False, is_route_eligible=False),
        "recheck": make("needs-recheck", "Автоперепроверка", verification_status="needs_recheck", is_published=False, is_visible_in_catalog=False, is_route_eligible=False),
        "low_confidence": make("low-confidence", "Низкая уверенность", existence_confidence_level="low"),
        "duplicate": make("duplicate-suspected", "Возможный дубль", is_duplicate_suspected=True),
        "spam": make("spam-poi", "Спам-точка", is_spam_poi=True),
        "generic": make("generic-osm", "Место для прогулки OSM 123"),
    }
    return places


def _overview(client: TestClient) -> dict[str, Any]:
    response = client.get("/admin/overview")
    assert response.status_code == 200
    return response.json()


def _cards(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [card for section in ("critical", "data_quality", "operations") for card in payload[section]]


def _cards_by_code(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["code"]: card for card in _cards(payload)}


def test_admin_overview_has_no_technical_copy_new(client: TestClient, db_session, place_factory) -> None:
    _seed_dirty_dataset(db_session, place_factory)

    for card in _cards(_overview(client)):
        text = " ".join(str(card.get(key) or "") for key in ("title", "hint", "action_label", "short_hint")).casefold()
        for term in FORBIDDEN_COPY:
            assert term not in text, f"{card['code']} leaked technical term: {term}"


def test_admin_overview_cards_have_operator_metadata_new(client: TestClient, db_session, place_factory) -> None:
    _seed_dirty_dataset(db_session, place_factory)

    for card in _cards(_overview(client)):
        assert card["queue_type"] in QUEUE_TYPES
        assert card["primary_action"] in PRIMARY_ACTIONS
        assert card["owner"] in OWNERS
        assert card["mobile_priority"] in MOBILE_PRIORITIES
        assert isinstance(card["is_human_actionable"], bool)
        assert card["short_hint"]
        assert card["action_label"]
        assert card["sample_endpoint"] or card["link_path"].startswith("/admin/")
        assert len(card["short_hint"]) <= 90
        assert len(card["title"]) <= 50
        assert len(card["action_label"]) <= 35


def test_admin_overview_card_counts_match_sample_endpoint_totals_new(client: TestClient, db_session, place_factory) -> None:
    _seed_dirty_dataset(db_session, place_factory)

    for card in _cards(_overview(client)):
        endpoint = card.get("sample_endpoint")
        if not endpoint:
            continue
        response = client.get(endpoint)
        assert response.status_code == 200, card["code"]
        assert response.json()["total"] == card["count"], card["code"]


def test_manual_review_excludes_auto_backlog_and_verification_new(client: TestClient, db_session, place_factory) -> None:
    _seed_dirty_dataset(db_session, place_factory)

    cards = _cards_by_code(_overview(client))

    assert cards["manual_review"]["count"] == 1
    assert cards["auto_backlog"]["count"] == 1
    assert cards["needs_verification"]["count"] == 1


def test_no_description_counts_short_title_copy_and_placeholders_new(client: TestClient, db_session, place_factory) -> None:
    _seed_dirty_dataset(db_session, place_factory)

    cards = _cards_by_code(_overview(client))

    assert cards["no_description"]["count"] == 5
    response = client.get(cards["no_description"]["sample_endpoint"])
    assert response.status_code == 200
    assert response.json()["total"] == 5


def test_route_unknown_is_separate_from_manual_not_route_eligible_new(client: TestClient, db_session, place_factory) -> None:
    _seed_dirty_dataset(db_session, place_factory)

    cards = _cards_by_code(_overview(client))

    assert cards["route_unknown"]["count"] == 1
    assert cards["not_route_eligible"]["count"] == 1
    assert cards["route_blockers"]["count"] == 3
    assert cards["route_blockers"]["title"] == "Проблемы маршрутов"
    assert cards["not_route_eligible"]["title"] == "Отключены вручную"


def test_admin_overview_mobile_cards_have_short_copy_new(client: TestClient, db_session, place_factory) -> None:
    _seed_dirty_dataset(db_session, place_factory)

    for card in _cards(_overview(client)):
        assert len(card["title"]) <= 50
        assert len(card["action_label"]) <= 35
        assert len(card["short_hint"]) <= 90
