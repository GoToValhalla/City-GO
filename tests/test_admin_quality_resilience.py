import pytest


def test_admin_quality_empty_database_returns_stable_contract(client):
    response = client.get("/admin/quality")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert isinstance(payload["todo"], list)
    assert payload["limit"] == 25
    assert payload["offset"] == 0


def test_admin_quality_does_not_call_heavy_critical_coverage(client, place_factory, monkeypatch):
    import services.data_quality.critical_coverage as cc_module

    place_factory(
        title="Lightweight Museum",
        category="museum",
        is_route_eligible=True,
        image_url=None,
        address=None,
    )

    monkeypatch.setattr(cc_module, "build_city_critical_coverage", lambda *args, **kwargs: pytest.fail("heavy build_city_critical_coverage called"))
    monkeypatch.setattr(cc_module, "compute_city_critical_coverage", lambda *args, **kwargs: pytest.fail("heavy compute_city_critical_coverage called"))

    response = client.get("/admin/quality")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert isinstance(payload["items"], list)
    assert isinstance(payload["todo"], list)
    assert payload["items"][0]["critical_coverage"]["mode"] == "fast_summary"
