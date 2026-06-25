import json
from pathlib import Path

from data.scripts.import_city_osm_v2 import COVERAGE_AWARE_PROFILE_FILTERS
from services.coverage_gap_service import load_known_poi_seed
from services.osm_import_taxonomy import category_from_osm_tags, unsupported_tag_reason


def test_kutaisi_known_poi_seed_contains_user_reported_places() -> None:
    items = {item['slug']: item for item in load_known_poi_seed() if item['city_slug'] == 'kutaisi'}

    assert set(items) >= {
        'bagrati-cathedral',
        'motsameta-monastery',
        'gelati-monastery',
        'sanapiro',
        'kebaby-bikentiya',
        'kutaisi-amusement-park',
        'sataplia-cave',
    }
    assert items['bagrati-cathedral']['expected_category'] == 'culture'
    assert items['sataplia-cave']['expected_scope'] == 'nature_daytrip'
    assert items['gelati-monastery']['expected_route_policy'] == 'day_trip'


def test_kutaisi_known_poi_seed_is_inside_configured_import_scopes() -> None:
    targets = json.loads(Path('data/config/import_targets.json').read_text(encoding='utf-8'))
    kutaisi = next(city for city in targets['targets'] if city['city'] == 'kutaisi')
    bboxes = [scope['bbox'] for scope in kutaisi['scopes']]

    for item in load_known_poi_seed():
        if item['city_slug'] != 'kutaisi':
            continue
        lat = float(item['lat'])
        lng = float(item['lng'])
        assert any(
            float(bbox['south']) <= lat <= float(bbox['north'])
            and float(bbox['west']) <= lng <= float(bbox['east'])
            for bbox in bboxes
        ), item['slug']


def test_osm_taxonomy_maps_heritage_cave_and_leisure_tags() -> None:
    assert category_from_osm_tags({'amenity': 'place_of_worship', 'building': 'cathedral'}) == 'culture'
    assert category_from_osm_tags({'historic': 'monastery'}) == 'culture'
    assert category_from_osm_tags({'natural': 'cave_entrance'}) == 'walk'
    assert category_from_osm_tags({'tourism': 'theme_park'}) == 'park'
    assert category_from_osm_tags({'attraction': 'amusement_ride'}) == 'park'


def test_unsupported_tag_reason_is_specific_for_meaningful_unmapped_source() -> None:
    assert unsupported_tag_reason({'amenity': 'library'}) == 'unsupported_tag'
    assert unsupported_tag_reason({'name': 'Unknown point'}) == 'source_absent'
    assert unsupported_tag_reason({'natural': 'cave_entrance'}) is None


def test_coverage_aware_import_filters_include_global_must_have_tags() -> None:
    tourist_filters = COVERAGE_AWARE_PROFILE_FILTERS['tourist_core']
    nature_filters = COVERAGE_AWARE_PROFILE_FILTERS['nature_walk']

    assert ('amenity', 'cafe|restaurant|place_of_worship|monastery') in tourist_filters
    assert ('building', 'church|cathedral|monastery|chapel') in tourist_filters
    assert ('tourism', 'attraction|museum|gallery|viewpoint|artwork|information|zoo|aquarium|theme_park') in tourist_filters
    assert ('natural', 'beach|water|wood|peak|cave_entrance|cave') in nature_filters
    assert ('waterway', 'waterfall') in nature_filters
