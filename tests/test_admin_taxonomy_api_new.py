import allure
import pytest

from models.category import Category


pytestmark = [pytest.mark.admin, pytest.mark.taxonomy, pytest.mark.api]


@allure.epic("Admin Platform")
@allure.feature("Backend-driven taxonomy")
@allure.story("Admin category controls use backend categories")
def test_admin_taxonomy_categories_include_catalog_and_observed(client, db_session, place_factory):
    db_session.add(
        Category(
            code="health",
            name="Здоровье",
            is_active=True,
            is_route_eligible=False,
            is_catalog_visible=False,
            is_default_enabled=False,
        )
    )
    db_session.commit()
    place_factory(slug="taxonomy-viewpoint", title="Viewpoint", category="viewpoint")
    place_factory(slug="taxonomy-transport", title="Transport", category="transport")

    response = client.get("/admin/taxonomy/categories")

    assert response.status_code == 200
    categories = {item["code"]: item for item in response.json()["categories"]}
    assert categories["health"]["source"] == "catalog"
    assert categories["health"]["is_route_eligible"] is False
    assert categories["viewpoint"]["is_observed"] is True
    assert categories["viewpoint"]["observed_count"] == 1
    assert categories["transport"]["is_observed"] is True
    assert categories["transport"]["observed_count"] == 1
    assert categories["coffee"]["label"] == "Кофейня"


@allure.epic("Admin Platform")
@allure.feature("Backend-driven taxonomy")
@allure.story("Unknown observed categories remain selectable")
def test_admin_taxonomy_preserves_unknown_observed_category(client, place_factory):
    place_factory(slug="taxonomy-custom", title="Custom", category="quiet_yard")

    response = client.get("/admin/taxonomy/categories")

    assert response.status_code == 200
    categories = {item["code"]: item for item in response.json()["categories"]}
    assert categories["quiet_yard"]["label"] == "quiet_yard"
    assert categories["quiet_yard"]["source"] == "catalog+observed"
    assert categories["quiet_yard"]["observed_count"] == 1
