import pytest
from sqlalchemy.orm import Session

from models.city import City
from services.admin_city_publish_service import publish_city_for_users


@pytest.mark.unit
def test_publish_city_sets_published_and_active_new(db_session: Session) -> None:
    city = City(
        name="Алматы",
        slug="almaty-pub-test",
        country="Россия",
        timezone="Europe/Kaliningrad",
        launch_status="imported",
        is_active=False,
    )
    db_session.add(city)
    db_session.commit()

    result = publish_city_for_users(
        db_session,
        city_slug="almaty-pub-test",
        actor="test-admin",
        country="Казахстан",
        timezone="Asia/Almaty",
    )

    assert result.launch_status == "published"
    assert result.is_active is True
    assert result.country == "Казахстан"
    assert result.timezone == "Asia/Almaty"


@pytest.mark.unit
def test_publish_city_missing_raises_new(db_session: Session) -> None:
    with pytest.raises(ValueError, match="не найден"):
        publish_city_for_users(db_session, city_slug="missing-city", actor="test-admin")
