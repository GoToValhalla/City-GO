"""CLI: полный audit pack Алматы."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from db.session import SessionLocal
from data.scripts.almaty_audit.api_snapshots import write_api_files
from data.scripts.almaty_audit.copy_batches import copy_enrichment_batches
from data.scripts.almaty_audit.db_import_jobs import write_import_jobs
from data.scripts.almaty_audit.db_places import write_places_full
from data.scripts.almaty_audit.db_raw_tags import write_raw_tags_sample
from data.scripts.almaty_audit.db_system_logs import write_system_logs
from data.scripts.almaty_audit.manifest import write_manifest
from data.scripts.almaty_audit.paths import AUDIT_ROOT, BATCHES_DIR, CITY_SLUGS, ensure_dirs
from data.scripts.almaty_audit.summary import write_summary
from models.city import City


def _not_run(root: Path, name: str, reason: str) -> None:
    (root / name).write_text(reason, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    notes: dict[str, str] = {}
    db = SessionLocal()
    try:
        city = db.query(City).filter(City.slug.in_(CITY_SLUGS)).first()
        slug = city.slug if city else CITY_SLUGS[0]
        n = write_places_full(db, AUDIT_ROOT / "places_almaty_full.csv", CITY_SLUGS)
        notes["places_almaty_full.csv"] = "db.query(Place)"
        print(f"places={n}")
        n = write_raw_tags_sample(db, AUDIT_ROOT / "places_almaty_sample_raw_tags.csv", CITY_SLUGS)
        notes["places_almaty_sample_raw_tags.csv"] = "SourceObservation.raw_payload sample"
        print(f"raw_tags_sample={n}")
        n = write_import_jobs(db, AUDIT_ROOT / "import_jobs_almaty.csv", CITY_SLUGS)
        notes["import_jobs_almaty.csv"] = "CityAdminImportJob+ImportBatch"
        print(f"import_jobs={n}")
        n = write_system_logs(db, AUDIT_ROOT / "system_logs_almaty.csv", CITY_SLUGS)
        notes["system_logs_almaty.csv"] = "SystemLog filtered"
        print(f"system_logs={n}")
    finally:
        db.close()
    _not_run(AUDIT_ROOT, "address_recovery_almaty_NOT_RUN.txt", "Address recovery apply для Алматы не запускался")
    _not_run(AUDIT_ROOT, "image_enrichment_almaty_NOT_RUN.txt", "enrich_place_images --apply для Алматы не запускался")
    export_root = Path(__file__).resolve().parents[3] / "data/exports/place_enrichment"
    batches = copy_enrichment_batches(export_root, BATCHES_DIR, CITY_SLUGS)
    api_base = os.environ.get("ADMIN_API_BASE", "http://localhost:8000")
    api_files = write_api_files(AUDIT_ROOT, api_base, CITY_SLUGS)
    print(f"api_files={api_files}")
    write_summary(AUDIT_ROOT, slug, batches)
    write_manifest(AUDIT_ROOT, notes)
    print(f"AUDIT_ROOT={AUDIT_ROOT.resolve()}")


if __name__ == "__main__":
    main()
