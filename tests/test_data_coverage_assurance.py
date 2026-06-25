import json
from pathlib import Path
from types import SimpleNamespace

from data.scripts.import_city_osm_v2 import COVERAGE_AWARE_PROFILE_FILTERS
from services.coverage_gap_service import load_known_poi_seed
from services.data_coverage_assurance import build_acceptance, build_summary
from services.data_coverage_contract import gap_reason_blocks_publication, scope_aliases
from services.osm_import_taxonomy import category_from_osm_tags, unsupported_tag_reason


def _row(status: str, gap_reason: str | None = None, policy: str = 'must_have'):
    """Лёгкая row-заглушка для проверки acceptance без поднятия БД."""

    return SimpleNamespace(
        city=SimpleNamespace(slug='kutaisi'),
        expected_category='culture',
        expected_scope='urban_core',
        expected_route_policy=policy,
        status=status,
        gap_reason=gap_reason,
    )


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


def test_osm_taxonomy_maps_heritage_cave_leisure_and_regional_tags() -> None:
    assert category_from_osm_tags({'amenity': 'place_of_worship', 'building': 'cathedral'}) == 'culture'
    assert category_from_osm_tags({'historic': 'monastery'}) == 'culture'
    assert category_from_osm_tags({'natural': 'cave_entrance'}) == 'walk'
    assert category_from_osm_tags({'waterway': 'waterfall'}) == 'walk'
    assert category_from_osm_tags({'tourism': 'theme_park'}) == 'park'
    assert category_from_osm_tags({'attraction': 'amusement_ride'}) == 'park'
    assert category_from_osm_tags({'amenity': 'marketplace'}) == 'market'
    assert category_from_osm_tags({'railway': 'funicular'}) == 'transport'
    assert category_from_osm_tags({'boundary': 'national_park'}) == 'walk'


def test_unsupported_tag_reason_is_specific_for_meaningful_unmapped_source() -> None:
    assert unsupported_tag_reason({'amenity': 'library'}) == 'unsupported_tag'
    assert unsupported_tag_reason({'name': 'Unknown point'}) == 'source_absent'
    assert unsupported_tag_reason({'natural': 'cave_entrance'}) is None


def test_coverage_aware_import_filters_include_global_must_have_tags() -> None:
    tourist_filters = COVERAGE_AWARE_PROFILE_FILTERS['tourist_core']
    food_filters = COVERAGE_AWARE_PROFILE_FILTERS['food_and_coffee']
    nature_filters = COVERAGE_AWARE_PROFILE_FILTERS['nature_walk']

    assert ('amenity', 'cafe|restaurant|place_of_worship|monastery|marketplace') in tourist_filters
    assert ('building', 'church|cathedral|monastery|chapel|synagogue|mosque') in tourist_filters
    assert ('tourism', 'attraction|museum|gallery|viewpoint|artwork|information|zoo|aquarium|theme_park') in tourist_filters
    assert ('railway', 'funicular|tram|monorail') in tourist_filters
    assert ('aerialway', 'cable_car|gondola') in tourist_filters
    assert ('boundary', 'national_park') in tourist_filters
    assert ('shop', 'bakery|confectionery|coffee|tea|ice_cream|deli|cheese|pastry|marketplace') in food_filters
    assert ('natural', 'beach|water|wood|peak|cave_entrance|cave|volcano|cliff|ridge') in nature_filters
    assert ('waterway', 'waterfall|river|stream') in nature_filters


def test_scope_aliases_connect_new_scope_types_to_legacy_import_targets() -> None:
    assert 'tourist_core' in scope_aliases('urban_core')
    assert 'food_area' in scope_aliases('food_core')
    assert 'heritage_ne_ring' in scope_aliases('heritage_ring')
    assert 'sataplia_nature' in scope_aliases('nature_daytrip')


def test_acceptance_blocks_city_when_critical_gap_is_unresolved() -> None:
    verdict = build_acceptance([
        _row('matched'),
        _row('out_of_scope', 'outside_bbox'),
    ])['kutaisi']

    assert verdict['accepted'] is False
    assert verdict['matched_critical'] == 1
    assert verdict['blocking_critical'] == 1
    assert 'blocking_gap_reasons_present' in verdict['reasons']


def test_acceptance_allows_city_when_critical_coverage_is_matched() -> None:
    verdict = build_acceptance([
        _row('matched'),
        _row('matched'),
        _row('source_absent', 'source_absent', policy='optional'),
    ])['kutaisi']

    assert verdict['accepted'] is True
    assert verdict['coverage_ratio'] == 1.0
    assert verdict['reasons'] == []


def test_summary_uses_post_assurance_rows() -> None:
    summary = build_summary([
        _row('matched'),
        _row('out_of_scope', 'not_imported_scope'),
        _row('needs_review', 'not_route_eligible'),
    ])

    assert summary['total'] == 3
    assert summary['matched'] == 1
    assert summary['critical_unresolved'] == 2
    assert summary['blocking_critical'] == 2
    assert summary['must_have_coverage_ratio'] == 0.3333
    assert summary['by_gap_reason']['not_route_eligible'] == 1


def test_blocking_gap_reason_contract() -> None:
    assert gap_reason_blocks_publication('unsupported_tag') is True
    assert gap_reason_blocks_publication('not_route_eligible') is True
    assert gap_reason_blocks_publication('source_absent') is False
