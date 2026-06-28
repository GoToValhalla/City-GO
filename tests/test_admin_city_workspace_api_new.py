import allure
import pytest

from models.city_admin_import_job import CityAdminImportJob
from models.place_image import PlaceImage


pytestmark = [pytest.mark.admin, pytest.mark.cities, pytest.mark.api]


@allure.epic("Admin Platform")
@allure.feature("City workspace")
@allure.story("City workspace aggregates operations state")
def test_admin_city_workspace_returns_city_import_readiness_and_coverage(
    client,
    db_session,
    city_factory,
    place_factory,
):
    city = city_factory(
        slug="workspace-city",
        name="Workspace City",
        launch_status="review_required",
        is_active=False,
    )
    city.readiness_score = 72
    city.quality_status = "needs_review"
    db_session.add(city)
    db_session.commit()
    place = place_factory(
        slug="workspace-place",
        title="Workspace Place",
        city_id=city.id,
        category="museum",
        address=None,
    )
    db_session.add(
        CityAdminImportJob(
            city_id=city.id,
            status="success_with_warnings",
            current_step="ready_for_review",
            scopes_total=2,
            scopes_succeeded=1,
            places_found=9,
            places_saved=7,
            step_details={"warnings": ["missing_photo"]},
        )
    )
    db_session.add(
        PlaceImage(
            place_id=place.id,
            image_url="https://example.test/photo.jpg",
            source_type="manual_upload",
            status="needs_review",
        )
    )
    db_session.commit()

    response = client.get("/admin/cities/by-slug/workspace-city/workspace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["city"]["slug"] == "workspace-city"
    assert payload["city"]["can_publish"] is True
    assert payload["readiness"]["readiness_score"] == 40
    assert payload["readiness"]["stored_readiness_score"] == 72
    assert payload["readiness"]["status"] == "needs_review"
    assert payload["import_job"]["status"] == "success_with_warnings"
    assert payload["import_job"]["places_found"] == 9
    assert payload["import_job"]["places_saved"] == 7
    assert payload["coverage"]["city_id"] == city.id
    assert payload["coverage"]["places_without_address"] == 1
    assert payload["coverage"]["places_without_photo"] == 1
    assert payload["coverage"]["pending_photos"] == 1


@allure.epic("Admin Platform")
@allure.feature("City workspace")
@allure.story("Missing city returns 404")
def test_admin_city_workspace_returns_404_for_unknown_slug(client):
    response = client.get("/admin/cities/by-slug/missing-city/workspace")

    assert response.status_code == 404