"""Static safety checks for .github/workflows/deploy.yml — prevents a repeat
of the incident where docker load/docker compose up hung indefinitely with
no execution timeout, and where an unconditional `docker image prune -af`
could delete the previous known-good rollback image before the new one was
confirmed healthy. Also covers the Phase 1 CI/deploy/smoke optimization:
parallel backend/frontend image builds, exact-SHA CI validation manifest
gating, and the single post-readiness import-worker invariant check."""

from __future__ import annotations

import platform
import subprocess
import tempfile
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


def test_archive_uses_gzip_level_1_new() -> None:
    text = _read()
    save_idx = text.index('docker save "$BACKEND_IMAGE:latest" "$FRONTEND_IMAGE:latest"')
    line_end = text.index("\n", save_idx)
    assert "gzip -1" in text[save_idx:line_end]
    assert "gzip -6 " not in text[save_idx:line_end]
    assert "gzip -6>" not in text[save_idx:line_end]


def test_archive_size_is_recorded_and_kept_separate_from_transfer_timing_new() -> None:
    text = _read()
    save_start = text.index("name: Download images from GHCR on runner")
    copy_compose_start = text.index("name: Copy compose file to server")
    save_section = text[save_start:copy_compose_start]

    assert "archive_size_bytes=" in save_section
    assert "archive_size_mib=" in save_section
    assert "timing_download_save_seconds=" in save_section

    transfer_start = text.index("name: Copy images archive to server")
    transfer_section = text[transfer_start:transfer_start + 900]
    assert "archive_size_bytes=" not in transfer_section
    assert "timing_transfer_seconds=" in transfer_section


def test_timing_summary_includes_archive_size_new() -> None:
    text = _read()
    summary_idx = text.rindex("name: Timing summary")
    section = text[summary_idx:summary_idx + 900]
    assert "archive_size_bytes" in section
    assert "archive_size_mib" in section


def test_deploy_validates_telegram_mini_app_url_before_replacing_containers_new() -> None:
    """Prevents a repeat of the incident where the Telegram Mini App button
    silently disappeared in production: TELEGRAM_MINI_APP_URL lived only in
    the host .env file, which deploy.yml never validated, so a missing or
    malformed value was never caught before rollout."""
    text = _read()
    assert "TELEGRAM_MINI_APP_URL" in text
    assert "/srv/app/.env" in text

    config_idx = text.index("docker compose config --quiet")
    ensure_idx = text.index("Ensure TELEGRAM_MINI_APP_URL")
    validate_idx = text.index("Validate TELEGRAM_MINI_APP_URL")
    stop_idx = text.index("docker compose stop frontend backend import-worker bot")
    assert config_idx < ensure_idx < validate_idx < stop_idx


def test_deploy_idempotently_writes_telegram_mini_app_url_default_new() -> None:
    """The deploy must self-heal a missing/invalid TELEGRAM_MINI_APP_URL in
    /srv/app/.env by writing the known-good production Mini App URL, rather
    than only failing the deploy and requiring a manual SSH fix."""
    text = _read()
    ensure_idx = text.index("Ensure TELEGRAM_MINI_APP_URL")
    validate_idx = text.index("Validate TELEGRAM_MINI_APP_URL")
    section = text[ensure_idx:validate_idx]

    assert "https://citygo.autismishe.online/telegram" in section
    assert "sed -i '/^TELEGRAM_MINI_APP_URL=/d' /srv/app/.env" in section
    assert 'echo "TELEGRAM_MINI_APP_URL=${DEFAULT_MINI_APP_URL}" >> /srv/app/.env' in section

    # Idempotent: touching .env before the grep must not fail if the file
    # doesn't exist yet, and running the block twice must not duplicate the line.
    assert "touch /srv/app/.env" in section


def _extract_mini_app_shell_block() -> str:
    """Extract the exact Ensure+Validate TELEGRAM_MINI_APP_URL shell lines
    from deploy.yml's remote heredoc, de-indented for standalone execution."""
    text = _read()
    start = text.index('echo "=== Ensure TELEGRAM_MINI_APP_URL')
    end = text.index('echo "=== Recording rollback metadata')
    raw_lines = text[start:end].splitlines()
    return "\n".join(line[10:] if line.startswith(" " * 10) else line for line in raw_lines)


def test_mini_app_url_block_survives_missing_env_line_under_strict_mode_new() -> None:
    """Regression for the exact incident: under `set -euo pipefail`, a `grep`
    command substitution with no match exits non-zero and kills the script
    before the auto-heal write ever runs, even though `2>/dev/null` only
    silences stderr and does nothing to the exit status. Executes the real
    Ensure+Validate block extracted from deploy.yml against a .env with no
    TELEGRAM_MINI_APP_URL line at all — the scenario confirmed on the
    production host — and asserts the process does not die early, the
    default URL is written, and validation subsequently passes (proving
    the deploy would actually continue)."""
    if platform.system() != "Linux":
        import pytest

        pytest.skip("deploy.yml's sed -i syntax is GNU-only; production/CI run on Linux")

    block = _extract_mini_app_shell_block()
    assert "/srv/app/.env" in block, "expected deploy.yml to reference /srv/app/.env; substitution below would no-op"

    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / ".env"
        env_path.write_text("FOO=bar\n", encoding="utf-8")

        # The real block hardcodes the absolute production path; substitute it
        # with the isolated temp file so this test never touches /srv/app.
        isolated_block = block.replace("/srv/app/.env", str(env_path))

        script = f"set -euo pipefail\n{isolated_block}\ncat {env_path}\necho DEPLOY_WOULD_CONTINUE\n"
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"shell block exited non-zero under set -euo pipefail with a missing "
            f"TELEGRAM_MINI_APP_URL line (stdout={result.stdout!r} stderr={result.stderr!r})"
        )
        assert "TELEGRAM_MINI_APP_URL=https://citygo.autismishe.online/telegram" in result.stdout
        assert "DEPLOY_WOULD_CONTINUE" in result.stdout
