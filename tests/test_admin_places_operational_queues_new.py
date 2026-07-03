from __future__ import annotations

from fastapi.testclient import TestClient


def _titles(response) -> set[str]:
    assert response.status_code == 200
    return {str(item["title"]) for item in response.json()["items"]}


def test_admin_places_search_supports_overview_auto_and_manual_queues_new(client: TestClient, place_factory) -> None:
    auto = place_factory(slug="auto-queue-place", title="Auto Queue Place", category="museum", publication_status="auto_backlog")
    manual = place_factory(slug="manual-queue-place", title="Manual Queue Place", category="museum", publication_status="needs_review")
    place_factory(slug="published-place", title="Published Place", category="museum", publication_status="published")

    auto_titles = _titles(client.get("/admin/places/search", params={"publication_status": "auto_backlog"}))
    manual_titles = _titles(client.get("/admin/places/search", params={"publication_status": "needs_review"}))

    assert auto.title in auto_titles
    assert manual.title not in auto_titles
    assert manual.title in manual_titles
    assert auto.title not in manual_titles


def test_admin_places_search_no_description_preset_includes_short_or_title_copy_new(client: TestClient, db_session, place_factory) -> None:
    short = place_factory(slug="short-description-place", title="Short Description Place", category="museum")
    copy = place_factory(slug="copy-description-place", title="Copy Description Place", category="museum")
    good = place_factory(slug="good-description-place", title="Good Description Place", category="museum")
    short.short_description = "short"
    copy.short_description = copy.title
    good.short_description = "A useful traveller-facing description with enough detail."
    db_session.add_all([short, copy, good])
    db_session.commit()

    titles = _titles(client.get("/admin/places/search", params={"preset": "no_description"}))

    assert short.title in titles
    assert copy.title in titles
    assert good.title not in titles


def test_admin_places_search_route_queue_preset_new(client: TestClient, db_session, place_factory) -> None:
    hidden_route = place_factory(slug="hidden-route-place", title="Hidden Route Place", category="museum", is_published=True, is_route_eligible=False)
    good = place_factory(slug="route-ready-place", title="Route Ready Place", category="museum", is_published=True, is_route_eligible=True)
    good.canonical_category = "museum"
    db_session.add(good)
    db_session.commit()

    not_in_routes = _titles(client.get("/admin/places/search", params={"preset": "not_in_routes"}))

    assert hidden_route.title in not_in_routes
    assert good.title not in not_in_routes
