from __future__ import annotations

import argparse
from dataclasses import asdict

from sqlalchemy.orm import joinedload

from db.session import SessionLocal
from models.city import City
from models.place import Place
from services.publication_policy import (
    MODE_APPLY,
    MODE_SHADOW,
    PublicationPolicyConfig,
    apply_publication_decision,
    evaluate_new_place,
)


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
        query = db.query(Place).options(joinedload(Place.city)).filter(
            Place.is_published.is_(False),
            Place.is_active.is_(True),
        )
        if args.city_slug:
            query = query.join(City).filter(City.slug == args.city_slug)

        places = query.order_by(Place.updated_at.desc()).limit(args.limit).all()
        summary = {
            "config": asdict(config),
            "evaluated": 0,
            "shadow_auto_publish": 0,
            "auto_publish": 0,
            "send_to_review": 0,
            "hidden": 0,
        }

        for place in places:
            decision = evaluate_new_place(place, config=config)
            apply_publication_decision(db, place, decision, config=config, actor="publication-policy-runner")
            summary["evaluated"] += 1
            summary[decision.decision] = int(summary.get(decision.decision, 0)) + 1

        db.commit()
        print(summary)
    finally:
        db.close()


if __name__ == "__main__":
    main()
