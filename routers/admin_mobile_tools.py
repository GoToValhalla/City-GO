from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.place import Place
from services.admin_mobile_place_review import list_review_cities, next_review_place, publish_place, rejected_places, reject_place
from services.system_log_service import write_system_log

router = APIRouter(prefix="/mobile-tools", tags=["admin-mobile-tools"])


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


@router.post("/places/{place_id}/defer")
def defer_current(place_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return _move_back_to_queue(db, place_id=place_id, actor=auth.actor_id, action="deferred")


@router.post("/places/{place_id}/restore")
def restore_current(place_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    return _move_back_to_queue(db, place_id=place_id, actor=auth.actor_id, action="restored")


def _move_back_to_queue(db: Session, *, place_id: int, actor: str, action: str) -> dict[str, object]:
    place = db.get(Place, place_id)
    if place is None:
        return {"action": "not_found", "place_id": place_id}
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_route_eligible = False
    place.is_searchable = False
    place.publication_status = "needs_review"
    place.publication_comment = f"{action} from mobile tools"
    place.updated_at = datetime.utcnow()
    db.add(place)
    write_system_log(db, level="info", module="mobile_review", message=f"mobile_review_{action}: {place.title}", details={"action": f"mobile_review_{action}"}, city_slug=place.city.slug if place.city else None, place_id=place.id, actor_id=actor, commit=False)
    db.commit()
    return {"action": action, "place_id": place.id}
