from __future__ import annotations

import hashlib


class RegressionGateError(ValueError):
    pass


class CostBudgetExceededError(ValueError):
    pass


def prompt_hash(prompt_text: str, *, schema_version: str | None = None) -> str:
    raw = f"{schema_version or 'default'}:{prompt_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assert_regression_gate_passed(*, status: str, pass_rate: float, minimum_pass_rate: float) -> None:
    if status != "passed" or pass_rate < minimum_pass_rate:
        raise RegressionGateError(
            f"Regression gate failed: status={status}, pass_rate={pass_rate}, minimum={minimum_pass_rate}"
        )


def assert_cost_budget_available(
    *,
    current_cost: float,
    additional_cost: float,
    max_cost: float | None,
    current_tokens: int,
    additional_tokens: int,
    max_tokens: int | None,
) -> None:
    if max_cost is not None and current_cost + additional_cost > max_cost:
        raise CostBudgetExceededError("Cost budget exceeded")
    if max_tokens is not None and current_tokens + additional_tokens > max_tokens:
        raise CostBudgetExceededError("Token budget exceeded")


def assert_candidate_only_columns(columns: set[str]) -> None:
    forbidden = {"is_published", "is_public", "is_visible_in_catalog", "published_at"}.intersection(columns)
    if forbidden:
        raise ValueError(f"Candidate table cannot contain public state fields: {sorted(forbidden)}")
