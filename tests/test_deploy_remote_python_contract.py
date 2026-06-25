from pathlib import Path


def test_remote_deploy_uses_available_host_python_interpreter() -> None:
    script = Path("scripts/deploy_production_remote.sh").read_text(encoding="utf-8")

    assert "HOST_PYTHON=\"$(command -v python3 || command -v python || true)\"" in script
    assert "\"$HOST_PYTHON\" - <<'PY'" in script
    assert "\npython - <<'PY'" not in script


def test_remote_deploy_fails_fast_when_no_python_is_available() -> None:
    script = Path("scripts/deploy_production_remote.sh").read_text(encoding="utf-8")

    assert "neither python3 nor python is available" in script
    assert "Cannot update /srv/app/.env safely" in script
