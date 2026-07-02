from __future__ import annotations

from pathlib import Path

from tests.allure_support import title


ROOT = Path(__file__).resolve().parents[1]

BLUEPRINT_DOCS = [
    ROOT / "docs/product/product_blueprint_v2.md",
    ROOT / "docs/product/areas_v2.md",
    ROOT / "docs/product/user_journey_v2.md",
    ROOT / "docs/product/event_storming_v2.md",
    ROOT / "docs/testing/test_roadmap_v2.md",
    ROOT / "docs/roadmap/roadmap_v2.md",
    ROOT / "docs/product/blueprint_index_v2.md",
]


@title("Product Blueprint v2 содержит обязательный набор документов")
def test_product_blueprint_v2_docs_exist() -> None:
    missing = [str(path.relative_to(ROOT)) for path in BLUEPRINT_DOCS if not path.exists()]

    assert missing == []


@title("Product Blueprint v2 фиксирует route modes и lifecycle")
def test_product_blueprint_v2_covers_route_modes_and_lifecycle() -> None:
    content = (ROOT / "docs/product/product_blueprint_v2.md").read_text(encoding="utf-8")

    assert "Mode 1" in content
    assert "Mode 2" in content
    assert "Mode 3" in content
    assert "Mode 4" in content
    assert "Destination lifecycle" in content
    assert "Place lifecycle" in content
    assert "Route lifecycle" in content


@title("Roadmap v2 определяет следующий implementation phase")
def test_roadmap_v2_defines_next_phase() -> None:
    content = (ROOT / "docs/roadmap/roadmap_v2.md").read_text(encoding="utf-8")

    assert "Destination Launch Pipeline" in content
    assert "Route Builder v2" in content
    assert "Telegram Mini App" in content


@title("Test roadmap v2 содержит критичные группы проверок")
def test_test_roadmap_v2_covers_critical_groups() -> None:
    content = (ROOT / "docs/testing/test_roadmap_v2.md").read_text(encoding="utf-8")

    assert "Route" in content
    assert "Admin" in content
    assert "Import" in content
    assert "Publication" in content
