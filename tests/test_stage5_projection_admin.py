import pytest
from fastapi import HTTPException

from core.config import settings
from core.admin_auth import admin_required
from services.data_foundation_projection_service import build_snapshot_from_place

TOKEN = "stage5-admin-token"


@pytest.fixture(autouse=True)
def _admin_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", TOKEN)


def _headers():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_admin_rebuild_status_readiness_and_activation_gate(client, db_session, place_factory):
    place = place_factory(slug="admin-projection")
    db_session.add(build_snapshot_from_place(place, snapshot_version=1)); db_session.commit()
    rebuild = client.post("/admin/projections/rebuild", headers=_headers(), json={
        "projection_type": "search",
        "source": "test", "audit_context": {"ticket": "CITYGO-376"},
    })
    assert rebuild.status_code == 200
    job_id = rebuild.json()["job_id"]
    status = client.get(f"/admin/projections/jobs/{job_id}", headers=_headers())
    readiness = client.get("/admin/projections/readiness", headers=_headers(), params={
        "projection_type": "search",
    })
    activation = client.get("/admin/projections/activation-safety", headers=_headers(), params={
        "toggle_key": "search_projection_reads_enabled",
    })
    assert status.status_code == readiness.status_code == activation.status_code == 200
    assert status.json()["actor"] == "test-admin"
    assert status.json()["audit_context"] == {"ticket": "CITYGO-376"}
    assert readiness.json()["ready"] is True
    assert readiness.json()["latest_rebuild_job"]["id"] == job_id
    assert activation.json()["activation_safe"] is True


def test_admin_projection_endpoints_require_auth():
    with pytest.raises(HTTPException) as exc_info:
        admin_required(None)
    assert exc_info.value.status_code == 401
