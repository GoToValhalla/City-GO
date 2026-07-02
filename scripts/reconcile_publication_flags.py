"""LEGACY COMPATIBILITY CLI for old publication flag reconciliation.

Status: historical/operational compatibility wrapper.

How it worked:
- This script was the original manual entrypoint for reconciling old public city
  feature toggles and leaked public place flags.
- Before publication state invariants were introduced, an operator could run this
  script to apply reconciliation directly.

Current source of truth:
- Diagnostic only: `scripts/diagnose_publication_states.py`.
- Repair flow: `scripts/repair_publication_states.py`.
- Service contract: `services/publication_reconciliation_service.py` is
  non-destructive by default; destructive changes require explicit flag, reason,
  actor and audit.

Rules:
- Do not use this as the default repair path for production incidents.
- Do not assume `--apply` hides published places; default service behavior is now
  protected/non-destructive.
- Keep this wrapper only for legacy visibility-toggle materialization and audited
  rollback compatibility.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.session import SessionLocal
from services.publication_reconciliation_service import (
    apply_city_visibility_toggle_reconciliation,
    apply_publication_reconciliation,
    materialize_legacy_city_visibility_defaults,
    publication_reconciliation_snapshot,
    rollback_publication_reconciliation,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or reconcile legacy public-city flags.")
    parser.add_argument("--apply", action="store_true", help="Legacy wrapper: run non-destructive reconciliation apply path.")
    parser.add_argument(
        "--materialize-legacy-city-visibility-defaults",
        action="store_true",
        help="Persist old default city_visible_to_users=true for cities created before --cutoff.",
    )
    parser.add_argument(
        "--apply-city-visibility-toggles",
        action="store_true",
        help="Publish cities that already have city_visible_to_users=true in admin feature toggles.",
    )
    parser.add_argument("--confirm", action="store_true", help="Required together with changing actions or --rollback-audit-ids.")
    parser.add_argument("--city", action="append", dest="city_slugs", help="Optional city slug; can be repeated.")
    parser.add_argument("--rollback-audit-ids", nargs="+", type=int)
    parser.add_argument("--cutoff", default="2026-06-26T00:00:00", help="ISO datetime cutoff for legacy default materialization.")
    parser.add_argument("--reason", default="production publication reconciliation")
    args = parser.parse_args()

    actions = sum(
        bool(value)
        for value in (
            args.apply,
            args.materialize_legacy_city_visibility_defaults,
            args.apply_city_visibility_toggles,
            args.rollback_audit_ids,
        )
    )
    if actions > 1:
        raise SystemExit(
            "Choose only one action: --apply, --materialize-legacy-city-visibility-defaults, "
            "--apply-city-visibility-toggles or --rollback-audit-ids."
        )
    if actions and not args.confirm:
        raise SystemExit("--confirm is required for a production-changing action.")

    with SessionLocal() as db:
        if args.apply:
            result = apply_publication_reconciliation(
                db,
                actor="production-reconciliation",
                city_slugs=args.city_slugs,
                reason=args.reason,
            )
        elif args.materialize_legacy_city_visibility_defaults:
            result = materialize_legacy_city_visibility_defaults(
                db,
                actor="production-reconciliation",
                cutoff=datetime.fromisoformat(args.cutoff),
                reason=args.reason,
            )
        elif args.apply_city_visibility_toggles:
            result = apply_city_visibility_toggle_reconciliation(
                db,
                actor="production-reconciliation",
                city_slugs=args.city_slugs,
                reason=args.reason,
            )
        elif args.rollback_audit_ids:
            result = rollback_publication_reconciliation(
                db,
                audit_ids=args.rollback_audit_ids,
                actor="production-reconciliation",
                reason=args.reason,
            )
        else:
            result = publication_reconciliation_snapshot(db)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
