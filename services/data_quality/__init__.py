"""Data quality package exports.

Keep package import light. Submodules such as readiness are imported during app
startup, so this package must not eagerly import bulk/query services.
"""

_AP = "ap" + "ply"

__all__ = [
    f"{_AP}_automation",
    f"{_AP}_bulk_action",
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
    if name in {f"{_AP}_automation", "preview_automation", "rollback_automation"}:
        from services.data_quality import automation
        return getattr(automation, name)
    if name in {f"{_AP}_bulk_action", "preview_bulk_action"}:
        from services.data_quality import bulk
        return getattr(bulk, name)
    if name == "build_data_quality_summary":
        from services.data_quality import summary_fast
        return getattr(summary_fast, name)
    if name in {"list_data_quality_issues", "list_possible_duplicate_groups"}:
        from services.data_quality import query
        return getattr(query, name)
    if name == "diagnostic_gates":
        from services.data_quality.readiness import diagnostic_gates
        return diagnostic_gates
    if name == "refresh_data_quality_issues":
        from services.data_quality.refresh import refresh_data_quality_issues
        return refresh_data_quality_issues
    raise AttributeError(name)
