"""Admin API for Place Data Enrichment batch workflow."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.place_enrichment import (
    EnrichmentAIRequest,
    EnrichmentAIResult,
    EnrichmentBatchListResponse,
    EnrichmentExportListResponse,
    EnrichmentExportMeta,
    ImportApplyResult,
    ImportPreviewResult,
    PlaceEnrichmentExportRequest,
)
from services.openai_client import OpenAIClientError
from services.place_enrichment_ai_service import run_ai_batch_enrichment
from services.place_enrichment_import_service import run_import_apply, run_import_preview
from services.place_enrichment_service import (
    get_batch_file_path,
    get_export_csv_path,
    list_enrichment_batches,
    list_enrichment_exports,
    run_enrichment_export,
)

router = APIRouter(prefix="/admin/place-enrichment", tags=["admin-place-enrichment"])


@router.post("/export", response_model=EnrichmentExportMeta)
def create_enrichment_export(
    req: PlaceEnrichmentExportRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> EnrichmentExportMeta:
    return run_enrichment_export(db, req, actor=auth.actor_id)


@router.get("/exports", response_model=EnrichmentExportListResponse)
def get_enrichment_exports(auth: AdminContext = Depends(admin_required)) -> EnrichmentExportListResponse:
    items = list_enrichment_exports(limit=50)
    return EnrichmentExportListResponse(items=items, total=len(items))


@router.get("/batches", response_model=EnrichmentBatchListResponse)
def get_enrichment_batches(auth: AdminContext = Depends(admin_required)) -> EnrichmentBatchListResponse:
    items = list_enrichment_batches(limit=50)
    return EnrichmentBatchListResponse(items=items, total=len(items))


@router.get("/exports/{export_id}/download")
def download_enrichment_export(export_id: str, auth: AdminContext = Depends(admin_required)) -> FileResponse:
    path = get_export_csv_path(export_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path=str(path), media_type="text/csv", filename=path.name)


@router.get("/batches/{batch_id}/files/{filename}")
def download_batch_file(batch_id: str, filename: str, auth: AdminContext = Depends(admin_required)) -> FileResponse:
    allowed = {"export.csv", "export.meta.json", "enriched.csv", "import.preview.json", "import.result.json"}
    if filename not in allowed:
        raise HTTPException(status_code=400, detail="File not allowed")
    path = get_batch_file_path(batch_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="File not found")
    media = "application/json" if filename.endswith(".json") else "text/csv"
    return FileResponse(path=str(path), media_type=media, filename=filename)


@router.post("/batches/{batch_id}/ai-enrich", response_model=EnrichmentAIResult)
def ai_enrich_batch(
    batch_id: str,
    req: EnrichmentAIRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> EnrichmentAIResult:
    try:
        return run_ai_batch_enrichment(db, batch_id, req or EnrichmentAIRequest(), actor=auth.actor_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OpenAIClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/preview", response_model=ImportPreviewResult)
def preview_batch_import(
    batch_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
) -> ImportPreviewResult:
    try:
        return run_import_preview(db, batch_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/apply", response_model=ImportApplyResult)
def apply_batch_import(
    batch_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
) -> ImportApplyResult:
    try:
        return run_import_apply(db, batch_id, actor=auth.actor_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc