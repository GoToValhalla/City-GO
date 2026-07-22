#!/usr/bin/env python3
"""Guarded Stage 5 production operations through canonical admin APIs."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

KINDS = ("search", "routing", "route_candidate_set")
TOGGLES = {
    "search": "search_projection_reads_enabled",
    "catalog": "catalog_projection_reads_enabled",
    "routing": "routing_projection_reads_enabled",
}
MUTATIONS = {"rebuild", "disable_all"} | {
    f"{verb}_{name}" for verb in ("enable", "disable") for name in TOGGLES
}


def request(method: str, path: str, body: dict[str, object] | None = None) -> dict[str, object]:
    base = os.environ["PRODUCTION_BASE_URL"].rstrip("/")
    data = None if body is None else json.dumps(body).encode()
    headers = {"Authorization": f"Bearer {os.environ['ADMIN_API_TOKEN']}", "Content-Type": "application/json"}
    call = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(call, timeout=120) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise RuntimeError("admin API returned a non-object response")
    return value


def scope_query() -> tuple[str, int | None]:
    scope = os.environ["SCOPE"]
    raw = os.environ.get("CITY_ID", "").strip()
    if scope == "city" and (not raw.isdigit() or int(raw) < 1):
        raise ValueError("city scope requires a positive numeric city_id")
    city_id = int(raw) if scope == "city" else None
    return urllib.parse.urlencode({"city_id": city_id}) if city_id else "", city_id


def readiness(require_ready: bool) -> list[dict[str, object]]:
    query, _ = scope_query()
    rows = [request("GET", f"/api/admin/projections/readiness?projection_type={kind}&{query}") for kind in KINDS]
    if require_ready and not all(row.get("ready") is True and row.get("activation_safe") is True for row in rows):
        raise RuntimeError("projection readiness gate failed")
    return rows


def toggle(name: str, enabled: bool) -> dict[str, object]:
    key = TOGGLES[name]
    if os.environ["SCOPE"] != "global":
        raise ValueError("projection toggles support global scope only")
    if enabled:
        safe = request("GET", f"/api/admin/projections/activation-safety?toggle_key={key}")
        if safe.get("activation_safe") is not True:
            raise RuntimeError(f"activation safety gate failed: {safe.get('reason', 'unknown')}")
    result = request("PUT", f"/api/admin/feature-toggles/{key}?scope=global", {
        "value_bool": enabled, "reason": "stage5_production_workflow",
    })
    if result.get("value_bool") is not enabled:
        raise RuntimeError("toggle verification failed")
    return result


def run(operation: str) -> dict[str, object]:
    if operation in MUTATIONS and os.environ.get("CONFIRMATION") != "CONFIRM_STAGE5_PRODUCTION_MUTATION":
        raise ValueError("mutation confirmation does not match")
    if operation == "status":
        toggles = request("GET", "/api/admin/feature-toggles?scope=global")
        return {"operation": operation, "toggles": toggles, "readiness": readiness(False)}
    if operation == "readiness":
        return {"operation": operation, "readiness": readiness(True)}
    if operation == "rebuild":
        _, city_id = scope_query()
        jobs = [request("POST", "/api/admin/projections/rebuild", {
            "projection_type": kind, "city_id": city_id, "source": "stage5_production_workflow",
            "audit_context": {"github_run_id": os.environ.get("GITHUB_RUN_ID", "")},
        }) for kind in KINDS]
        return {"operation": operation, "jobs": jobs, "readiness": readiness(True)}
    if operation == "disable_all":
        return {"operation": operation, "toggles": [toggle(name, False) for name in TOGGLES]}
    verb, name = operation.split("_", 1)
    return {"operation": operation, "toggle": toggle(name, verb == "enable")}


if __name__ == "__main__":
    try:
        print(json.dumps(run(os.environ["OPERATION"]), sort_keys=True, default=str))
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": type(exc).__name__, "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
