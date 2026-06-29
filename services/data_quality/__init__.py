"""Data quality package exports.

Keep package import light. Submodules such as readiness are imported during app
startup, so this package must not eagerly import bulk/query services.
"""

__all__ = [
    "apply_automation",
    "apply_bulk_action",
    "build_data_quality_summary",
    "diagnostic_gates",
    "list_data_quality_issues",
    "list_possible_duplicate_groups",
    "preview_automation",
    "preview_bulk_action",
    "refresh_data_quality_issues",
    "rollback_automation",
]


def __getattr__(name: str):
    if name in {"apply_automation", "preview_automation", "rollback_automation"}:
        from services.data_quality import automation
        return getattr(automation, name)
    if name in {"apply_bulk_action", "preview_bulk_action"}:
        from services.data_quality import bulk
        return getattr(bulk, name)
    if name in {"build_data_quality_summary", "list_data_quality_issues", "list_possible_duplicate_groups"}:
        from services.data_quality import query
        return getattr(query, name)
    if name == "diagnostic_gates":
        from services.data_quality.readiness import diagnostic_gates
        return diagnostic_gates
    if name == "refresh_data_quality_issues":
        from services.data_quality.refresh import refresh_data_quality_issues
        return refresh_data_quality_issues
    raise AttributeError(name)
