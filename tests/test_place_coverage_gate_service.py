from services.place_coverage_gate_service import CoverageGateThresholds, evaluate_coverage_gate


def _report() -> dict[str, object]:
    return {
        "total_places": 100,
        "with_coordinates": 98,
        "with_opening_hours": 75,
        "with_visit_duration": 82,
        "category_counts": {
            "coffee": 10,
            "food": 20,
            "walk": 12,
            "museum": 5,
            "bar": 4,
            "park": 7,
        },
    }


def test_evaluate_coverage_gate_passes_when_thresholds_are_met() -> None:
    result = evaluate_coverage_gate(_report())

    assert result.passed is True
    assert result.failures == ()


def test_evaluate_coverage_gate_reports_ratio_failure() -> None:
    report = {**_report(), "with_opening_hours": 30}

    result = evaluate_coverage_gate(report)

    assert result.passed is False
    assert result.failures == ("with_opening_hours ratio 0.300 is below 0.700",)


def test_evaluate_coverage_gate_reports_missing_required_categories() -> None:
    report = {**_report(), "category_counts": {"coffee": 1}}

    result = evaluate_coverage_gate(report)

    assert result.passed is False
    assert result.failures == ("required categories missing: food, walk, museum, bar, park",)


def test_evaluate_coverage_gate_reports_invalid_payload_fields() -> None:
    result = evaluate_coverage_gate({"total_places": "100", "category_counts": []})

    assert result.passed is False
    assert "total_places is missing or invalid" in result.failures
    assert "with_coordinates is missing or invalid" in result.failures


def test_evaluate_coverage_gate_accepts_custom_thresholds() -> None:
    thresholds = CoverageGateThresholds(min_total_places=1, required_categories=("coffee",))

    result = evaluate_coverage_gate({"total_places": 1, "with_coordinates": 1,
                                     "with_opening_hours": 1, "with_visit_duration": 1,
                                     "category_counts": {"coffee": 1}}, thresholds)

    assert result.passed is True
