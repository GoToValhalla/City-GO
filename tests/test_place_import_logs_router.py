from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.dependencies import get_db
from models.place_import_event import PlaceImportEvent
from routers.place_import_logs import router
from tests.test_place_import_log_service import _item
from schemas.place_seed_import_summary import PlaceSeedImportSummary
from services.place_import_log_service import record_place_import


def _app() -> FastAPI:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PlaceImportEvent.__table__.create(bind=engine)
    db = sessionmaker(bind=engine)()
    summary = PlaceSeedImportSummary(total=1, created=1, updated=0, skipped=0, invalid=0, errors=[])
    record_place_import(db, [_item()], summary, dry_run=True)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    return app


def test_place_import_log_summary_endpoint() -> None:
    response = TestClient(_app()).get("/place-import-logs/summary")
    assert response.status_code == 200
    assert response.json()["total_imports"] == 1
