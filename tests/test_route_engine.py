from types import SimpleNamespace

from services.route_engine import RouteEngine, RouteExecutionRequest, RouteStrategySelector


class DummyStrategy:
    mode = "dummy"

    def __init__(self) -> None:
        self.called_with: tuple[object, RouteExecutionRequest] | None = None

    def build(self, deps: object, execution: RouteExecutionRequest) -> object:
        self.called_with = (deps, execution)
        return {"strategy": self.mode, "request": execution.request}


def test_route_engine_delegates_to_selected_strategy() -> None:
    strategy = DummyStrategy()
    engine = RouteEngine(selector=RouteStrategySelector(instant=strategy))
    deps = SimpleNamespace(name="deps")
    request = SimpleNamespace(route_time_mode="flexible")
    db = SimpleNamespace(name="db")
    profile = SimpleNamespace(user_id="u1")

    result = engine.build(deps=deps, db=db, request=request, profile=profile)

    assert result == {"strategy": "dummy", "request": request}
    assert strategy.called_with is not None
    called_deps, execution = strategy.called_with
    assert called_deps is deps
    assert execution.db is db
    assert execution.request is request
    assert execution.profile is profile
