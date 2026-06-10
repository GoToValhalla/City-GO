from datetime import datetime

from services.place_search_response_service import build_place_search_response


def test_build_place_search_response_returns_expected_structure() -> None:
    items = [
        {
            "id": 1,
            "title": "Coffee Point",
            "slug": "coffee-point",
            "city_id": 1,
            "category_id": 2,
            "short_description": "Good coffee place",
            "category": "coffee",
            "address": "Kurortny Prospekt 12",
            "lat": 54.964,
            "lng": 20.475,
            "price_level": 1,
            "dog_friendly": False,
            "family_friendly": False,
            "indoor": False,
            "outdoor": False,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    ]

    response = build_place_search_response(
        items=items,
        total=1,
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0
    assert len(response.items) == 1
    assert response.items[0].id == 1
    assert response.items[0].title == "Coffee Point"
    assert response.items[0].slug == "coffee-point"