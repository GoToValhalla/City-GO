from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    schema = Path("schemas/admin_backlog_reduction.py").read_text(encoding="utf-8")
    service = Path("services/admin_backlog_reduction_service.py").read_text(encoding="utf-8")
    diagnostics = Path(".github/workflows/admin-diagnostics.yml").read_text(encoding="utf-8")

    checks: list[str] = []
    assert "limit: int = Field(default=100, ge=1, le=1000)" in schema
    checks.append("dry-run/apply request has hard max limit")

    assert ".limit(min(request.limit, spec.max_batch_size)).all()" in service
    checks.append("generic candidates are bounded by request and action max batch")

    assert "limit(spec.max_batch_size).all()" in service
    checks.append("route eligibility recompute has bounded candidate window")

    assert "Dry-run smoke: skipped in this workflow" in diagnostics
    checks.append("screen diagnostics does not execute heavy reduction actions")

    print(json.dumps({"status": "ok", "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
