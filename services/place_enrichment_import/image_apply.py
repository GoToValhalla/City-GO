"""Применение suggested_image_url из enrichment CSV в place_images."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_APPROVED, PlaceImage
from services.place_enrichment_import.parse_values import is_empty


def apply_csv_images(db: Session, enriched_path: Path, *, actor: str) -> dict[str, int | list[str]]:
    rows = list(csv.DictReader(enriched_path.read_text(encoding="utf-8").splitlines()))
    created = 0
    skipped = 0
    errors: list[str] = []
    for row in rows:
        url = (row.get("suggested_image_url") or "").strip()
        if is_empty(url):
            continue
        pid_raw = (row.get("id") or "").strip()
        if not pid_raw.isdigit():
            errors.append(f"Некорректный id для image: {pid_raw}")
            continue
        place = db.query(Place).filter(Place.id == int(pid_raw)).first()
        if place is None:
            skipped += 1
            errors.append(f"Место не найдено id={pid_raw}")
            continue
        exists = db.query(PlaceImage).filter(PlaceImage.place_id == place.id, PlaceImage.image_url == url).first()
        if exists is not None:
            skipped += 1
            continue
        db.add(PlaceImage(
            place_id=place.id, image_url=url, source_type="enrichment_csv",
            status=PLACE_IMAGE_STATUS_APPROVED, is_primary=place.image_url is None,
        ))
        if place.image_url is None:
            place.image_url = url
        created += 1
    return {"images_created": created, "images_skipped": skipped, "image_errors": errors}
