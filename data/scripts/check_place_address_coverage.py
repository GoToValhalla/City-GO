from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from models.place import Place
from services.place_address_coverage import city_address_report
from services.place_address_coverage_export import export_coverage


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Address coverage report per city.")
    parser.add_argument("--export", action="store_true", help="Save JSON artifact to data/exports/address_recovery/.")
    parser.add_argument("--label", default="address_coverage", help="Artifact label prefix.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    with SessionLocal() as db:
        cities = db.query(City).order_by(City.slug.asc()).all()
        report: dict[str, object] = {}
        for city in cities:
            places = db.query(Place).filter(Place.city_id == city.id).all()
            entry = city_address_report(places)
            entry["city_slug"] = city.slug
            report[city.slug] = entry
        payload: dict[str, object] = {"cities": report}
        if args.export:
            payload["artifact_path"] = export_coverage(report, label=args.label)
        return payload


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
