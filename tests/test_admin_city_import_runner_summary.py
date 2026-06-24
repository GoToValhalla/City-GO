from services.admin_city_import_runner import summarize_import_results


def _payload(import_result):
    return {
        "results": [
            {
                "scope": "center",
                "status": "success",
                "import_result": import_result,
            }
        ]
    }


def test_summary_reports_zero_changes_for_unchanged_import():
    result = summarize_import_results(_payload({"raw_count": 5, "unchanged": 5}))

    assert result["status"] == "success"
    assert result["places_found"] == 5
    assert result["unchanged"] == 5
    assert result["meaningful_changes"] == 0
    assert result["places_saved"] == 0


def test_summary_counts_review_and_hidden_changes():
    result = summarize_import_results(
        _payload(
            {
                "raw_count": 7,
                "created": 2,
                "updated": 1,
                "needs_review": 3,
                "hidden": 1,
            }
        )
    )

    assert result["places_saved"] == 6
    assert result["meaningful_changes"] == 7
