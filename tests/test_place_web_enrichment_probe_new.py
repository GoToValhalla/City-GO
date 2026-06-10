"""Тесты preview-парсера web enrichment без сетевых запросов."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "data" / "scripts" / "place_web_enrichment_probe.py"
_spec = importlib.util.spec_from_file_location("place_web_enrichment_probe", _SCRIPT_PATH)
assert _spec and _spec.loader
probe = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = probe
_spec.loader.exec_module(probe)


def test_load_places_from_enrichment_export_csv_new(tmp_path: Path) -> None:
    input_csv = tmp_path / "places.csv"
    input_csv.write_text(
        "id,title,category,city_name,lat,lng,current_address,current_website,current_phone,"
        "current_opening_hours,current_image_url,source_url,raw_osm_tags\n"
        "1,Kulikov,food,Алматы,43.1,76.9,,,,,,https://www.openstreetmap.org/node/1,"
        '"{""website"":""https://kulikov.example"",""opening_hours"":""Mo-Su 08:00-22:00""}"\n',
        encoding="utf-8",
    )

    places = probe.load_places(input_csv, limit=10)

    assert len(places) == 1
    assert places[0].place_id == "1"
    assert places[0].title == "Kulikov"
    assert places[0].city == "Алматы"
    assert places[0].lat == 43.1
    assert places[0].lng == 76.9
    assert places[0].raw["raw_osm_tags_parsed"]["website"] == "https://kulikov.example"


def test_enrich_one_uses_nominatim_and_wikidata_without_network_new(monkeypatch: pytest.MonkeyPatch) -> None:
    place = probe.PlaceInput(
        place_id="42",
        title="Museum Test",
        city="Алматы",
        category="museum",
        lat=43.2,
        lng=76.9,
    )

    def fake_search_nominatim(_: object) -> object:
        return probe.SourceHit(
            source="nominatim_search",
            source_url="https://www.openstreetmap.org/node/42",
            confidence=0.75,
            reason="found_by_text_search",
            data={
                "address": "Абая 10, Алматы",
                "website": "https://museum.example",
                "phone": "+7 700 000 00 00",
                "opening_hours": "Mo-Su 10:00-18:00",
                "wikidata": "Q42",
            },
        )

    def fake_wikidata_image(qid: str | None) -> object:
        assert qid == "Q42"
        return probe.SourceHit(
            source="wikidata",
            source_url="https://www.wikidata.org/wiki/Q42",
            confidence=0.9,
            reason="wikidata_p18_image",
            data={"image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Test.jpg"},
        )

    monkeypatch.setattr(probe, "search_nominatim", fake_search_nominatim)
    monkeypatch.setattr(probe, "wikidata_image", fake_wikidata_image)
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)

    result = probe.enrich_one(place, sleep_seconds=0)

    assert result.suggested_address == "Абая 10, Алматы"
    assert result.suggested_website == "https://museum.example"
    assert result.suggested_phone == "+7 700 000 00 00"
    assert result.suggested_opening_hours == "Mo-Su 10:00-18:00"
    assert result.suggested_image_url.endswith("Test.jpg")
    assert result.image_match_status == "wikidata_p18"
    assert result.suggested_confidence == 0.9


def test_write_outputs_creates_preview_files_new(tmp_path: Path) -> None:
    results = [
        probe.ProbeResult(
            input_place_id="1",
            input_title="A",
            input_city="Алматы",
            input_category="cafe",
            current_address=None,
            current_image_url=None,
            suggested_address="Абая 1, Алматы",
            suggested_image_url="/static/placeholders/cafe.svg",
            image_match_status="category_placeholder",
            suggested_data_source="category_placeholder",
        ),
        probe.ProbeResult(
            input_place_id="2",
            input_title="B",
            input_city="Алматы",
            input_category="museum",
            current_address=None,
            current_image_url=None,
            suggested_address="Достык 2, Алматы",
            suggested_image_url="https://commons.wikimedia.org/wiki/Special:Redirect/file/B.jpg",
            image_match_status="wikidata_p18",
            suggested_data_source="wikidata",
        ),
    ]

    probe.write_outputs(results, tmp_path)

    assert (tmp_path / "preview.csv").exists()
    assert (tmp_path / "preview.json").exists()
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 2
    assert summary["with_suggested_address"] == 2
    assert summary["with_real_image"] == 1
    assert summary["by_image_match_status"]["category_placeholder"] == 1
    assert summary["by_image_match_status"]["wikidata_p18"] == 1

    with (tmp_path / "preview.csv").open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["input_place_id"] == "1"
    assert rows[1]["image_match_status"] == "wikidata_p18"
