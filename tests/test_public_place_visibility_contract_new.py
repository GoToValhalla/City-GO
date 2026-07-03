from __future__ import annotations

from services.user_route_place_loader import load_place


def _set_canonical(db_session, place, category: str | None):
    place.canonical_category = category
    db_session.add(place)
    db_session.commit()
    db_session.refresh(place)
    return place


def test_public_place_loader_rejects_canonical_pharmacy_new(db_session, place_factory) -> None:
    place = place_factory(category="museum", title="Аптека", is_published=True, is_visible_in_catalog=True)
    _set_canonical(db_session, place, "pharmacy")

    assert load_place(db_session, str(place.id)) is None


def test_public_place_loader_rejects_canonical_bank_new(db_session, place_factory) -> None:
    place = place_factory(category="museum", title="Bank", is_published=True, is_visible_in_catalog=True)
    _set_canonical(db_session, place, "bank")

    assert load_place(db_session, str(place.id)) is None


def test_public_place_loader_accepts_allowed_canonical_category_even_when_display_category_is_noisy_new(db_session, place_factory) -> None:
    place = place_factory(category="pharmacy", title="City Museum", is_published=True, is_visible_in_catalog=True)
    _set_canonical(db_session, place, "museum")

    loaded = load_place(db_session, str(place.id))

    assert loaded is not None
    assert loaded.id == place.id


def test_public_place_loader_rejects_unpublished_hidden_or_inactive_places_new(db_session, place_factory) -> None:
    unpublished = place_factory(category="museum", title="Unpublished", is_published=False)
    hidden = place_factory(category="museum", title="Hidden", is_visible_in_catalog=False)
    inactive = place_factory(category="museum", title="Inactive", is_active=False)

    assert load_place(db_session, str(unpublished.id)) is None
    assert load_place(db_session, str(hidden.id)) is None
    assert load_place(db_session, str(inactive.id)) is None


def test_public_place_loader_rejects_non_numeric_or_missing_place_id_new(db_session) -> None:
    assert load_place(db_session, None) is None
    assert load_place(db_session, "not-a-number") is None
