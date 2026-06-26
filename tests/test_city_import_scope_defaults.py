from models.city_import_scope import CityImportScope


def test_city_import_scope_enabled_by_default_for_refresh_pipeline() -> None:
    default = CityImportScope.__table__.c.enabled.default

    assert default is not None
    assert default.arg is True
