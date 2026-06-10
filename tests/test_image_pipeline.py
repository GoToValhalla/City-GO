from pathlib import Path

from data.scripts.image_pipeline.official import extract_og_image
from data.scripts.image_pipeline.run import run_pipeline
from data.scripts.image_pipeline.selector import choose_image
from data.scripts.image_pipeline.verification import verification_queue
from data.scripts.image_pipeline.wikidata import direct_qid, wikipedia_title
from data.scripts.image_pipeline.io import write_json


def test_wikidata_tag_parsing() -> None:
    assert direct_qid({"wikidata": "Q123"}) == "Q123"
    assert wikipedia_title({"wikipedia": "ru:Зеленоградск"}) == "Зеленоградск"


def test_official_og_image_extracts_absolute_url() -> None:
    html = '<html><meta property="og:image" content="/cover.jpg"></html>'
    assert extract_og_image(html, "https://example.com/place") == "https://example.com/cover.jpg"


def test_selector_prioritizes_exact_wikidata_photo() -> None:
    image = choose_image(
        {"slug": "p", "category": "coffee"},
        {"wikidata_p18": [{"image": "https://img", "source_url": "https://wd"}],
         "mapillary_area": [{"url": "https://area", "source_url": "https://map"}]},
        "2026-06-05",
    )
    assert image["match_status"] == "exact_place_photo"
    assert image["source"] == "wikidata_p18"


def test_verification_queue_skips_high_confidence_exact() -> None:
    exact = {"slug": "a", "title": "A", "category": "museum",
             "image": {"match_status": "exact_place_photo", "match_confidence": "high"}}
    category = {"slug": "b", "title": "B", "category": "coffee",
                "image": {"match_status": "category_photo", "match_confidence": "low", "url": None}}
    assert verification_queue((exact, category))[0]["slug"] == "b"


def test_run_pipeline_writes_artifacts_and_queue(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    raw = tmp_path / "raw.json"
    out = tmp_path / "out.json"
    queue = tmp_path / "queue.json"
    write_json(catalog, {"items": [{"slug": "zelenogradsk-coffee-a", "title": "A",
                                    "category": "coffee", "source_url": "https://www.openstreetmap.org/node/1"}]})
    write_json(raw, {"elements": [{"type": "node", "id": 1, "tags": {"name": "A"}}]})

    counts = run_pipeline(catalog, raw, out, queue)

    assert counts == {"category_photo": 1}
    assert out.exists()
    assert queue.exists()
