#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.session import SessionLocal
from models.place import Place
from services.route_eligibility_policy import evaluate_place_route_eligibility


def main() -> int:
    args = _parser().parse_args()
    if args.mode == "apply" and not args.confirm:
        raise SystemExit("--mode=apply requires --confirm")
    with SessionLocal() as db:
        report = recompute(db, mode=args.mode, batch_size=args.batch_size)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def recompute(db, *, mode: str, batch_size: int) -> dict[str, object]:
    totals: Counter[str] = Counter()
    by_city: dict[str, Counter[str]] = defaultdict(Counter)
    changed: list[dict[str, object]] = []
    offset = 0
    while True:
        places = db.query(Place).order_by(Place.id.asc()).offset(offset).limit(batch_size).all()
        if not places:
            break
        for place in places:
            verdict = evaluate_place_route_eligibility(place)
            desired_reason = None if verdict.eligible else ",".join(verdict.reasons[:5])
            needs_update = place.is_route_eligible is not verdict.eligible or (place.route_exclusion_reason or None) != desired_reason
            bucket = "eligible" if verdict.eligible else "excluded"
            totals[bucket] += 1
            by_city[str(place.city_id)][bucket] += 1
            for reason in verdict.reasons[:1] or ("eligible",):
                totals[reason] += 1
                by_city[str(place.city_id)][reason] += 1
            if needs_update:
                changed.append(_change(place, verdict.eligible, desired_reason))
                if mode == "apply":
                    place.is_route_eligible = verdict.eligible
                    place.route_exclusion_reason = desired_reason
        if mode == "apply":
            db.commit()
        offset += batch_size
    return {
        "mode": mode,
        "batch_size": batch_size,
        "generated_at": datetime.utcnow().isoformat(),
        "changed_count": len(changed),
        "changed_sample": changed[:50],
        "counts": dict(totals),
        "by_city": {city: dict(counter) for city, counter in by_city.items()},
        "rollback_report": "Re-run previous DB backup or restore changed_sample fields manually for sampled rows.",
    }


def _change(place: Place, eligible: bool, reason: str | None) -> dict[str, object]:
    return {
        "place_id": int(place.id),
        "city_id": int(place.city_id),
        "from_is_route_eligible": bool(place.is_route_eligible),
        "to_is_route_eligible": eligible,
        "from_reason": place.route_exclusion_reason,
        "to_reason": reason,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
