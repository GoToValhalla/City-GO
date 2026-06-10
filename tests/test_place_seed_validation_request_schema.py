from schemas.place_seed_validation_request import PlaceSeedValidationRequest


def test_place_seed_validation_request_defaults() -> None:
    request = PlaceSeedValidationRequest()

    assert request.items == []


def test_place_seed_validation_request_accepts_items() -> None:
    request = PlaceSeedValidationRequest(
        items=[
            {
                "title": "Coffee Point",
                "slug": "coffee-point",
                "city_slug": "zelenogradsk",
                "category": "coffee",
                "taxonomy": {
                    "category": "coffee",
                    "tags": [],
                    "scenario_tags": [],
                    "vibe_tags": [],
                    "restriction_tags": [],
                },
            }
        ]
    )

    assert len(request.items) == 1
    assert request.items[0].title == "Coffee Point"
    assert request.items[0].slug == "coffee-point"
