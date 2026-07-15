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


def test_summary_sums_original_and_bbox_fallback_results_instead_of_discarding_original():
    """Regression for production defect: Zelenogradsk showed found=136,
    saved=0 with 22 real review items already in the database. Root cause:
    run_due_import_jobs._run_expanded_bbox_fallback re-runs _apply_import a
    SECOND time (a genuinely additional, separately persisted ImportBatch —
    it never replaces the first run's already-committed Place/
    SourceObservation/review-queue rows) whenever the first run's
    created+updated+unchanged count is below MIN_SAVED_BEFORE_BBOX_FALLBACK.
    The old summarize_import_results picked ONLY the fallback's own counters
    (effective_result = fallback_import or import_result) when a fallback
    ran, so a near-empty fallback silently zeroed out a genuinely successful
    original run's real created/updated/needs_review counts in the displayed
    summary — even though those rows were still in the database. Both runs'
    counters must be summed, not have one discard the other."""
    result = summarize_import_results(
        _payload(
            {
                "raw_count": 136,
                "created": 0,
                "updated": 0,
                "needs_review": 22,
                "hidden": 0,
                "fallback_applied": True,
                "fallback_level": 1,
                "fallback_reason": "low_saved_places",
                "fallback_result": {
                    "status": "success",
                    "expansion_factor": 1.8,
                    "import_result": {
                        "raw_count": 0,
                        "created": 0,
                        "updated": 0,
                        "needs_review": 0,
                        "hidden": 0,
                    },
                },
            }
        )
    )

    assert result["places_found"] == 136
    assert result["needs_review"] == 22
    assert result["places_saved"] == 22
    assert result["meaningful_changes"] == 22


def test_summary_adds_fallback_contributions_on_top_of_original_when_both_find_places():
    """When the fallback ALSO finds real objects (not the near-empty case
    above), its contributions must add to the original run's counters, not
    replace them — both ImportBatch rows are independently persisted."""
    result = summarize_import_results(
        _payload(
            {
                "raw_count": 10,
                "created": 2,
                "updated": 1,
                "needs_review": 0,
                "hidden": 0,
                "fallback_applied": True,
                "fallback_result": {
                    "status": "success",
                    "import_result": {
                        "raw_count": 4,
                        "created": 1,
                        "updated": 0,
                        "needs_review": 1,
                        "hidden": 0,
                    },
                },
            }
        )
    )

    assert result["places_found"] == 14
    assert result["created"] == 3
    assert result["updated"] == 1
    assert result["needs_review"] == 1
    assert result["places_saved"] == 5
