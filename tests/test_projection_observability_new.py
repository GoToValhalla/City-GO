import json
import logging

from services.projection_observability import log_projection_read, logger


def test_projection_read_info_event_is_not_filtered_new(caplog) -> None:
    assert logger.level == logging.INFO
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_projection_read(
            read_path="search",
            projection_type="search_place_document",
            city_id=7,
            uses_projection=True,
            latency_ms=12,
            source_version=3,
            projection_version=3,
        )

    record = next(row for row in caplog.records if row.name == "citygo.public_read_projections")
    payload = json.loads(record.message)
    assert payload == {
        "city_id": 7,
        "event": "projection_read",
        "latency_ms": 12,
        "path": "projection",
        "projection_type": "search_place_document",
        "projection_version": 3,
        "read_path": "search",
        "reason": "projection_ready",
        "source_version": 3,
    }
