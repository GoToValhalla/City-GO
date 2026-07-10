"""Static safety checks for .github/workflows/deploy.yml — prevents a repeat
of the incident where docker load/docker compose up hung indefinitely with
no execution timeout, and where an unconditional `docker image prune -af`
could delete the previous known-good rollback image before the new one was
confirmed healthy. Also covers the Phase 1 CI/deploy/smoke optimization:
parallel backend/frontend image builds, exact-SHA CI validation manifest
gating, and the single post-readiness import-worker invariant check."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def _read() -> str:
    return DEPLOY_WORKFLOW.read_text(encoding="utf-8")


def _yaml() -> dict:
    return yaml.safe_load(_read())


def test_deploy_workflow_is_valid_yaml_new() -> None:
    data = _yaml()
    assert "jobs" in data
    assert set(data["jobs"].keys()) == {"resolve-and-gate", "build-backend", "build-frontend", "deploy", "notify"}


def test_deploy_workflow_stays_manual_only_new() -> None:
    data = _yaml()
    triggers = data[True]  # PyYAML parses the `on:` key as boolean True
    assert set(triggers.keys()) == {"workflow_dispatch"}


def test_docker_load_is_wrapped_in_timeout_new() -> None:
    text = _read()
    assert "timeout 300s docker load -i" in text
    assert "ERROR: docker load timed out or failed" in text


def test_docker_compose_up_is_wrapped_in_timeout_new() -> None:
    text = _read()
    assert "timeout 180s docker compose up -d --remove-orphans" in text
    assert "ERROR: docker compose up timed out or failed" in text


def test_timeout_exit_codes_are_not_swallowed_new() -> None:
    """A timeout/failure must actually fail the step, not be hidden by `|| true`."""
    text = _read()
    assert 'exit "$LOAD_STATUS"' in text
    assert 'exit "$UP_STATUS"' in text


def test_aggressive_image_prune_only_runs_after_health_verification_new() -> None:
    """docker image prune -af must not run before the new image is loaded and
    confirmed healthy — otherwise it can delete the only rollback path."""
    text = _read()
    deploy_on_server_idx = text.index("name: Deploy on server")
    verify_ready_idx = text.index("name: Verify backend ready")
    cleanup_idx = text.index("name: Cleanup old images after confirmed healthy deploy")
    prune_af_idx = text.index("docker image prune -af")

    assert deploy_on_server_idx < verify_ready_idx < cleanup_idx
    assert prune_af_idx > verify_ready_idx, "docker image prune -af must appear after the health-check step, not before"


def test_deploy_on_server_step_no_longer_prunes_all_images_new() -> None:
    """The risky pre-load section must only do safe, non-tag-deleting cleanup."""
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    deploy_section = text[deploy_start:verify_build_json_start]

    assert "docker image prune -af" not in deploy_section
    assert "docker container prune -f" in deploy_section
    assert "docker builder prune -f" in deploy_section


def test_rollback_sha_metadata_is_recorded_new() -> None:
    text = _read()
    assert ".last_deployed_sha" in text
    assert "Previous deployed SHA" in text
    assert "Attempted SHA" in text


def test_failure_diagnostics_present_on_ready_check_failure_new() -> None:
    text = _read()
    verify_ready_start = text.index("name: Verify backend ready")
    cleanup_start = text.index("name: Cleanup old images after confirmed healthy deploy")
    section = text[verify_ready_start:cleanup_start]

    assert "docker compose ps" in section
    assert "Disk free" in section
    assert "Docker image list summary" in section
    assert "docker compose logs" in section


def test_backend_and_frontend_build_jobs_are_independent_new() -> None:
    """build-backend and build-frontend must both depend only on
    resolve-and-gate (not on each other), so GitHub Actions can run them in
    parallel."""
    data = _yaml()
    jobs = data["jobs"]

    assert jobs["build-backend"]["needs"] == "resolve-and-gate"
    assert jobs["build-frontend"]["needs"] == "resolve-and-gate"


def test_deploy_job_waits_for_both_builds_new() -> None:
    data = _yaml()
    needs = data["jobs"]["deploy"]["needs"]
    assert set(needs) == {"resolve-and-gate", "build-backend", "build-frontend"}


def test_backend_image_publish_depends_on_import_smoke_new() -> None:
    """Backend import smoke must run and pass before the image is pushed."""
    text = _read()
    build_backend_start = text.index("build-backend:")
    build_frontend_start = text.index("build-frontend:")
    section = text[build_backend_start:build_frontend_start]

    smoke_idx = section.index("Backend import smoke inside image")
    push_idx = section.index("name: Push backend image")
    assert smoke_idx < push_idx


def test_exact_sha_tags_are_used_new() -> None:
    text = _read()
    assert "${{ needs.resolve-and-gate.outputs.backend_image }}:${{ env.DEPLOY_TARGET_SHA }}" in text
    assert "${{ needs.resolve-and-gate.outputs.frontend_image }}:${{ env.DEPLOY_TARGET_SHA }}" in text
    assert 'docker pull "$BACKEND_IMAGE:${DEPLOY_TARGET_SHA}"' in text
    assert 'docker pull "$FRONTEND_IMAGE:${DEPLOY_TARGET_SHA}"' in text


def test_deploy_verifies_ci_validation_manifest_new() -> None:
    text = _read()
    assert "ci_validate_manifest.py verify" in text
    assert "--expected-sha" in text
    assert "ci-validation-manifest" in text


def test_deploy_fails_closed_when_manifest_download_fails_new() -> None:
    text = _read()
    resolve_start = text.index("resolve-and-gate:")
    build_backend_start = text.index("build-backend:")
    section = text[resolve_start:build_backend_start]

    assert "gh run download" in section
    assert "Deploy fails closed" in section
    assert "exit 1" in section


def test_no_direct_production_ghcr_pull_new() -> None:
    """The production host must never pull images directly from GHCR — the
    runner pulls, saves, gzips, and SCPs the archive; production only loads
    a local file."""
    text = _read()
    deploy_on_server_start = text.index("name: Deploy on server")
    cleanup_start = text.index("name: Cleanup old images after confirmed healthy deploy")
    remote_section = text[deploy_on_server_start:cleanup_start]

    assert "docker pull" not in remote_section
    assert "docker load -i /tmp/city-go-images.tar.gz" in remote_section


def test_import_worker_final_invariant_check_appears_once_new() -> None:
    """The import-worker-must-not-be-running check must be enforced once,
    at the final post-readiness point, not duplicated across multiple steps."""
    text = _read()
    assert text.count("Final invariant: import-worker must not be running") == 1
    # The pre-existing "Ensure import-worker stays stopped after deploy"
    # duplicate check (previously present both in "Deploy on server" and
    # "Verify backend ready") must not remain as a separate step anymore.
    assert "Ensure import-worker stays stopped after deploy" not in text


def test_import_worker_invariant_stops_and_fails_if_running_new() -> None:
    text = _read()
    final_check_idx = text.index("Final invariant: import-worker must not be running")
    section = text[final_check_idx:final_check_idx + 1500]

    assert 'docker compose stop import-worker || true' in section
    assert "exit 1" in section


def test_no_automatic_deploy_trigger_new() -> None:
    data = _yaml()
    triggers = data[True]
    assert "push" not in triggers
    assert "schedule" not in triggers
    assert "workflow_run" not in triggers


def test_build_backend_and_frontend_use_gha_cache_new() -> None:
    text = _read()
    assert "cache-from: type=gha,scope=city-go-backend" in text
    assert "cache-to: type=gha,mode=max,scope=city-go-backend" in text
    assert "cache-from: type=gha,scope=city-go-frontend" in text
    assert "cache-to: type=gha,mode=max,scope=city-go-frontend" in text


def test_image_digest_is_recorded_before_transport_new() -> None:
    text = _read()
    assert "RepoDigests" in text
