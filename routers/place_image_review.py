"""Admin API очереди проверки фотографий мест."""
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from core.admin_auth import AdminContext,admin_required
from db.dependencies import get_db
from schemas.place_image import PendingPlaceImageRead,PendingPlaceImagesResponse,PlaceImageActionResult,PlaceImageBulkActionResult,PlaceImageBulkReviewAction,PlaceImageReviewAction
from services.feature_toggle_guards import assert_photo_moderation
from services.place_image_review_service import approve_place_image,bulk_review_place_images,get_pending_place_images,reject_place_image,set_primary_place_image
from services.taxonomy_workflow_service import run_workflow

router=APIRouter(prefix="/admin/place-images",tags=["admin-place-images"])

@router.get("/pending",response_model=PendingPlaceImagesResponse)
def read_pending_place_images(city_slug:str|None=Query(None),limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 assert_photo_moderation(db);items,total=get_pending_place_images(db,city_slug=city_slug,limit=limit,offset=offset);return PendingPlaceImagesResponse(items=[PendingPlaceImageRead.model_validate(item) for item in items],total=total,limit=limit,offset=offset)

@router.post("/{image_id}/approve",response_model=PlaceImageActionResult)
def post_approve_place_image(image_id:int,body:PlaceImageReviewAction|None=None,auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 try:image=approve_place_image(db,image_id,actor=auth.actor_id,comment=None if body is None else body.comment)
 except LookupError as exc:raise HTTPException(404,str(exc)) from exc
 _photo_workflow(db,image,auth.actor_id,"approve");return PlaceImageActionResult.model_validate(image)

@router.post("/{image_id}/reject",response_model=PlaceImageActionResult)
def post_reject_place_image(image_id:int,body:PlaceImageReviewAction|None=None,auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 try:image=reject_place_image(db,image_id,actor=auth.actor_id,comment=None if body is None else body.comment)
 except LookupError as exc:raise HTTPException(404,str(exc)) from exc
 return PlaceImageActionResult.model_validate(image)

@router.post("/{image_id}/set-primary",response_model=PlaceImageActionResult)
def post_set_primary_place_image(image_id:int,auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 try:image=set_primary_place_image(db,image_id,actor=auth.actor_id)
 except LookupError as exc:raise HTTPException(404,str(exc)) from exc
 except ValueError as exc:raise HTTPException(400,str(exc)) from exc
 _photo_workflow(db,image,auth.actor_id,"primary");return PlaceImageActionResult.model_validate(image)

def _photo_workflow(db:Session,image:object,actor:str,action:str)->None:
 place_id=getattr(image,"place_id",None)
 if place_id is None:return
 run_workflow(db,workflow="after_photo_confirmation",request_id=uuid4().hex,idempotency_key=f"photo:{action}:{getattr(image,'id','')}:{getattr(image,'updated_at','')}",entity_type="place",entity_id=str(place_id),payload={"image_id":getattr(image,"id",None)},actor=actor)
