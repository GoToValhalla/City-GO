"""Оркестратор pipeline: импорт → адреса → фото → качество → readiness."""
from __future__ import annotations
import json
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.cleanup_imported_places_quality import run as run_quality_cleanup
from data.scripts.enrich_place_images import run as run_image_enrich
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_log import log_import_event
from services.admin_city_import_runner import run_osm_import_only,summarize_import_results
from services.category_normalize_service import normalize_city_categories,normalize_places_categories
from services.city_readiness.score import compute_city_readiness
from services.import_pipeline.progress import append_step_warning,set_step
from services.import_pipeline.steps import STEP_CATEGORIES_TAGS,STEP_COLLECTING_PLACES,STEP_COMPUTING_QUALITY,STEP_COMPUTING_READINESS,STEP_FINDING_ADDRESSES,STEP_FINDING_IMAGES,STEP_PREPARING_DESCRIPTIONS,STEP_READY_FOR_REVIEW,STEP_RUNNING
from services.place_import_lifecycle_service import mark_place_for_review
IMAGE_LIMIT=2000
ADDRESS_LIMIT=5000

def run_enrichment_pipeline(db:Session,*,job:CityAdminImportJob,city:City,actor_id:str,force:bool=True,notify_completion:bool=True)->dict[str,Any]:
 city_id=int(city.id);original=(city.launch_status,bool(city.is_active));started=datetime.utcnow();warnings=[];results={}
 job.status="running";job.started_at=job.started_at or started;set_step(job,STEP_RUNNING);db.commit()
 try:
  set_step(job,STEP_COLLECTING_PLACES);_log(db,job,city.slug,actor_id,STEP_COLLECTING_PLACES,"started");db.commit()
  summary=summarize_import_results(run_osm_import_only(city.slug,force=force));results["import"]=summary
  job.scopes_succeeded=int(summary.get("scopes_succeeded") or 0);job.places_found=int(summary.get("places_found") or 0);job.places_saved=int(summary.get("places_saved") or 0)
  total=db.query(Place).filter(Place.city_id==city_id).count();set_step(job,STEP_COLLECTING_PLACES,total=total,processed=total,successful=job.places_saved,detail={"import_diff":summary});db.commit()
  if summary.get("status")!="success" and total<=0:raise RuntimeError(str(summary.get("last_error") or "Ошибка импорта OSM"))
  if summary.get("status")!="success":warning={"step":STEP_COLLECTING_PLACES,"error":str(summary.get("last_error") or "partial import")};warnings.append(warning);append_step_warning(job,STEP_COLLECTING_PLACES,warning["error"])
  addresses=_optional(db,job,city.slug,actor_id,STEP_FINDING_ADDRESSES,warnings,lambda:run_address_backfill(["--city",city.slug,"--limit",str(ADDRESS_LIMIT),"--apply"]));results["addresses"]=addresses;set_step(job,STEP_FINDING_ADDRESSES,processed=int(addresses.get("checked") or 0),successful=int(addresses.get("updated") or 0),failed=int(addresses.get("errors") or 0));db.commit()
  images=_optional(db,job,city.slug,actor_id,STEP_FINDING_IMAGES,warnings,lambda:run_image_enrich(["--city",city.slug,"--limit",str(IMAGE_LIMIT),"--apply"]));results["images"]=images;set_step(job,STEP_FINDING_IMAGES,processed=int(images.get("scanned_places") or 0),successful=int(images.get("created") or 0),failed=int(images.get("failed_image_lookup") or images.get("failed") or 0));db.commit()
  db.expire_all();places=_changed(db,city_id,started)
  for place in places:mark_place_for_review(place,reason="import_or_enrichment_changed")
  db.commit();set_step(job,STEP_PREPARING_DESCRIPTIONS,detail={"mode":"manual_required"});cats=normalize_places_categories(db,places=places,apply=True);results["categories"]=cats;set_step(job,STEP_CATEGORIES_TAGS,processed=int(cats.get("scanned") or 0),successful=int(cats.get("updated") or 0));db.commit()
  ids=sorted({int(p.id) for p in places});results.update(changed_place_ids=ids,has_changes=bool(ids),quality={"mode":"foundation","changed_places":len(ids)});set_step(job,STEP_COMPUTING_QUALITY,processed=len(ids),detail=results["quality"]);set_step(job,STEP_COMPUTING_READINESS)
  readiness=compute_city_readiness(db,city_slug=city.slug) or {};results["readiness"]=readiness;set_step(job,STEP_COMPUTING_READINESS,detail={"readiness_score":readiness.get("readiness_score")})
  if total<=0:raise RuntimeError("OSM import finished without places")
  set_step(job,STEP_READY_FOR_REVIEW,successful=len(ids),processed=len(ids));job.status="success_with_warnings" if warnings else "success";job.finished_at=datetime.utcnow();job.step_details={**dict(job.step_details or {}),"warnings":warnings,"changed_place_ids":ids,"has_changes":bool(ids),"import_summary":summary}
  if ids:city.launch_status="review_required";city.is_active=False
  else:city.launch_status,city.is_active=original
  city.last_import_at=job.finished_at;log_import_event(db,event="import_pipeline_finished",city_slug=city.slug,actor_id=actor_id,message=f"Pipeline #{job.id}: {len(ids)} изменений",details={"job_id":job.id,**results});db.commit()
  if notify_completion:_notify(city,job,total,len(ids),readiness,warnings)
  return results
 except Exception as exc:
  places=_changed(db,city_id,started);ids=sorted({int(p.id) for p in places})
  for place in places:mark_place_for_review(place,reason="partial_import_changed")
  total=db.query(Place).filter(Place.city_id==city_id).count();job.last_error=str(exc)[:2000];job.finished_at=datetime.utcnow();job.step_details={**dict(job.step_details or {}),"changed_place_ids":ids,"has_changes":bool(ids)}
  if total>0:
   job.status="partial_success"
   if ids:city.launch_status="review_required";city.is_active=False
   else:city.launch_status,city.is_active=original
  else:job.status="failed";city.launch_status,city.is_active=original
  db.commit()
  if total<=0:raise
  return results

def _changed(db:Session,city_id:int,since:datetime)->list[Place]:return db.query(Place).filter(Place.city_id==city_id,Place.updated_at>=since).order_by(Place.id).all()
def _notify(city,job,total,changed,readiness,warnings):send_admin_alert(title="Import completed with warnings" if warnings else "Import pipeline finished",message=f"{city.name}: {changed} мест обновлено и отправлено на проверку." if changed else f"{city.name}: изменений нет, публикация сохранена.",level="warning" if warnings else "info",city_slug=city.slug,job_id=int(job.id),details={"status":job.status,"places_total":total,"changed_places":changed,"readiness":readiness,"warnings":warnings})
def _optional(db,job,slug,actor,step,warnings,action):
 set_step(job,step);_log(db,job,slug,actor,step,"started");db.commit()
 try:result=action();_log(db,job,slug,actor,step,"success");return result if isinstance(result,dict) else {"result":result}
 except Exception as exc:warnings.append({"step":step,"error":str(exc)[:1000]});append_step_warning(job,step,exc);_log(db,job,slug,actor,step,"warning",error=str(exc));db.commit();return {"status":"warning","error":str(exc)[:1000]}
def _log(db,job,slug,actor,step,status,**details):
 payload={"city_slug":slug,"job_id":job.id,"step":step,"status":status,**details};print(json.dumps(payload,ensure_ascii=False,default=str));log_import_event(db,event="import_step",city_slug=slug,actor_id=actor,message=f"{step}: {status}",details=payload)
