from typing import Any, Literal

from pydantic import BaseModel, Field

RoutePolicy = Literal["always_allowed", "allowed_by_context", "useful_only", "forbidden", "manual_review"]


class CategoryWrite(BaseModel):
    code: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    parent_id: int | None = None
    icon: str | None = None
    color_token: str = "category-default"
    sort_order: int = 0
    is_active: bool = True
    is_catalog_visible: bool = True
    is_searchable: bool = True
    is_route_eligible: bool = True
    default_visit_duration_minutes: int | None = Field(None, ge=1, le=1440)
    indoor_default: bool | None = None
    outdoor_default: bool | None = None
    user_name: str | None = None
    admin_name: str | None = None
    route_policy: RoutePolicy = "manual_review"
    route_contexts: list[str] = []


class CategoryPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_id: int | None = None
    icon: str | None = None
    color_token: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    is_catalog_visible: bool | None = None
    is_searchable: bool | None = None
    is_route_eligible: bool | None = None
    default_visit_duration_minutes: int | None = None
    indoor_default: bool | None = None
    outdoor_default: bool | None = None
    user_name: str | None = None
    admin_name: str | None = None
    route_policy: RoutePolicy | None = None
    route_contexts: list[str] | None = None


class TreeNodeWrite(BaseModel):
    id: int
    parent_id: int | None = None
    sort_order: int = 0


class TreeWrite(BaseModel):
    nodes: list[TreeNodeWrite]


class MappingWrite(BaseModel):
    source: str
    source_key: str
    source_value: str
    target_category_id: int
    priority: int = 100
    confidence: float = Field(1.0, ge=0, le=1)
    active: bool = True
    conditions: dict[str, Any] = {}
    fallback: bool = False
    comment: str | None = None


class MappingPatch(BaseModel):
    target_category_id: int | None = None
    priority: int | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    active: bool | None = None
    conditions: dict[str, Any] | None = None
    fallback: bool | None = None
    comment: str | None = None


class ClassifyPreview(BaseModel):
    place_id: int | None = None
    source: str | None = None
    source_tags: dict[str, Any] = {}
    title: str | None = None
    description: str | None = None
    current_category: str | None = None
    manual_category_id: int | None = None


class ClassifyApply(ClassifyPreview):
    expected_category_id: int | None = None


class ConflictResolve(BaseModel):
    action: Literal["accept", "choose", "create_mapping", "apply_similar", "defer", "exclude", "enrich"]
    category_id: int | None = None
    create_mapping: bool = False
    comment: str | None = None


class BulkRequest(BaseModel):
    filters: dict[str, Any]
    target_category_id: int | None = None
    use_rule_engine: bool = False
    update_route_eligibility: bool = False
    idempotency_key: str
    limit: int = Field(10000, ge=1, le=50000)


class BulkApply(BaseModel):
    batch_id: str


class QualityRulePatch(BaseModel):
    name_ru: str | None = None
    severity: str | None = None
    active: bool | None = None
    parameters: dict[str, Any] | None = None
    auto_fix_available: bool | None = None
    blocking_publication: bool | None = None
    blocking_route_eligibility: bool | None = None


class WorkflowRun(BaseModel):
    entity_type: str = "place"
    entity_id: str | None = None
    payload: dict[str, Any] = {}
    request_id: str
    idempotency_key: str
