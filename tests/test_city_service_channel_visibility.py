from models.feature_toggle import FeatureToggle
from services.city_service import get_available_cities


def test_public_city_catalog_requires_explicit_city_publication(db_session, city_factory, place_factory) -> None:
    published = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    place_factory(city_id=published.id, slug="rostov-place", title="Место", category="museum")
    city_factory(slug="astrakhan", name="Астрахань", is_active=False, launch_status="importing")
    city_factory(slug="yerevan", name="Ереван", is_active=True, launch_status="draft")

    slugs = {row["slug"] for row in get_available_cities(db_session)}

    assert slugs == {published.slug}


def test_public_city_catalog_is_not_split_by_web_and_telegram_feature_flags(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    place_factory(city_id=city.id, slug="rostov-place", title="Место", category="museum")
    db_session.add_all(
        [
            FeatureToggle(key="web_enabled", scope="city", scope_id=city.slug, value_bool=False),
            FeatureToggle(key="telegram_enabled", scope="city", scope_id=city.slug, value_bool=True),
        ]
    )
    db_session.commit()

    assert [row["slug"] for row in get_available_cities(db_session)] == [city.slug]
