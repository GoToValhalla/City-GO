def test_admin_quality_empty_database_returns_stable_contract(client):
    response = client.get("/admin/quality")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert isinstance(payload["todo"], list)


def test_admin_quality_degrades_when_critical_coverage_fails(client, place_factory, monkeypatch):
    import services.admin_platform_quality as quality_service

    place_factory(
        title="Broken Coverage Museum",
        category="museum",
        canonical_category="museum",
        is_route_eligible=True,
        image_url=None,
        address=None,
    )

    def raise_coverage_error(*args, **kwargs):
        raise RuntimeError("coverage boom")

    monkeypatch.setattr(quality_service, "compute_city_critical_coverage", raise_coverage_error)

    response = client.get("/admin/quality")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    row = payload["items"][0]
    assert row["critical_coverage"]["degraded"] is True
    assert row["critical_coverage"]["error"] == "RuntimeError"
