import importlib
import json


def test_admin_deployment_defaults_point_to_city_go_deploy(monkeypatch):
    for key in ("GITHUB_DEPLOY_REPO", "GITHUB_DEPLOY_WORKFLOW", "GITHUB_DEPLOY_BRANCH"):
        monkeypatch.delenv(key, raising=False)

    from routers import admin_place_ops

    module = importlib.reload(admin_place_ops)

    assert module.GITHUB_REPO == "GoToValhalla/City-GO"
    assert module.GITHUB_WORKFLOW == "deploy.yml"
    assert module.GITHUB_BRANCH == "main"


def test_admin_deployment_dispatch_passes_deploy_ref_to_deploy_workflow(monkeypatch):
    for key in ("GITHUB_DEPLOY_REPO", "GITHUB_DEPLOY_WORKFLOW"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GITHUB_DEPLOY_BRANCH", "release-test")

    from routers import admin_place_ops

    module = importlib.reload(admin_place_ops)
    payload = json.loads(module._workflow_dispatch_payload().decode("utf-8"))

    assert payload == {"ref": "release-test", "inputs": {"deploy_ref": "release-test"}}


def test_admin_deployment_dispatch_keeps_legacy_ci_payload_without_inputs(monkeypatch):
    monkeypatch.setenv("GITHUB_DEPLOY_REPO", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_DEPLOY_WORKFLOW", "ci.yml")
    monkeypatch.setenv("GITHUB_DEPLOY_BRANCH", "main")

    from routers import admin_place_ops

    module = importlib.reload(admin_place_ops)
    payload = json.loads(module._workflow_dispatch_payload().decode("utf-8"))

    assert payload == {"ref": "main"}


def test_admin_api_watchdog_checks_route_eligibility():
    from scripts.check_production_admin_api import CHECKS

    assert "/api/admin/routes/eligibility?limit=50&offset=0" in {check.path for check in CHECKS}
