"""Allowed AI task and provider registry for the admin selector."""

from __future__ import annotations

from dataclasses import dataclass

from core.config import settings


@dataclass(frozen=True)
class AIProviderSpec:
    key: str
    label: str
    model_name: str
    input_usd_per_1m: float
    output_usd_per_1m: float
    max_output_tokens: int
    enabled: bool
    disabled_reason: str | None = None


@dataclass(frozen=True)
class AITaskSpec:
    key: str
    label: str
    description: str
    mode: str
    schema_version: str
    enabled: bool
    allowed_provider_keys: tuple[str, ...]
    max_batch_size: int
    writes_public_fields: bool
    disabled_reason: str | None = None


def provider_specs() -> dict[str, AIProviderSpec]:
    openai_enabled = bool(settings.ai_enabled and settings.openai_api_key)
    return {
        "fake_shadow": AIProviderSpec(
            key="fake_shadow",
            label="Fake provider (0 USD, tests/shadow)",
            model_name="fake-local-v1",
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            max_output_tokens=settings.ai_max_output_tokens_per_place,
            enabled=True,
        ),
        "openai_gpt_5_nano": AIProviderSpec(
            key="openai_gpt_5_nano",
            label="OpenAI GPT-5 nano",
            model_name=settings.ai_openai_model,
            input_usd_per_1m=0.05,
            output_usd_per_1m=0.40,
            max_output_tokens=settings.ai_max_output_tokens_per_place,
            enabled=openai_enabled,
            disabled_reason=None if openai_enabled else "AI_ENABLED=true и OPENAI_API_KEY обязательны",
        ),
    }


def task_specs() -> dict[str, AITaskSpec]:
    enabled_tasks = _csv(settings.ai_enabled_tasks)
    return {
        "explain_review_reason": AITaskSpec(
            key="explain_review_reason",
            label="Объяснить причину проверки",
            description="Готовит короткое объяснение для админа по существующей review_queue записи.",
            mode="shadow",
            schema_version="explain_review_reason.v1",
            enabled="explain_review_reason" in enabled_tasks,
            allowed_provider_keys=("fake_shadow", "openai_gpt_5_nano"),
            max_batch_size=1,
            writes_public_fields=False,
        ),
        "parse_hours": AITaskSpec(
            key="parse_hours",
            label="Распарсить часы работы",
            description="Будущий controlled extractor для opening_hours с evidence.",
            mode="shadow",
            schema_version="parse_hours.v1",
            enabled=False,
            allowed_provider_keys=("openai_gpt_5_nano",),
            max_batch_size=1,
            writes_public_fields=False,
            disabled_reason="Требует golden dataset и проверки prompt injection.",
        ),
        "extract_contacts": AITaskSpec(
            key="extract_contacts",
            label="Извлечь контакты",
            description="Будущий extractor телефона/сайта/соцсетей только в candidate.",
            mode="shadow",
            schema_version="extract_contacts.v1",
            enabled=False,
            allowed_provider_keys=("openai_gpt_5_nano",),
            max_batch_size=1,
            writes_public_fields=False,
            disabled_reason="Требует source evidence и post-validation.",
        ),
        "draft_description": AITaskSpec(
            key="draft_description",
            label="Черновик описания",
            description="Будущий draft на базе verified observations, без фактов из головы.",
            mode="shadow",
            schema_version="draft_description.v1",
            enabled=False,
            allowed_provider_keys=("openai_gpt_5_nano",),
            max_batch_size=1,
            writes_public_fields=False,
            disabled_reason="Требует антигаллюцинационные тесты и ручной UX review.",
        ),
    }


def enabled_task_specs() -> list[AITaskSpec]:
    return [item for item in task_specs().values() if item.enabled]


def allowed_providers_for_task(task_type: str) -> list[AIProviderSpec]:
    task = get_task_spec(task_type)
    providers = provider_specs()
    return [providers[key] for key in task.allowed_provider_keys if providers[key].enabled]


def get_task_spec(task_type: str) -> AITaskSpec:
    tasks = task_specs()
    if task_type not in tasks:
        raise ValueError("unknown_task")
    task = tasks[task_type]
    if not task.enabled:
        raise ValueError(task.disabled_reason or "task_disabled")
    return task


def get_provider_for_task(task_type: str, provider_key: str) -> AIProviderSpec:
    task = get_task_spec(task_type)
    providers = provider_specs()
    provider = providers.get(provider_key)
    if provider is None:
        raise ValueError("unknown_provider")
    if provider_key not in task.allowed_provider_keys:
        raise ValueError("provider_not_allowed_for_task")
    if not provider.enabled:
        raise ValueError(provider.disabled_reason or "provider_disabled")
    return provider


def _csv(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}
