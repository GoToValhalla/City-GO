from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.place_verification import PlaceNearbyConfirmRequest, PlaceVerificationEnqueueSummary, PlaceVerificationQueueResponse, PlaceVerificationRequest, PlaceVerificationResult, PlaceVerificationStats, PlaceVerificationSummary, PlaceVerificationTaskRead
from services.admin_audit_service import write_admin_audit_log
from services.feature_toggle_guards import assert_verification_enabled
from services.place_verification_service import apply_place_verification, confirm_place_nearby, enqueue_stale_places, get_place_verification_queue, pending_verification_tasks, place_verification_stats, place_verification_summary
from services.taxonomy_workflow_service import run_workflow

router=APIRouter(prefix="/place-verification",tags=["place-verification"])
admin_router=APIRouter(prefix="/admin/place-verifications",tags=["admin-place-verifications"])

@router.post("/enqueue-stale/{city_slug}",response_model=PlaceVerificationEnqueueSummary)
def post_enqueue_stale_places(city_slug:str,auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 summary=enqueue_stale_places(db,city_slug);write_admin_audit_log(db,actor=auth.actor_id,action="enqueue_stale_verification",entity_type="city",entity_id=city_slug,new_value={"enqueued":summary.enqueued,"already_pending":summary.already_pending});db.commit();return summary

@router.get("/queue",response_model=list[PlaceVerificationTaskRead])
def get_pending_verification_tasks(db:Session=Depends(get_db)):return list(map(PlaceVerificationTaskRead.model_validate,pending_verification_tasks(db)))

@admin_router.get("/queue",response_model=PlaceVerificationQueueResponse)
def get_admin_place_verification_queue(city_slug:str|None=Query(None),status:str|None=Query(None),confidence_level:str|None=Query(None),max_confidence:int|None=Query(None,ge=0,le=100),category:str|None=Query(None),lat:float|None=Query(None),lng:float|None=Query(None),radius_meters:float|None=Query(None,ge=1),limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 assert_verification_enabled(db);items,total=get_place_verification_queue(db,city_slug=city_slug,status=status,confidence_level_filter=confidence_level,max_confidence=max_confidence,category=category,lat=lat,lng=lng,radius_meters=radius_meters,limit=limit,offset=offset);return PlaceVerificationQueueResponse(items=items,total=total,limit=limit,offset=offset)

@admin_router.post("/places/{place_id}/verify",response_model=PlaceVerificationResult)
def post_admin_verify_place(place_id:int,body:PlaceVerificationRequest,auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 try:place=apply_place_verification(db,place_id,action=body.action,verifier=auth.actor_id,verifier_lat=body.verifier_lat,verifier_lng=body.verifier_lng,photo_url=body.photo_url,comment=body.comment)
 except LookupError as exc:raise HTTPException(404,str(exc)) from exc
 except ValueError as exc:raise HTTPException(400,str(exc)) from exc
 if body.action=="exists":run_workflow(db,workflow="after_place_confirmation",request_id=uuid4().hex,idempotency_key=f"verify:{place.id}:{place.verified_at}",entity_type="place",entity_id=str(place.id),payload={},actor=auth.actor_id)
 return _place_result(place)

@admin_router.post("/places/{place_id}/confirm-nearby",response_model=PlaceVerificationResult)
def post_admin_confirm_place_nearby(place_id:int,body:PlaceNearbyConfirmRequest,auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):
 try:place=confirm_place_nearby(db,place_id,verifier=auth.actor_id,verifier_lat=body.verifier_lat,verifier_lng=body.verifier_lng,comment=body.comment)
 except LookupError as exc:raise HTTPException(404,str(exc)) from exc
 except ValueError as exc:raise HTTPException(400,str(exc)) from exc
 run_workflow(db,workflow="after_place_confirmation",request_id=uuid4().hex,idempotency_key=f"nearby:{place.id}:{place.verified_at}",entity_type="place",entity_id=str(place.id),payload={},actor=auth.actor_id);return _place_result(place)

@admin_router.get("/summary",response_model=PlaceVerificationSummary)
def get_admin_place_verification_summary(city_slug:str|None=Query(None),auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):return PlaceVerificationSummary(**place_verification_summary(db,city_slug=city_slug))

@admin_router.get("/stats",response_model=PlaceVerificationStats)
def get_admin_place_verification_stats(city_slug:str|None=Query(None),auth:AdminContext=Depends(admin_required),db:Session=Depends(get_db)):return PlaceVerificationStats(**place_verification_stats(db,city_slug or "khanty-mansiysk"))

def _place_result(place):return PlaceVerificationResult(place_id=place.id,title=place.title,status=place.status,is_active=place.is_active,existence_confidence_score=place.existence_confidence_score,existence_confidence_level=place.existence_confidence_level,verification_status=place.verification_status,verification_source=place.verification_source,verification_method=place.verification_method,verified_at=place.verified_at,verified_by=place.verified_by,verification_comment=place.verification_comment)
