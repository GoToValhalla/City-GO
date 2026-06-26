from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.publication_reconciliation import (
    PublicationReconciliationApplyRequest,
    PublicationReconciliationResponse,
    PublicationReconciliationRollbackRequest,
    PublicationReconciliationRollbackResponse,
)
from services.publication_reconciliation_service import (
    apply_publication_reconciliation,
    publication_reconciliation_snapshot,
    rollback_publication_reconciliation,
)

router = APIRouter(prefix="/admin/publication-reconciliation", tags=["admin-publication-reconciliation"])


@router.get("/snapshot")
def read_publication_snapshot(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return publication_reconciliation_snapshot(db)


@router.post("/apply", response_model=PublicationReconciliationResponse)
def apply_reconciliation(
    payload: PublicationReconciliationApplyRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PublicationReconciliationResponse:
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Требуется confirm=true; публикация городов не выполняется автоматически.")
    return PublicationReconciliationResponse(
        **apply_publication_reconciliation(
            db,
            actor=auth.actor_id,
            city_slugs=payload.city_slugs,
            reason=payload.reason,
        )
    )


@router.post("/rollback", response_model=PublicationReconciliationRollbackResponse)
def rollback_reconciliation(
    payload: PublicationReconciliationRollbackRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PublicationReconciliationRollbackResponse:
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Требуется confirm=true для rollback.")
    return PublicationReconciliationRollbackResponse(
        **rollback_publication_reconciliation(
            db,
            audit_ids=payload.audit_ids,
            actor=auth.actor_id,
            reason=payload.reason,
        )
    )
