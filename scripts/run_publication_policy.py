from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.session import SessionLocal
from models.city import City
from models.place import Place
from models.review_queue_item import ReviewQueueItem
from services.publication_policy import (
    MODE_APPLY,
    MODE_SHADOW,
    PublicationPolicyConfig,
    apply_publication_decision,
    evaluate_new_place,
)
from services.publication_policy_summary import get_publication_policy_summary

BATCH_SIZE = 25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate City GO publication policy for unpublished places.")
    parser.add_argument("--mode", choices=(MODE_SHADOW, MODE_APPLY), default=MODE_SHADOW)
    parser.add_argument("--city", dest="city_slug", default=None, help="Optional city slug")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--auto-publish-enabled", action="store_true")
    parser.add_argument("--auto-publish-threshold", type=float, default=90.0)
    parser.add_argument("--review-threshold", type=float, default=60.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PublicationPolicyConfig(
        mode=args.mode,
        auto_publish_enabled=bool(args.auto_publish_enabled),
        auto_publish_threshold=args.auto_publish_threshold,
        review_threshold=args.review_threshold,
    )

    db = SessionLocal()
    try:
        place_ids = _load_place_ids(db, city_slug=args.city_slug, limit=args.limit)
        run_summary = {
            "config": asdict(config),
            "evaluated": 0,
            "shadow_auto_publish": 0,
            "auto_publish": 0,
            "send_to_review": 0,
            "hidden": 0,
        }
        print(f"publication_policy_candidates={len(place_ids)}", flush=True)

        for place_id in place_ids:
            place = db.get(Place, place_id)
            if place is None:
                continue
            decision = evaluate_new_place(place, config=config)
            apply_publication_decision(db, place, decision, config=config, actor="publication-policy-runner")
            run_summary["evaluated"] += 1
            run_summary[decision.decision] = int(run_summary.get(decision.decision, 0)) + 1

            if run_summary["evaluated"] % BATCH_SIZE == 0:
                db.commit()
                db.expunge_all()
                print(f"publication_policy_progress={run_summary['evaluated']}/{len(place_ids)}", flush=True)

        db.commit()
        summary = get_publication_policy_summary(db, days=7, city_slug=args.city_slug)
        output = {"run": run_summary, "last_7_days": summary}
        print(json.dumps(output, ensure_ascii=False, sort_keys=True), flush=True)
        print("PUBLICATION_POLICY_SUMMARY_JSON=" + json.dumps(output, ensure_ascii=False, sort_keys=True), flush=True)
    finally:
        db.close()


def _load_place_ids(db, *, city_slug: str | None, limit: int) -> list[int]:
    open_publication_review_exists = db.query(ReviewQueueItem.id).filter(
        ReviewQueueItem.place_id == Place.id,
        ReviewQueueItem.field_name == "publication",
        ReviewQueueItem.status == "open",
    ).exists()

    query = db.query(Place.id).filter(
        Place.is_published.is_(False),
        Place.is_active.is_(True),
        ~open_publication_review_exists,
    )
    if city_slug:
        query = query.join(City, City.id == Place.city_id).filter(City.slug == city_slug)
    rows = query.order_by(Place.updated_at.desc()).limit(limit).all()
    return [int(row[0]) for row in rows]


if __name__ == "__main__":
    main()
