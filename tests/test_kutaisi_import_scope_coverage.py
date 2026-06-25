import json
from pathlib import Path


def _scopes() -> dict[str, dict]:
    payload = json.loads(Path('data/config/import_targets.json').read_text(encoding='utf-8'))
    city = next(item for item in payload['targets'] if item['city'] == 'kutaisi')
    return {scope['code']: scope for scope in city['scopes']}


def test_kutaisi_has_extended_import_scopes() -> None:
    scopes = _scopes()

    assert 'heritage_ne_ring' in scopes
    assert 'sataplia_tourist' in scopes
    assert 'sataplia_nature' in scopes
    assert 'food_wider_center' in scopes


def test_kutaisi_extended_import_scopes_have_expected_profiles() -> None:
    scopes = _scopes()

    assert scopes['heritage_ne_ring']['profile'] == 'tourist_core'
    assert scopes['sataplia_tourist']['profile'] == 'tourist_core'
    assert scopes['sataplia_nature']['profile'] == 'nature_walk'
    assert scopes['food_wider_center']['profile'] == 'food_and_coffee'


def test_kutaisi_wider_food_scope_extends_original_food_area() -> None:
    scopes = _scopes()
    original = scopes['food_area']['bbox']
    wider = scopes['food_wider_center']['bbox']

    assert wider['south'] < original['south']
    assert wider['west'] < original['west']
    assert wider['north'] > original['north']
    assert wider['east'] > original['east']
