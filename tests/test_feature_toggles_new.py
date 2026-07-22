"""Тесты feature toggles: каталог, guards, seed."""

from fastapi.testclient import TestClient

from services.feature_toggle_catalog import GLOBAL_TOGGLES
from services.feature_toggle_service import is_toggle_enabled, list_global_toggles


def test_global_toggle_catalog_new() -> None:
    keys = {item["key"] for item in GLOBAL_TOGGLES}
    assert "route_planning_engine_enabled" in keys
    assert "ai_intent_parsing_enabled" in keys
    assert len(GLOBAL_TOGGLES) >= 20


def test_list_global_toggles_has_groups_new(client: TestClient) -> None:
    response = client.get("/admin/feature-toggles?scope=global")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == len(GLOBAL_TOGGLES)
    assert all(item.get("group") for item in items)


def test_toggle_groups_endpoint_new(client: TestClient) -> None:
    response = client.get("/admin/feature-toggles/groups")
    assert response.status_code == 200
    assert len(response.json()) >= 5


def test_maintenance_mode_guard_new(db_session) -> None:
    import pytest
    from fastapi import HTTPException

    from services.feature_toggle_guards import assert_web_public
    from services.feature_toggle_service import update_toggle

    update_toggle(db_session, key="maintenance_mode", scope="global", scope_id=None, value_bool=True, actor="test")
    with pytest.raises(HTTPException) as exc:
        assert_web_public(db_session)
    assert exc.value.status_code == 503


def test_toggle_update_persists_new(client: TestClient, db_session) -> None:
    response = client.put("/admin/feature-toggles/debug_mode?scope=global", json={"value_bool": True, "reason": "test"})
    assert response.status_code == 200
    assert is_toggle_enabled(db_session, "debug_mode", default=False) is True


def test_tma_enabled_toggle_in_catalog_new() -> None:
    keys = {item["key"] for item in GLOBAL_TOGGLES}
    assert "tma_enabled" in keys
    tma_toggle = next(item for item in GLOBAL_TOGGLES if item["key"] == "tma_enabled")
    assert tma_toggle["default"] is True


def test_search_projection_reads_toggle_in_catalog_new() -> None:
    keys = {item["key"] for item in GLOBAL_TOGGLES}
    assert "search_projection_reads_enabled" in keys
    toggle = next(item for item in GLOBAL_TOGGLES if item["key"] == "search_projection_reads_enabled")
    assert toggle["default"] is False
    assert toggle["group"] == "data"


def test_public_features_endpoint_defaults_tma_enabled_new(client: TestClient) -> None:
    response = client.get("/features/public")
    assert response.status_code == 200
    assert response.json() == {"tma_enabled": True}


def test_public_features_endpoint_reflects_admin_toggle_new(client: TestClient, db_session) -> None:
    update_response = client.put("/admin/feature-toggles/tma_enabled?scope=global", json={"value_bool": False, "reason": "disable tma"})
    assert update_response.status_code == 200

    response = client.get("/features/public")
    assert response.status_code == 200
    assert response.json() == {"tma_enabled": False}
