from models.feature_toggle import FeatureToggle
from services.city_service import get_available_cities


def test_city_availability_uses_the_requested_channel(db_session, city_factory) -> None:
    city = city_factory(slug="astrakhan", name="Астрахань")
    db_session.add_all(
        [
            FeatureToggle(
                key="web_enabled",
                scope="city",
                scope_id=city.slug,
                value_bool=False,
            ),
            FeatureToggle(
                key="telegram_enabled",
                scope="city",
                scope_id=city.slug,
                value_bool=True,
            ),
        ]
    )
    db_session.commit()

    web_slugs = {row["slug"] for row in get_available_cities(db_session, include_draft=True, channel="web")}
    telegram_slugs = {row["slug"] for row in get_available_cities(db_session, include_draft=True, channel="telegram")}

    assert city.slug not in web_slugs
    assert city.slug in telegram_slugs


def test_telegram_channel_respects_its_global_switch(db_session, city_factory) -> None:
    city_factory(slug="yerevan", name="Ереван")
    db_session.add(
        FeatureToggle(
            key="telegram_bot_enabled",
            scope="global",
            scope_id=None,
            value_bool=False,
        )
    )
    db_session.commit()

    assert get_available_cities(db_session, include_draft=True, channel="telegram") == []
