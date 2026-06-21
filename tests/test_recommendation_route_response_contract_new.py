from schemas.recommendation_route import RecommendationRoutePointResponse


def test_route_point_response_accepts_string_and_boolean_scoring_metadata_new() -> None:
    point = RecommendationRoutePointResponse.model_validate(
        {
            "place_id": "1",
            "lat": 61.0,
            "lng": 69.0,
            "category": "museum",
            "visit_minutes": 30,
            "scoring_breakdown": {
                "score": 0.91,
                "route_assembly_fallback": "emergency_seed",
                "long_walk_segment": True,
            },
        }
    )

    assert point.scoring_breakdown["route_assembly_fallback"] == "emergency_seed"
    assert point.scoring_breakdown["long_walk_segment"] is True
