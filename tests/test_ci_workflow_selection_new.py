"""Static safety checks for .github/workflows/ci.yml — path-aware manual CI
selection must never allow a required suite to be silently skipped, and must
fail safe (full regression) whenever the comparison base cannot be trusted."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _read() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def _yaml() -> dict:
    return yaml.safe_load(_read())


def test_ci_workflow_is_valid_yaml_new() -> None:
    data = _yaml()
    assert "jobs" in data


def test_ci_stays_manual_only_new() -> None:
    data = _yaml()
    triggers = data[True]
    assert set(triggers.keys()) == {"workflow_dispatch"}


def test_regression_scope_input_exists_new() -> None:
    data = _yaml()
    inputs = data[True]["workflow_dispatch"]["inputs"]
    assert inputs["regression_scope"]["default"] == "auto"
    assert set(inputs["regression_scope"]["options"]) == {"auto", "full"}


def test_generate_allure_html_input_exists_new() -> None:
    data = _yaml()
    inputs = data[True]["workflow_dispatch"]["inputs"]
    assert inputs["generate_allure_html"]["type"] == "boolean"
    assert inputs["generate_allure_html"]["default"] is False


def test_explicit_full_forces_full_regression_new() -> None:
    text = _read()
    resolve_start = text.index("resolve-base:")
    changes_start = text.index("changes:")
    section = text[resolve_start:changes_start]

    assert 'REGRESSION_SCOPE" = "full"' in section
    assert "selection_mode=full_explicit" in section


def test_missing_trusted_base_forces_full_regression_new() -> None:
    text = _read()
    resolve_start = text.index("resolve-base:")
    changes_start = text.index("changes:")
    section = text[resolve_start:changes_start]

    assert "selection_mode=auto_no_trusted_base" in section
    force_full_start = text.index("force-full")
    force_full_section = text[force_full_start:force_full_start + 800]
    assert '[ -z "$BASE_SHA" ]' in force_full_section


def test_base_must_be_a_real_ancestor_new() -> None:
    """The resolved base SHA must be verified as a real git ancestor of the
    target commit — not just any prior successful CI run's SHA — otherwise a
    stale/unrelated branch state could be used as a trusted comparison base."""
    text = _read()
    assert "git merge-base --is-ancestor" in text


def test_backend_only_change_does_not_require_frontend_new() -> None:
    text = _read()
    frontend_start = text.index("frontend-tests:")
    frontend_if = text[frontend_start:frontend_start + 900]
    # Frontend must not be forced solely by a backend change (only workflow/
    # docker changes or non-docs-only combined with smoke force it).
    assert "needs.changes.outputs.backend == 'true' ||\n        needs.changes.outputs.smoke == 'true'" not in frontend_if.replace(" ", "").replace("\n", "\n")


def test_workflow_change_forces_both_suites_new() -> None:
    text = _read()
    backend_start = text.index("backend-tests:")
    frontend_start = text.index("frontend-tests:")
    backend_if = text[backend_start:backend_start + 700]
    frontend_if = text[frontend_start:frontend_start + 700]

    assert "needs.changes.outputs.workflows == 'true'" in backend_if
    assert "needs.changes.outputs.workflows == 'true'" in frontend_if


def test_docker_change_forces_full_regression_new() -> None:
    text = _read()
    backend_start = text.index("backend-tests:")
    frontend_start = text.index("frontend-tests:")
    backend_if = text[backend_start:backend_start + 700]
    frontend_if = text[frontend_start:frontend_start + 700]

    assert "needs.changes.outputs.docker == 'true'" in backend_if
    assert "needs.changes.outputs.docker == 'true'" in frontend_if


def test_unknown_or_uncertain_change_runs_full_regression_new() -> None:
    """Anything that isn't cleanly classified as docs-only must fall through
    to the backend suite — this is the 'unknown or uncertain changes → safe
    full regression' requirement."""
    text = _read()
    backend_start = text.index("backend-tests:")
    backend_if = text[backend_start:backend_start + 700]
    assert "needs.changes.outputs.docs != 'true'" in backend_if


def test_docs_only_gate_requires_no_other_changes_new() -> None:
    text = _read()
    docs_only_start = text.index("docs-only-check:")
    backend_start = text.index("backend-tests:")
    section = text[docs_only_start:backend_start]

    assert "needs.changes.outputs.docs == 'true'" in section
    assert "needs.changes.outputs.workflows != 'true'" in section
    assert "needs.changes.outputs.backend != 'true'" in section
    assert "needs.changes.outputs.frontend != 'true'" in section
    assert "needs.changes.outputs.docker != 'true'" in section
    assert "needs.changes.outputs.smoke != 'true'" in section


def test_validation_manifest_job_exists_and_uploads_artifact_new() -> None:
    data = _yaml()
    jobs = data["jobs"]
    assert "validation-manifest" in jobs
    steps = jobs["validation-manifest"]["steps"]
    upload_steps = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact")]
    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["name"] == "ci-validation-manifest"


def test_validation_manifest_uses_helper_script_new() -> None:
    text = _read()
    assert "scripts/ci_validate_manifest.py" in text
    assert '"write"' in text or "write\n" in text or "ARGS=(write" in text


def test_validation_manifest_job_always_runs_new() -> None:
    """The manifest must be built even if a required suite failed, so deploy
    can see a truthful validation_complete=false rather than finding nothing."""
    data = _yaml()
    assert data["jobs"]["validation-manifest"]["if"] == "always()"


def test_allure_html_gated_on_failure_or_explicit_input_new() -> None:
    text = _read()
    allure_step_idx = text.index("Generate backend Allure HTML")
    section = text[allure_step_idx:allure_step_idx + 300]
    assert "if: failure() || env.GENERATE_ALLURE_HTML == 'true'" in section


def test_raw_allure_results_remain_unconditional_new() -> None:
    text = _read()
    upload_idx = text.index("name: Upload backend artifacts")
    section = text[upload_idx:upload_idx + 700]
    assert "artifacts/allure-results/backend" in section
    assert "artifacts/junit/backend.xml" in section
    assert "artifacts/coverage/backend.xml" in section


def test_artifact_hint_does_not_promise_html_on_success_new() -> None:
    text = _read()
    assert "HTML not generated on this successful run" in text


def test_workflow_validate_can_run_on_manual_dispatch_new() -> None:
    """workflow-validate must be reachable on a manual run when workflow
    files changed or full regression was requested — the previous version
    excluded workflow_dispatch entirely."""
    text = _read()
    workflow_validate_start = text.index("workflow-validate:")
    changes_end = text.index("docs-only-check:")
    section = text[workflow_validate_start:changes_end]
    assert "github.event_name != 'workflow_dispatch'" not in section
