from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_admin_place_change_review_contract_points_to_review_queue_item() -> None:
    router = _read("routers/admin_place_change_review.py")
    service = _read("services/place_change_review_service.py")

    assert "approve_place_change" in router
    assert "reject_place_change" in router
    assert "ReviewQueueItem" in service
    assert 'PLACE_CHANGE_FIELD = "place_change"' in service
    assert 'OPEN_STATUS = "open"' in service
    assert "ReviewQueueItem.field_name == PLACE_CHANGE_FIELD" in service
    assert "ReviewQueueItem.status == OPEN_STATUS" in service


def test_active_place_change_review_endpoint_does_not_import_legacy_sqlalchemy_model() -> None:
    router = _read("routers/admin_place_change_review.py")
    service = _read("services/place_change_review_service.py")

    active_text = "\n".join([router, service])
    assert "models.place_change_review" not in active_text
    assert "from models.place_change_review import" not in active_text
    assert "place" + "_change" + "_reviews" not in active_text
