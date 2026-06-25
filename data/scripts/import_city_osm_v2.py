from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.scripts import import_city_osm as legacy_import
from db.session import SessionLocal
from services.coverage_gap_service import refresh_coverage_statuses
from services.osm_import_taxonomy import category_from_osm_tags

# These filters are the production Overpass contract for Data Coverage Assurance.
# The legacy importer still owns persistence/lifecycle logic; this wrapper installs
# the expanded tag selection and shared taxonomy before running it.
COVERAGE_AWARE_PROFILE_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "tourist_core": [
        ("tourism", "attraction|museum|gallery|viewpoint|artwork|information|zoo|aquarium|theme_park"),
        ("historic", None),
        ("heritage", None),
        ("amenity", "cafe|restaurant|place_of_worship|monastery"),
        ("building", "church|cathedral|monastery|chapel"),
        ("leisure", "park|garden|nature_reserve|playground|amusement_arcade"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave"),
        ("waterway", "waterfall"),
        ("attraction", "amusement_ride"),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "food_and_coffee": [
        ("amenity", "cafe|restaurant|fast_food|bar|pub|food_court"),
        ("shop", "bakery|confectionery|coffee|tea|ice_cream"),
        ("cuisine", None),
    ],
    "nature_walk": [
        ("leisure", "park|garden|nature_reserve|playground"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave"),
        ("waterway", "waterfall"),
        ("tourism", "viewpoint|information|attraction"),
        ("heritage", None),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "useful_services": [
        ("amenity", "toilets|pharmacy|atm|parking|shelter|bank|clinic|hospital|police"),
    ],
}


def _install_coverage_taxonomy() -> None:
    legacy_import.PROFILE_FILTERS = COVERAGE_AWARE_PROFILE_FILTERS
    legacy_import._category = category_from_osm_tags


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = legacy_import.parse_args(argv)
    _install_coverage_taxonomy()
    result = legacy_import.run(argv)

    if args.apply:
        with SessionLocal() as db:
            coverage = refresh_coverage_statuses(db, city_slug=args.city)
            db.commit()
        result = {
            **result,
            "coverage_gap_refresh": {
                "evaluated": coverage["evaluated"],
                "changed": coverage["changed"],
                "summary": coverage["summary"],
            },
        }

    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
