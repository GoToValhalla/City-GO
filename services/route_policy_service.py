"""Централизованная политика допуска категорий в маршруты."""
from __future__ import annotations
from dataclasses import dataclass
from models.category import Category
ROUTE_CONTEXTS=frozenset({"tourist_walk","family","food","coffee","practical","emergency","accessibility"})
ROUTE_POLICIES=frozenset({"always_allowed","allowed_by_context","useful_only","forbidden","manual_review"})
ALWAYS=frozenset({"museum","attraction","walk","park","beach","gallery","culture","historic","landmark","monument","viewpoint"})
CONTEXTUAL=frozenset({"coffee","cafe","food","restaurant","bar","pub","shopping_mall"})
USEFUL=frozenset({"pharmacy","bank","atm","parking","transport","bus_stop","toilets","information"})
FORBIDDEN=frozenset({"hospital","police","shelter","service","unknown"})
KNOWN=ALWAYS|CONTEXTUAL|USEFUL|FORBIDDEN
@dataclass(frozen=True,slots=True)
class RoutePolicyDecision:allowed:bool;requires_review:bool;reason:str

def evaluate_category_policy(category:Category|None,*,context:str="tourist_walk",fallback_code:str|None=None)->RoutePolicyDecision:
 if context not in ROUTE_CONTEXTS:return RoutePolicyDecision(False,True,"Неизвестный контекст маршрута.")
 if category is None:return evaluate_category_code_policy(fallback_code,context=context)
 if not category.is_active:return RoutePolicyDecision(False,True,"Категория архивирована.")
 policy=category.route_policy or "manual_review"
 if policy=="manual_review" and category.code in KNOWN:return evaluate_category_code_policy(category.code,context=context)
 if policy=="always_allowed":return RoutePolicyDecision(True,False,"Категория разрешена во всех маршрутах.")
 if policy=="forbidden":return RoutePolicyDecision(False,False,"Категория запрещена политикой маршрутов.")
 if policy=="manual_review":return RoutePolicyDecision(False,True,"Категория требует ручной проверки.")
 if policy=="useful_only":return RoutePolicyDecision(context in {"practical","emergency","accessibility"},False,"Инфраструктура разрешена только в практическом контексте.")
 contexts=set(category.route_contexts or []) or _default_contexts(category.code)
 return RoutePolicyDecision(context in contexts,False,"Контекст разрешён категорией." if context in contexts else "Контекст не разрешён категорией.")

def evaluate_category_code_policy(code:str|None,*,context:str="tourist_walk")->RoutePolicyDecision:
 value=(code or "").strip().lower()
 if value in ALWAYS:return RoutePolicyDecision(True,False,"Legacy-категория разрешена централизованной политикой.")
 if value in CONTEXTUAL:return RoutePolicyDecision(context in {"tourist_walk","family","food","coffee"},False,"Сценарная категория проверена централизованной политикой.")
 if value in USEFUL:return RoutePolicyDecision(context in {"practical","emergency","accessibility"},False,"Инфраструктурная категория разрешена только в практическом контексте.")
 if value in FORBIDDEN:return RoutePolicyDecision(False,False,"Категория запрещена централизованной политикой.")
 return RoutePolicyDecision(False,True,"Категория отсутствует или требует ручной проверки.")

def _default_contexts(code:str)->set[str]:
 if code in {"coffee","cafe"}:return {"tourist_walk","family","coffee","food"}
 if code in {"food","restaurant","bar","pub"}:return {"tourist_walk","family","food"}
 return {"tourist_walk"}
