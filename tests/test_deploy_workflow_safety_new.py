"""Static safety checks for .github/workflows/deploy.yml — prevents a repeat
of the incident where docker load/docker compose up hung indefinitely with
no execution timeout, and where an unconditional `docker image prune -af`
could delete the previous known-good rollback image before the new one was
confirmed healthy."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def _read() -> str:
    return DEPLOY_WORKFLOW.read_text(encoding="utf-8")


def test_deploy_workflow_is_valid_yaml_new() -> None:
    data = yaml.safe_load(_read())
    assert "jobs" in data
    assert set(data["jobs"].keys()) == {"build", "deploy", "notify"}


def test_deploy_workflow_stays_manual_only_new() -> None:
    data = yaml.safe_load(_read())
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
