from services.public_place_quality import is_technical_osm_title


def test_category_prefixed_osm_titles_are_technical():
    assert is_technical_osm_title("Пляж OSM 1202021911") is True
    assert is_technical_osm_title("Парк OSM 42") is True
    assert is_technical_osm_title("Смотровая точка OSM 100") is True


def test_normal_titles_are_not_technical():
    assert is_technical_osm_title("Пляж Центральный") is False
    assert is_technical_osm_title("Музей истории Астрахани") is False
