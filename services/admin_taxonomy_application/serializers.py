from __future__ import annotations

from models.taxonomy import QualityRule, TaxonomyBulkBatch, TaxonomyConflict, TaxonomyMapping, WorkflowOperation


def mapping_dict(row: TaxonomyMapping) -> dict[str, object]:
    keys = ("id", "source", "source_key", "source_value", "target_category_id", "priority",
            "confidence", "active", "conditions", "fallback", "comment", "created_by")
    return {key: getattr(row, key) for key in keys}


def conflict_dict(row: TaxonomyConflict) -> dict[str, object]:
    return {"id": row.id, "place_id": row.place_id,
            "place_title": row.place.title if hasattr(row, "place") else None,
            "conflict_type": row.conflict_type, "severity": row.severity, "source": row.source,
            "confidence": row.confidence, "current_category_id": row.current_category_id,
            "recommended_category_id": row.recommended_category_id, "details": row.details,
            "status": row.status}


def batch_dict(row: TaxonomyBulkBatch) -> dict[str, object]:
    return {key: getattr(row, key) for key in
            ("id", "status", "filters", "preview", "result", "rollback_result")}


def quality_rule_dict(row: QualityRule) -> dict[str, object]:
    keys = ("id", "code", "name_ru", "severity", "entity_type", "active", "parameters",
            "auto_fix_available", "blocking_publication", "blocking_route_eligibility")
    return {key: getattr(row, key) for key in keys}


def operation_dict(row: WorkflowOperation) -> dict[str, object]:
    keys = ("id", "workflow", "request_id", "entity_type", "entity_id", "status",
            "current_step", "steps", "retry_count", "max_retries", "error_message")
    return {key: getattr(row, key) for key in keys}
