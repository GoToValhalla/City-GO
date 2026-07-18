from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

import services.user_route_state_integrity as integrity
import services.user_route_state_lifecycle_service as lifecycle_module
from services.user_route_mutation_result import RouteMutationResult
from services.user_route_state_lifecycle_service import (
    RouteStateLifecycleService,
    UserRouteMutationRejectedError,
)

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_PATH = ROOT / "services/user_route_state_lifecycle_service.py"


def test_rejected_mutation_never_advances_revision_new(monkeypatch) -> None:
    called = False

    def fake_advance(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("rejected mutation advanced registry")

    monkeypatch.setattr(lifecycle_module, "advance_route_state", fake_advance)

    with pytest.raises(UserRouteMutationRejectedError, match="rejected"):
        RouteStateLifecycleService._issue_accepted(
            object(),
            SimpleNamespace(),
            RouteMutationResult.rejected("rejected"),
            object(),
        )

    assert called is False


def test_accepted_mutation_is_the_only_path_to_advance_new(monkeypatch) -> None:
    expected = object()
    state = SimpleNamespace()

    def fake_sanitize(value):
        assert value is state
        return value

    def fake_advance(_db, *, previous, next_state, registry):
        assert previous is not None
        assert next_state is state
        assert registry is not None
        return expected

    monkeypatch.setattr(lifecycle_module, "sanitize_user_route_state", fake_sanitize)
    monkeypatch.setattr(lifecycle_module, "advance_route_state", fake_advance)

    result = RouteStateLifecycleService._issue_accepted(
        object(),
        SimpleNamespace(),
        RouteMutationResult.success(state),
        object(),
    )

    assert result is expected


def test_mutation_services_use_typed_outcomes_new() -> None:
    edit_source = (ROOT / "services/user_route_edit_service.py").read_text(encoding="utf-8")
    correct_source = (ROOT / "services/user_route_correct_service.py").read_text(encoding="utf-8")
    lifecycle_source = LIFECYCLE_PATH.read_text(encoding="utf-8")

    assert "RouteMutationResult" in edit_source
    assert "RouteMutationResult" in correct_source
    assert "_safe_failure" not in edit_source
    assert "result.accepted" in lifecycle_source
    assert "result.state is None" in lifecycle_source


def test_only_lifecycle_owner_calls_route_mutation_methods_new() -> None:
    forbidden_methods = {"correct", "update_order", "replace_place", "add_place"}
    violations: list[str] = []

    for directory in (ROOT / "routers", ROOT / "services", ROOT / "core"):
        for path in directory.rglob("*.py"):
            if path == LIFECYCLE_PATH:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr not in forbidden_methods:
                    continue
                receiver = node.func.value
                receiver_text = ast.unparse(receiver) if hasattr(ast, "unparse") else ""
                if "UserRouteEditService" in receiver_text or "UserRouteCorrectService" in receiver_text:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.func.attr}")

    assert not violations, "route mutation bypasses lifecycle owner:\n" + "\n".join(violations)


def test_noop_mutations_are_explicitly_rejected_new() -> None:
    edit_source = (ROOT / "services/user_route_edit_service.py").read_text(encoding="utf-8")
    correct_source = (ROOT / "services/user_route_correct_service.py").read_text(encoding="utf-8")

    assert "requested_ids == current_ids" in edit_source
    assert "request.new_place_id == request.old_place_id" in edit_source
    assert "Коррекция не изменила маршрут" in correct_source
    assert "Коррекция не изменила параметры маршрута" in correct_source


def test_route_readiness_is_not_overwritten_by_action_labels_new() -> None:
    mapper_source = (ROOT / "services/user_route_mapper.py").read_text(encoding="utf-8")
    recalc_source = (ROOT / "services/user_route_recalc_service.py").read_text(encoding="utf-8")
    correct_source = (ROOT / "services/user_route_correct_service.py").read_text(encoding="utf-8")

    assert 'status="corrected"' not in recalc_source
    assert 'status="corrected"' not in correct_source
    assert "status: str | None" not in mapper_source
    assert "final_route_to_state(final, intent, revision=revision)" in recalc_source


def test_no_runtime_mapper_call_can_override_readiness_status_new() -> None:
    violations: list[str] = []

    for directory in (ROOT / "services", ROOT / "routers", ROOT / "core"):
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
                if name != "final_route_to_state":
                    continue
                if any(keyword.arg == "status" for keyword in node.keywords):
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}")

    assert not violations, "readiness status overridden by mapper caller:\n" + "\n".join(violations)


@pytest.mark.parametrize("secret", ["", "short", "change-me", integrity._TEST_SECRET])
def test_unsafe_runtime_secrets_fail_startup_and_runtime_new(monkeypatch, secret: str) -> None:
    monkeypatch.setattr(integrity, "_is_test", lambda: False)
    monkeypatch.setattr(integrity.settings, "user_route_state_secret", secret)

    with pytest.raises(RuntimeError):
        integrity.validate_route_state_runtime_config()
    with pytest.raises(integrity.UserRouteStateIntegrityError):
        integrity._secret()


def test_strong_runtime_secret_is_accepted_new(monkeypatch) -> None:
    monkeypatch.setattr(integrity, "_is_test", lambda: False)
    monkeypatch.setattr(integrity.settings, "user_route_state_secret", "x" * 32)

    integrity.validate_route_state_runtime_config()
    assert integrity._secret() == b"x" * 32


def test_router_maps_rejected_mutation_without_committing_new() -> None:
    source = (ROOT / "routers/user_routes.py").read_text(encoding="utf-8")

    assert "UserRouteMutationRejectedError" in source
    assert 'status_code=422' in source
    assert '"code": "route_mutation_rejected"' in source
