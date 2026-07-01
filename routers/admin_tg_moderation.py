from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.admin_mobile_place_review import list_review_cities, next_review_place, publish_place, rejected_places, reject_place

router = APIRouter(prefix="/admin/tg-moderation", tags=["admin-tg-moderation"])


@router.get("/cities")
def read_cities(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return list_review_cities(db)


@router.get("/places/next")
def read_next_place(city_slug: str = Query(...), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return next_review_place(db, city_slug)


@router.get("/places/rejected")
def read_rejected(city_slug: str = Query(...), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return rejected_places(db, city_slug)


@router.post("/places/{place_id}/publish")
def publish_current(place_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return publish_place(db, place_id, auth.actor_id)


@router.post("/places/{place_id}/reject")
def reject_current(place_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return reject_place(db, place_id, auth.actor_id)
