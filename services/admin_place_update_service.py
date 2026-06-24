"""Обновление места из админки."""
from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from core.place_category_hierarchy import CATEGORY_LABELS_RU,ROUTE_EXCLUDED_CATEGORIES
from models.category import Category
from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.place_service import get_place_by_id
from services.product_event_service import record_event
from services.taxonomy_workflow_service import run_workflow
_ALLOWED=frozenset({"title","category","canonical_category","address","short_description","image_url","lat","lng","source","source_url","website","phone","atmosphere","inside","best_for","opening_hours","average_visit_duration_minutes","price_level","indoor","outdoor","dog_friendly","family_friendly","is_active","status","publication_status","verification_status","admin_comment","route_exclusion_reason","address_source","address_confidence"})

def update_admin_place_fields(db:Session,place_id:int,fields:dict[str,object],*,actor:str)->Place|None:
 place=get_place_by_id(db,place_id)
 if place is None:return None
 updates=dict(fields);reason=updates.pop("reason",None);category_changed="category" in updates or "canonical_category" in updates
 if "category" in updates and "canonical_category" not in updates:updates["canonical_category"]=str(updates.get("category")) if updates.get("category") else None
 if category_changed:
  code=str(updates.get("canonical_category") or updates.get("category") or "").strip().lower();category=db.query(Category).filter(Category.code==code).first()
  if category is None:
   eligible=code not in ROUTE_EXCLUDED_CATEGORIES;category=Category(code=code,name=CATEGORY_LABELS_RU.get(code,code.replace("_"," ").title()),user_name=CATEGORY_LABELS_RU.get(code),is_active=True,is_catalog_visible=True,is_searchable=True,is_route_eligible=eligible,route_policy="allowed_by_context" if eligible else "useful_only",route_contexts=[]);db.add(category);db.flush()
  elif not category.is_active:raise ValueError("Выбранная категория архивирована")
  place.category_id=category.id;updates["category"]=category.code;updates["canonical_category"]=category.code
 if updates.get("lat") is not None and updates.get("lng") is not None:
  lat=float(updates["lat"]);lng=float(updates["lng"])
  if abs(lat)<0.000001 and abs(lng)<0.000001:raise ValueError("Нельзя сохранить место с координатами 0,0")
 old={key:getattr(place,key) for key in updates if key in _ALLOWED}
 for key,value in updates.items():
  if key in _ALLOWED:setattr(place,key,value)
 if "visible_to_users" in updates:place.is_visible_in_catalog=bool(updates["visible_to_users"])
 if "searchable" in updates:place.is_searchable=bool(updates["searchable"])
 if "route_enabled" in updates:
  place.is_route_eligible=bool(updates["route_enabled"])
  if updates["route_enabled"]:place.route_exclusion_reason=None
  elif updates.get("route_exclusion_reason"):place.route_exclusion_reason=str(updates["route_exclusion_reason"])
 if updates.get("publication_status")=="published":place.is_published=True;place.published_at=datetime.utcnow()
 if updates.get("publication_status") in ("hidden","unpublished","draft","needs_review"):place.is_published=False
 if "tag_ids" in updates:
  db.query(PlaceTag).filter(PlaceTag.place_id==place_id).delete()
  for tag_id in updates["tag_ids"] or []:db.add(PlaceTag(place_id=place_id,tag_id=int(tag_id)))
 write_admin_audit_log(db,actor=actor,action="update_place_admin",entity_type="place",entity_id=place.id,old_value=old,new_value=updates,reason=str(reason) if reason else None);record_event(db,event_type="place_updated",place_id=place.id,commit=False);db.commit();db.refresh(place)
 if category_changed:run_workflow(db,workflow="after_category_change",request_id=uuid4().hex,idempotency_key=f"category:{place.id}:{place.updated_at}",entity_type="place",entity_id=str(place.id),payload={},actor=actor)
 return place
