from schemas.user_route import UserRouteState
from services.user_route_state_registry_service import register_initial_route_state
from tests.allure_support import title


def _route_payload(city_slug="flex-city"):
    return {
        "lat": 54.96,
        "lng": 20.48,
        "start_source": "city_center",
        "build_mode": "auto",
        "time_budget_minutes": 120,
        "route_time_mode": "flexible",
        "interests": [],
        "avoided_categories": [],
        "excluded_place_ids": [],
        "budget_level": None,
        "pace_mode": None,
        "is_visiting": False,
        "city_id": city_slug,
        "visit_city_id": None,
        "visit_days": None,
        "user_id": "test-user",
    }


def _state(place_ids, city_slug="flex-city"):
    return {
        "route_id": "route-1",
        "revision": 1,
        "status": "ready",
        "partial_reason": None,
        "context": _route_payload(city_slug),
        "total_places": len(place_ids),
        "total_minutes": 60,
        "total_estimated_minutes": 70,
        "estimated_distance": 1.0,
        "estimated_end_time": None,
        "has_warnings": False,
        "warning_count": 0,
        "places_with_warnings": [],
        "quality_score": 0.7,
        "quality_breakdown": {},
        "total_walk_distance_meters": 0,
        "time_breakdown": {},
        "category_distribution": {},
        "warnings": [],
        "user_warnings": [],
        "points": [
            {
                "place_id": str(place_id),
                "city_slug": city_slug,
                "position": index,
                "title": f"Место {place_id}",
                "address": None,
                "image_url": None,
                "short_description": None,
                "source": None,
                "lat": 54.96 + index / 10000,
                "lng": 20.48 + index / 10000,
                "category": "cafe" if index == 1 else "walk",
                "visit_minutes": 30,
                "estimated_walk_minutes": 1,
                "estimated_arrival_time": None,
                "estimated_departure_time": None,
                "time_status": None,
                "time_warning": None,
                "scoring_breakdown": {},
            }
            for index, place_id in enumerate(place_ids, 1)
        ],
        "explanation": {},
    }


def _issued_state(db_session, place_ids, city_slug):
    issued = register_initial_route_state(db_session, UserRouteState.model_validate(_state(place_ids, city_slug)))
    db_session.commit()
    return issued.model_dump(mode="json")


@title("Предпросмотр пользовательского маршрута возвращается без публикации")
def test_user_route_preview_returns_preview_status_new(client, city_factory, place_factory):
    city = city_factory(slug="preview-city", name="Preview City")
    place_factory(slug="preview-place", title="Preview Place", city_id=city.id, category="walk")
    response = client.post("/v1/user-routes/preview", json=_route_payload("preview-city"))
    assert response.status_code == 200
    assert response.json()["status"] == "preview"


def test_user_route_build_structured_returns_slot_options_new(client, city_factory, place_factory):
    city = city_factory(slug="slot-city", name="Slot City")
    place_factory(slug="slot-cafe-1", title="Кофе 1", city_id=city.id, category="cafe")
    place_factory(slug="slot-cafe-2", title="Кофе 2", city_id=city.id, category="cafe")
    payload = {**_route_payload("slot-city"), "build_mode": "constructor", "slots": [{"slot_id": "s1", "category": "cafe", "preferred_place_id": None}]}
    response = client.post("/v1/user-routes/build-structured", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "slot-city"
    assert data["slots"][0]["slot_id"] == "s1"
    assert len(data["slots"][0]["options"]) >= 1


def test_user_route_update_reorders_existing_places_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="update-city", name="Update City")
    first = place_factory(slug="update-first", title="Первое", city_id=city.id, category="cafe")
    second = place_factory(slug="update-second", title="Второе", city_id=city.id, category="walk")
    response = client.post(
        "/v1/user-routes/route-1/update",
        json={"current_route": _issued_state(db_session, [first.id, second.id], "update-city"), "ordered_place_ids": [str(second.id), str(first.id)]},
    )
    assert response.status_code == 200
    assert response.json()["points"][0]["place_id"] == str(second.id)


def test_user_route_replace_place_updates_route_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="replace-city", name="Replace City")
    old = place_factory(slug="replace-old", title="Старое", city_id=city.id, category="cafe")
    new = place_factory(slug="replace-new", title="Новое", city_id=city.id, category="cafe")
    response = client.post(
        "/v1/user-routes/route-1/replace-place",
        json={"current_route": _issued_state(db_session, [old.id], "replace-city"), "old_place_id": str(old.id), "new_place_id": str(new.id)},
    )
    assert response.status_code == 200
    assert response.json()["points"][0]["place_id"] == str(new.id)


def test_user_route_add_place_appends_place_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="add-city", name="Add City")
    first = place_factory(slug="add-first", title="Первое", city_id=city.id, category="cafe")
    added = place_factory(slug="add-added", title="Добавленное", city_id=city.id, category="walk")
    response = client.post(
        "/v1/user-routes/route-1/add-place",
        json={"current_route": _issued_state(db_session, [first.id], "add-city"), "place_id": str(added.id)},
    )
    assert response.status_code == 200
    assert [point["place_id"] for point in response.json()["points"]] == [str(first.id), str(added.id)]


def test_user_route_alternatives_from_state_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="alt-city", name="Alt City")
    current = place_factory(slug="alt-current", title="Текущее", city_id=city.id, category="cafe")
    place_factory(slug="alt-new", title="Альтернатива", city_id=city.id, category="cafe")
    response = client.post(
        f"/v1/user-routes/route-1/alternatives/{current.id}",
        json=_issued_state(db_session, [current.id], "alt-city"),
    )
    assert response.status_code == 200
    assert response.json()["route_id"] == "route-1"
    assert len(response.json()["options"]) >= 1
