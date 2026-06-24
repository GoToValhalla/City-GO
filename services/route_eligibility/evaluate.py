"""Оценка допуска места в маршрут через централизованную taxonomy policy."""
from __future__ import annotations
from dataclasses import dataclass
from models.city import City
from models.place import Place
from services.data_foundation_policy import ROUTE_ALLOWED_QUALITY_TIERS
from services.place_quality_signals import is_placeholder_title
from services.route_policy_service import evaluate_category_policy
@dataclass(frozen=True)
class RouteEligibilityResult:eligible:bool;reasons:tuple[str,...]

def evaluate_place_route_eligibility(place:Place,*,city:City|None=None,context:str="tourist_walk")->RouteEligibilityResult:
 reasons:list[str]=[]
 if not place.city_id:reasons.append("missing_city_id")
 if city is not None:
  if getattr(city,"is_active",True) is False:reasons.append("city_inactive")
  if getattr(city,"launch_status","published")!="published":reasons.append("city_not_published")
 if not getattr(place,"is_active",True):reasons.append("place_inactive")
 if getattr(place,"status","active")!="active":reasons.append("place_status_not_active")
 if (getattr(place,"lifecycle_status",None) or "active")!="active":reasons.append("lifecycle_not_active")
 if not getattr(place,"is_published",True):reasons.append("place_not_published")
 if not getattr(place,"is_visible_in_catalog",True):reasons.append("place_not_visible_in_catalog")
 if not getattr(place,"is_route_eligible",True):reasons.append("route_eligible_false")
 if is_placeholder_title(getattr(place,"title",None)):reasons.append("placeholder_title")
 if place.lat is None or place.lng is None:reasons.append("missing_coordinates")
 elif place.lat==0.0 and place.lng==0.0:reasons.append("invalid_coordinates")
 code=(getattr(place,"canonical_category",None) or getattr(place,"category",None) or "").strip().lower()
 policy=evaluate_category_policy(getattr(place,"category_ref",None),context=context,fallback_code=code)
 if not policy.allowed:reasons.append("route_policy_review" if policy.requires_review else f"forbidden_category:{code or 'unknown'}")
 quality=(getattr(place,"quality_tier",None) or "silver").strip().lower()
 if quality not in ROUTE_ALLOWED_QUALITY_TIERS:reasons.append(f"quality_tier_not_route_allowed:{quality or 'empty'}")
 if getattr(place,"is_spam_poi",False):reasons.append("spam_poi")
 if getattr(place,"is_duplicate_suspected",False):reasons.append("duplicate_suspected")
 if getattr(place,"critical_field_expired",False):reasons.append("critical_field_expired")
 if getattr(place,"publication_status","published")=="archived":reasons.append("place_archived")
 return RouteEligibilityResult(not reasons,tuple(reasons))
