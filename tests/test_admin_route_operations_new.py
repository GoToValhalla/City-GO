"""Тесты Route Operations API."""

from __future__ import annotations


def test_eligibility_list_excludes_pharmacy_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-elig-city")
    place_factory(slug="ops-cafe", category="cafe", city_id=city.id)
    place_factory(slug="ops-pharm", category="pharmacy", city_id=city.id)
    response = client.get(f"/admin/routes/eligibility?city_slug={city.slug}&eligible=false")
    assert response.status_code == 200
    body = response.json()
    categories = {row["category"] for row in body["items"]}
    assert "pharmacy" in categories
    assert all(not row["eligible"] for row in body["items"])


def test_eligibility_list_empty_database_contract_new(client) -> None:
    response = client.get("/admin/routes/eligibility?limit=50&offset=0")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_eligibility_list_unknown_city_does_not_scan_all_places_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="known-elig-city")
    place_factory(city_id=city.id, category="museum", address="ул. Музейная, 1")

    response = client.get("/admin/routes/eligibility?city_slug=missing-city&limit=50&offset=0")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_eligibility_list_bad_place_row_does_not_500_new(client, city_factory, place_factory, monkeypatch) -> None:
    from services.route_eligibility_dashboard import list_service

    city = city_factory(slug="bad-row-city")
    place = place_factory(city_id=city.id, category="museum", address="ул. Музейная, 2")

    def broken_score(_place):
        raise RuntimeError("broken quality")

    monkeypatch.setattr(list_service, "compute_place_quality_score", broken_score)
    response = client.get(f"/admin/routes/eligibility?city_slug={city.slug}&limit=50&offset=0")

    payload = response.json()
    assert response.status_code == 200
    assert payload["items"][0]["place_id"] == place.id
    assert payload["items"][0]["primary_reason"] == "row_error"


def test_data_quality_report_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-dq-city")
    place_factory(slug="dq-cafe", category="cafe", city_id=city.id)
    place_factory(slug="dq-pharm", category="pharmacy", city_id=city.id)
    response = client.get(f"/admin/routes/data-quality/{city.slug}")
    assert response.status_code == 200
    body = response.json()
    assert body["places_total"] >= 2
    assert body["suspicious_category_counts"].get("pharmacy", 0) >= 1
    assert any(i["code"] == "no_photo" for i in body["issues"])


def test_data_quality_report_includes_p0_action_plan_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-dq-action-plan")
    place_factory(slug="dq-action-cafe", category="cafe", city_id=city.id, address="")
    place_factory(slug="dq-action-pharmacy", category="pharmacy", city_id=city.id, address="")

    response = client.get(f"/admin/routes/data-quality/{city.slug}")

    assert response.status_code == 200
    body = response.json()
    codes = {item["code"] for item in body["action_plan"]}
    assert "low_route_eligible_count" in codes
    assert "review_suspicious_categories" in codes
    assert "run_address_recovery" in codes
    assert "run_image_enrichment" in codes
    assert "run_description_enrichment" in codes
    assert all(item["admin_link"].startswith(f"/admin/routes/eligibility?city_slug={city.slug}") for item in body["action_plan"])


def test_city_readiness_empty_city_new(client, city_factory) -> None:
    city = city_factory(slug="ops-ready-empty")
    response = client.get(f"/admin/routes/readiness/{city.slug}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["readiness_score"] == 0


def test_city_readiness_with_places_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-ready-ok")
    place_factory(slug="rdy-museum", category="museum", city_id=city.id,
                  lat=city.center_lat, lng=city.center_lng)
    response = client.get(f"/admin/routes/readiness/{city.slug}")
    assert response.status_code == 200
    assert response.json()["components"]["places_total"] >= 1


def test_readiness_list_new(client, city_factory) -> None:
    city_factory(slug="ops-list-a")
    city_factory(slug="ops-list-b")
    response = client.get("/admin/routes/readiness")
    assert response.status_code == 200
    slugs = {row["city_slug"] for row in response.json()["items"]}
    assert "ops-list-a" in slugs
