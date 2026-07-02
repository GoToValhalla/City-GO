from __future__ import annotations

import pytest
from sqlalchemy import inspect

import models.intelligence_discipline_stage3  # noqa: F401
from db.base import Base
from services.intelligence_discipline_service import (
    CostBudgetExceededError,
    RegressionGateError,
    assert_candidate_only_columns,
    assert_cost_budget_available,
    assert_regression_gate_passed,
    prompt_hash,
)
from tests.allure_support import title


STAGE3_TABLES = {
    "prompt_versions",
    "golden_datasets",
    "evaluation_cases",
    "regression_gate_runs",
    "cost_budget_policies",
}


@title("Stage 3 metadata содержит таблицы Intelligence Discipline")
def test_stage3_metadata_contains_intelligence_tables() -> None:
    assert STAGE3_TABLES <= set(Base.metadata.tables)


@title("Stage 3 test database создаёт таблицы Intelligence Discipline")
def test_stage3_database_contains_intelligence_tables(engine) -> None:
    assert STAGE3_TABLES <= set(inspect(engine).get_table_names())


@title("PromptVersion содержит version/hash/schema/status rollout contract")
def test_prompt_version_contract_columns() -> None:
    table = Base.metadata.tables["prompt_versions"]
    columns = set(table.columns.keys())

    assert {
        "task_type",
        "version",
        "prompt_hash",
        "prompt_reference",
        "output_schema_version",
        "status",
        "rollout_policy",
        "owner",
        "changelog",
    } <= columns

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("task_type", "version") in unique_columns
    assert ("prompt_hash",) in unique_columns


@title("GoldenDataset и EvaluationCase содержат threshold/input/expected contract")
def test_golden_dataset_and_case_contract_columns() -> None:
    dataset_columns = set(Base.metadata.tables["golden_datasets"].columns.keys())
    case_columns = set(Base.metadata.tables["evaluation_cases"].columns.keys())

    assert {"task_type", "dataset_version", "locale", "city_id", "minimum_pass_rate", "status"} <= dataset_columns
    assert {"dataset_id", "case_key", "input_payload", "expected_output", "expected_decision", "severity", "tags"} <= case_columns


@title("RegressionGateRun содержит pass-rate, score payload и failure summary")
def test_regression_gate_run_contract_columns() -> None:
    columns = set(Base.metadata.tables["regression_gate_runs"].columns.keys())

    assert {
        "prompt_version_id",
        "dataset_id",
        "model_provider",
        "model_name",
        "status",
        "pass_rate",
        "failed_cases_count",
        "total_cases_count",
        "score_payload",
        "failure_summary",
    } <= columns


@title("CostBudgetPolicy содержит task/model/city/token/cost/action contract")
def test_cost_budget_policy_contract_columns() -> None:
    columns = set(Base.metadata.tables["cost_budget_policies"].columns.keys())

    assert {
        "task_type",
        "model_provider",
        "model_name",
        "city_id",
        "period",
        "max_tokens",
        "max_cost_amount",
        "action_when_exceeded",
        "status",
    } <= columns


@title("Prompt hash детерминированный и зависит от schema version")
def test_prompt_hash_is_deterministic_and_schema_aware() -> None:
    first = prompt_hash("extract facts", schema_version="v1")
    second = prompt_hash("extract facts", schema_version="v1")
    third = prompt_hash("extract facts", schema_version="v2")

    assert first == second
    assert first != third
    assert len(first) == 64


@title("Regression gate блокирует promotion при fail или низком pass-rate")
def test_regression_gate_helper_blocks_failed_or_low_score() -> None:
    assert_regression_gate_passed(status="passed", pass_rate=0.97, minimum_pass_rate=0.95)

    with pytest.raises(RegressionGateError):
        assert_regression_gate_passed(status="failed", pass_rate=0.99, minimum_pass_rate=0.95)

    with pytest.raises(RegressionGateError):
        assert_regression_gate_passed(status="passed", pass_rate=0.70, minimum_pass_rate=0.95)


@title("Cost budget helper блокирует превышение стоимости и токенов")
def test_cost_budget_helper_blocks_over_budget_runs() -> None:
    assert_cost_budget_available(
        current_cost=1.0,
        additional_cost=0.5,
        max_cost=2.0,
        current_tokens=100,
        additional_tokens=50,
        max_tokens=200,
    )

    with pytest.raises(CostBudgetExceededError):
        assert_cost_budget_available(
            current_cost=1.8,
            additional_cost=0.5,
            max_cost=2.0,
            current_tokens=100,
            additional_tokens=50,
            max_tokens=200,
        )

    with pytest.raises(CostBudgetExceededError):
        assert_cost_budget_available(
            current_cost=1.0,
            additional_cost=0.5,
            max_cost=2.0,
            current_tokens=180,
            additional_tokens=50,
            max_tokens=200,
        )


@title("Candidate-only guard запрещает public state fields")
def test_candidate_only_guard_blocks_public_state_fields() -> None:
    assert_candidate_only_columns({"field_name", "value_json", "status"})

    with pytest.raises(ValueError):
        assert_candidate_only_columns({"field_name", "value_json", "is_published"})
