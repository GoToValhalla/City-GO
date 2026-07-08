"""Нормализация импортированных мест через управляемую таксономию."""
from __future__ import annotations
from sqlalchemy.orm import Session
from core.place_category_hierarchy import CATEGORY_LABELS_RU,LEGACY_TO_CANONICAL,ROUTE_EXCLUDED_CATEGORIES,normalize_category_code
from core.place_taxonomy import PLACE_CATEGORIES
from models.category import Category
from models.city import City
from models.place import Place
from models.source_observation import SourceObservation
from services.taxonomy_automation_service import normalize_place,validate_place


def normalize_city_categories(db:Session,*,city_slug:str,apply:bool=True)->dict[str,object]:
 city=db.query(City).filter(City.slug==city_slug).first()
 if city is None:raise ValueError(f"Город не найден: {city_slug}")
 result=normalize_places_categories(db,places=db.query(Place).filter(Place.city_id==city.id).all(),apply=apply)
 if apply:db.commit()
 return result


def normalize_places_categories(db:Session,*,places:list[Place],apply:bool=True)->dict[str,object]:
 scanned=updated=synced=skipped=unknown=conflicts=0
 category_cache:dict[str,Category|None]={}
 for place in places:
  scanned+=1
  if apply:
   automated=normalize_place(db,place,actor="import_pipeline")
   if automated["applied"]:
    updated+=1;validate_place(db,place);continue
   conflicts+=1
  canon=_category_for_place(db,place)
  if canon is None or canon not in PLACE_CATEGORIES:skipped+=1;unknown+=1;continue
  category=_canonical_category(db,canon,apply=apply,cache=category_cache);category_id=getattr(category,"id",None)
  category_changed=canon!=place.category;canonical_changed=canon!=place.canonical_category;fk_changed=bool(category_id) and place.category_id!=category_id
  if not category_changed and not canonical_changed and not fk_changed:skipped+=1;continue
  if apply:
   place.category=canon;place.canonical_category=canon
   if category_id:place.category_id=category_id
   validate_place(db,place);db.add(place)
  if category_changed:updated+=1
  else:synced+=1
 return {"scanned":scanned,"updated":updated,"synced":synced,"skipped":skipped,"unknown":unknown,"conflicts":conflicts,"legacy_map":LEGACY_TO_CANONICAL}


def _category_for_place(db:Session,place:Place)->str|None:
 canon=normalize_category_code(place.category or place.canonical_category)
 if canon!="service" or place.id is None:return canon
 observations=db.query(SourceObservation.raw_category).filter(SourceObservation.canonical_place_id==place.id).order_by(SourceObservation.last_seen_at.desc(),SourceObservation.id.desc()).all()
 for (raw_category,) in observations:
  candidate=normalize_category_code(raw_category)
  if candidate and candidate!="service" and candidate in PLACE_CATEGORIES:return candidate
 return canon


def _canonical_category(db:Session,code:str,*,apply:bool,cache:dict[str,Category|None]|None=None)->Category|None:
 if cache is not None and code in cache:return cache[code]
 category=db.query(Category).filter(Category.code==code).first()
 if category is None and apply:
  route_eligible=code not in ROUTE_EXCLUDED_CATEGORIES
  category=Category(code=code,name=CATEGORY_LABELS_RU.get(code,code),user_name=CATEGORY_LABELS_RU.get(code,code),is_active=True,is_route_eligible=route_eligible,is_catalog_visible=True,is_searchable=True,is_default_enabled=True,is_spam_category=False,route_policy="manual_review" if code=="service" else "useful_only" if not route_eligible else "allowed_by_context",route_contexts=[])
  db.add(category);db.flush()
 if cache is not None:cache[code]=category
 return category
