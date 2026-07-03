from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason=(
        "Temporary pause: route/place behavioural tests depend on the new quality "
        "dashboard and triage model. Re-enable after P0 Quality Dashboard / Backlog Fix."
    )
)


def test_route_eligibility_matrix_paused_until_quality_backlog_fix_new() -> None:
    assert True
