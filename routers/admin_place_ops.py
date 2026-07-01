"""Admin: деталь места, создание, bulk, адреса, city settings."""

from __future__ import annotations

import json
import os
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from models.place import Place
from schemas.admin_place_ops import (
    AdminAddressRefreshRequest,
    AdminBulkApplyRequest,
    AdminBulkPreviewRequest,
    AdminCityToggleUpdateRequest,
    AdminPlaceCreateDraftRequest,
    AdminPlaceDetailRead,
    AdminPlaceDuplicateCheckRequest,
    AdminPlaceUpdateRequest,
)
from schemas.admin_system_log import SystemLogListResponse, SystemLogRead
from services.admin_address_job_service import queue_address_refresh, run_address_refresh_operation
from services.admin_city_settings_service import city_settings_payload, update_city_toggle
from services.admin_place_bulk_service import apply_bulk, preview_bulk
from services.admin_place_create_service import create_draft_place
from services.admin_place_detail_service import build_admin_place_detail
from services.admin_place_duplicate_service import find_similar_places
from services.admin_place_lookup_service import lookup_place_candidates
from services.admin_place_update_service import update_admin_place_fields
from services.place_read_service import build_place_read
from services.system_log_service import list_system_logs, write_system_log

router = APIRouter(prefix="/admin", tags=["admin-place-ops"])

GITHUB_REPO = os.getenv("GITHUB_DEPLOY_REPO", "GoToValhalla/City-GO")
GITHUB_WORKFLOW = os.getenv("GITHUB_DEPLOY_WORKFLOW", "deploy.yml")
GITHUB_BRANCH = os.getenv("GITHUB_DEPLOY_BRANCH", "main")
GITHUB_TOKEN_ENV_KEYS = ("GITHUB_DEPLOY_TOKEN", "GITHUB_WORKFLOW_TOKEN", "GITHUB_TOKEN")


@router.get("/places/{place_id}/detail", response_model=AdminPlaceDetailRead)
def read_place_detail(place_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    payload = build_admin_place_detail(db, place_id)
    if payload is None:
        raise HTTPException(404, "Место не найдено")
    return AdminPlaceDetailRead.model_validate(payload)


@router.post("/places/lookup")
def lookup_place(body: AdminPlaceDuplicateCheckRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    try:
        return lookup_place_candidates(db, city_id=body.city_id, query=body.title)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/places/check-duplicates")
def check_duplicates(body: AdminPlaceDuplicateCheckRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return {"items": find_similar_places(db, city_id=body.city_id, title=body.title, lat=body.lat, lng=body.lng, address=body.address)}


@router.post("/places/create-draft", response_model=AdminPlaceDetailRead)
def create_draft(body: AdminPlaceCreateDraftRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    try:
        place = create_draft_place(db, body.model_dump(), actor=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    payload = build_admin_place_detail(db, place.id)
    return AdminPlaceDetailRead.model_validate(payload)


@router.patch("/places/{place_id}", response_model=AdminPlaceDetailRead)
def patch_place(place_id: int, body: AdminPlaceUpdateRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    fields = {key: value for key, value in body.model_dump().items() if value is not None}
    try:
        place = update_admin_place_fields(db, place_id, fields, actor=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if place is None:
        raise HTTPException(404, "Место не найдено")
    payload = build_admin_place_detail(db, place.id)
    return AdminPlaceDetailRead.model_validate(payload)


@router.post("/places/bulk/preview")
def bulk_preview(body: AdminBulkPreviewRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return preview_bulk(db, body.place_ids, body.action, body.params)


@router.post("/places/bulk/apply")
def bulk_apply(body: AdminBulkApplyRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    if not body.confirm:
        raise HTTPException(422, "Требуется confirm=true")
    return apply_bulk(db, body.place_ids, body.action, body.params, actor=auth.actor_id)


@router.post("/places/address-refresh")
def refresh_addresses(
    body: AdminAddressRefreshRequest,
    background_tasks: BackgroundTasks,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    op = queue_address_refresh(db, actor=auth.actor_id, city_slug=body.city_slug, place_ids=body.place_ids or None)
    if op.status == "queued":
        background_tasks.add_task(run_address_refresh_operation, op.id)
    return {"operation_id": op.id, "status": op.status, "result": op.result, "error": op.error_message}


@router.get("/cities/{city_slug}/settings")
def read_city_settings(city_slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    payload = city_settings_payload(db, city_slug)
    if payload is None:
        raise HTTPException(404, "Город не найден")
    return payload


@router.put("/cities/{city_slug}/settings/{key}")
def put_city_setting(city_slug: str, key: str, body: AdminCityToggleUpdateRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    try:
        update_city_toggle(db, city_slug=city_slug, key=key, value=body.value_bool, actor=auth.actor_id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return city_settings_payload(db, city_slug)


@router.get("/system-logs", response_model=SystemLogListResponse)
def read_system_logs(
    level: str | None = None, module: str | None = None, city_slug: str | None = None,
    request_id: str | None = None, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0),
    q: str | None = None, place_id: int | None = None, route_id: str | None = None,
    actor_id: str | None = None, environment: str | None = None,
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
):
    items, total = list_system_logs(
        db, level=level, module=module, city_slug=city_slug, request_id=request_id,
        q=q, place_id=place_id, route_id=route_id, actor_id=actor_id,
        environment=environment, sort=sort, limit=limit, offset=offset,
    )
    return SystemLogListResponse(items=[SystemLogRead.model_validate(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/deployment/status")
def deployment_status(auth: AdminContext = Depends(admin_required)):
    token_key = _configured_token_key()
    return {
        "enabled": token_key is not None,
        "mode": "github_actions_workflow_dispatch",
        "repo": GITHUB_REPO,
        "workflow": GITHUB_WORKFLOW,
        "branch": GITHUB_BRANCH,
        "token_configured": token_key is not None,
        "token_env_key": token_key,
        "action": "run_deploy_workflow",
        "deploy_note": "Кнопка запускает Production Deploy workflow для City-GO/main.",
    }


@router.post("/deployment/run-ci")
def run_ci_workflow(body: dict[str, object], auth: AdminContext = Depends(admin_required)):
    if body.get("confirm") is not True:
        raise HTTPException(422, "Требуется confirm=true")

    token = _github_token()
    if not token:
        raise HTTPException(503, "Не настроен GITHUB_DEPLOY_TOKEN или GITHUB_WORKFLOW_TOKEN")

    payload = _workflow_dispatch_payload()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    request = Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "City-Go-Admin",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urlopen(request, timeout=15) as response:
            status_code = response.getcode()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(exc.code, f"GitHub Actions error: {detail}") from exc
    except URLError as exc:
        raise HTTPException(502, f"GitHub недоступен: {exc.reason}") from exc

    return {
        "status": "queued",
        "github_status_code": status_code,
        "repo": GITHUB_REPO,
        "workflow": GITHUB_WORKFLOW,
        "branch": GITHUB_BRANCH,
    }


def _workflow_dispatch_payload() -> bytes:
    payload: dict[str, object] = {"ref": GITHUB_BRANCH}
    if GITHUB_WORKFLOW == "deploy.yml":
        payload["inputs"] = {"deploy_ref": GITHUB_BRANCH}
    return json.dumps(payload).encode("utf-8")


def _github_token() -> str | None:
    for key in GITHUB_TOKEN_ENV_KEYS:
        value = os.getenv(key)
        if value:
            return value
    return None


def _configured_token_key() -> str | None:
    for key in GITHUB_TOKEN_ENV_KEYS:
        if os.getenv(key):
            return key
    return None
