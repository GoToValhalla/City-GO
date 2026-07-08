"""Real local rehearsal against Kaliningrad found: 8/10 photo candidates were
the OpenStreetMap logo, because place.source_url pointed at an
openstreetmap.org node page and the OG-image website scraper blindly trusted
its og:image meta tag as if it were the place's real business website photo."""

from __future__ import annotations

import data.scripts.enrich_place_images as enrich_place_images


def test_openstreetmap_node_page_is_not_treated_as_business_website_new() -> None:
    assert enrich_place_images._is_business_website("https://www.openstreetmap.org/node/471928335") is False


def test_wikidata_and_wikipedia_pages_are_not_business_websites_new() -> None:
    assert enrich_place_images._is_business_website("https://www.wikidata.org/wiki/Q12345") is False
    assert enrich_place_images._is_business_website("https://ru.wikipedia.org/wiki/Some_article") is False


def test_real_business_website_is_still_accepted_new() -> None:
    assert enrich_place_images._is_business_website("https://kant-museum.example.com") is True


def test_candidate_from_website_og_image_skips_osm_node_pages_new(monkeypatch) -> None:
    def fail_if_called(url: str):
        raise AssertionError("must never fetch a non-business-website URL for og:image")

    monkeypatch.setattr(enrich_place_images, "_fetch_text", fail_if_called)

    result = enrich_place_images._candidate_from_website_og_image("https://www.openstreetmap.org/node/601372005")

    assert result is None
