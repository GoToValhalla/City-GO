from services import place_address_geocode as geocode


def test_geoapify_building_address_has_high_confidence(monkeypatch):
    monkeypatch.setattr(geocode.settings, "geoapify_api_key", "test")
    monkeypatch.setattr(
        geocode,
        "_geoapify_payload",
        lambda *_args, **_kwargs: {
            "results": [{
                "street": "улица Ленина",
                "housenumber": "10",
                "city": "Астрахань",
                "distance": 4,
                "rank": {"confidence": 0.97},
            }]
        },
    )
    monkeypatch.setattr(geocode, "_nominatim_candidate", lambda *_args, **_kwargs: None)

    candidate = geocode.reverse_geocode_candidate(46.3, 48.0, category="museum")

    assert candidate.address == "улица Ленина, 10, Астрахань"
    assert candidate.source == "geoapify_reverse"
    assert candidate.precision == "building"
    assert candidate.confidence == 0.97


def test_location_without_house_gets_nearby_street_label(monkeypatch):
    monkeypatch.setattr(geocode.settings, "geoapify_api_key", "")
    monkeypatch.setattr(
        geocode,
        "reverse_geocode_payload",
        lambda *_args, **_kwargs: {
            "address": {"road": "Петровская набережная", "city": "Астрахань"}
        },
    )

    candidate = geocode.reverse_geocode_candidate(46.3, 48.0, category="beach")

    assert candidate.address == "Рядом с Петровская набережная, Астрахань"
    assert candidate.precision == "street"
    assert candidate.confidence == 0.82


def test_venue_without_street_is_not_given_fake_address(monkeypatch):
    monkeypatch.setattr(geocode.settings, "geoapify_api_key", "")
    monkeypatch.setattr(
        geocode,
        "reverse_geocode_payload",
        lambda *_args, **_kwargs: {"address": {"city": "Астрахань"}},
    )

    assert geocode.reverse_geocode_candidate(46.3, 48.0, category="cafe") is None
