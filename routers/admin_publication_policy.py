from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.publication_policy_summary import get_publication_policy_summary

router = APIRouter(prefix="/admin/publication-policy", tags=["admin-publication-policy"])


@router.get("/summary")
def read_publication_policy_summary(
    days: int = Query(default=7, ge=1, le=90),
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return get_publication_policy_summary(db, days=days, city_slug=city_slug)
