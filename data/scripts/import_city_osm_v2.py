from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.scripts import import_city_osm as legacy_import
from db.session import SessionLocal
from services.coverage_profile_filters import COVERAGE_PROFILE_FILTERS
from services.data_coverage_assurance import run_data_coverage_assurance
from services.osm_import_taxonomy import category_from_osm_tags
from services.place_layer_service import apply_place_layers

# These filters are the production Overpass contract for Data Coverage Assurance.
# The legacy importer still owns persistence/lifecycle logic; this wrapper installs
# the expanded tag selection and shared taxonomy before running it.
COVERAGE_AWARE_PROFILE_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "tourist_core": [
        ("tourism", "attraction|museum|gallery|viewpoint|artwork|information|zoo|aquarium|theme_park"),
        ("historic", None),
        ("heritage", None),
        ("amenity", "cafe|restaurant|place_of_worship|monastery|marketplace"),
        ("amenity", "cafe|restaurant|place_of_worship|monastery"),
        ("amenity", "marketplace"),
        ("building", "church|cathedral|monastery|chapel|synagogue|mosque"),
        ("building", "church|cathedral|monastery|chapel"),
        ("building", "synagogue|mosque"),
        ("leisure", "park|garden|nature_reserve|playground|amusement_arcade|marina|promenade"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave|volcano|cliff|ridge"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave"),
        ("natural", "volcano|cliff|ridge"),
        ("waterway", "waterfall|river|stream"),
        ("waterway", "waterfall"),
        ("waterway", "river|stream"),
        ("attraction", "amusement_ride"),
        ("railway", "funicular|tram|monorail"),
        ("aerialway", "cable_car|gondola"),
        ("boundary", "national_park"),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "food_and_coffee": [
        ("amenity", "cafe|restaurant|fast_food|bar|pub|food_court|marketplace"),
        ("shop", "bakery|confectionery|coffee|tea|ice_cream|deli|cheese|pastry|marketplace"),
        ("cuisine", None),
    ],
    "nature_walk": [
        ("leisure", "park|garden|nature_reserve|playground|marina|promenade"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave|volcano|cliff|ridge"),
        ("natural", "beach|water|wood|peak|cave_entrance|cave"),
        ("natural", "volcano|cliff|ridge"),
        ("waterway", "waterfall|river|stream"),
        ("waterway", "waterfall"),
        ("waterway", "river|stream"),
        ("tourism", "viewpoint|information|attraction"),
        ("boundary", "national_park"),
        ("heritage", None),
        ("wikidata", None),
        ("wikipedia", None),
    ],
    "useful_services": [
        ("amenity", "toilets|pharmacy|atm|parking|shelter|bank|clinic|hospital|police"),
    ],
}
COVERAGE_AWARE_PROFILE_FILTERS.update(COVERAGE_PROFILE_FILTERS)


def _install_coverage_taxonomy() -> None:
    legacy_import.PROFILE_FILTERS = COVERAGE_AWARE_PROFILE_FILTERS
    legacy_import._category = category_from_osm_tags


def run(argv: list[str] | None = None) -> dict[str, object]:
    args = legacy_import.parse_args(argv)
    _install_coverage_taxonomy()
    result = legacy_import.run(argv)

    if args.apply:
        with SessionLocal() as db:
            layer_result = apply_place_layers(db, city_slug=args.city)
            coverage = run_data_coverage_assurance(db, city_slug=args.city)
            db.commit()
        result = {
            **result,
            "coverage_bridge": {"place_layers": layer_result},
            "data_coverage_assurance": {
                "evaluated": coverage["evaluated"],
                "changed": coverage["changed"],
                "changed_by_assurance": coverage["changed_by_assurance"],
                "summary": coverage["summary"],
                "acceptance": coverage["acceptance"],
                "recommended_actions": coverage["recommended_actions"],
                "scope_suggestions": coverage.get("scope_suggestions", []),
            },
        }

    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
