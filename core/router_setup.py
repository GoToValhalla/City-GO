from fastapi import FastAPI

from routers.admin import router as admin_router
from routers.admin_ai import router as admin_ai_router
from routers.admin_background_operations import router as admin_background_operations_router
from routers.admin_bot_analytics import router as admin_bot_analytics_router
from routers.admin_br_model import router as admin_br_model_router
from routers.admin_coverage_gaps import router as admin_coverage_gaps_router
from routers.admin_data_pipeline import router as admin_data_pipeline_router
from routers.admin_data_quality import router as admin_data_quality_router
from routers.admin_emergency_hide import router as admin_emergency_hide_router
from routers.admin_import_jobs import router as admin_import_jobs_router
from routers.admin_import_pipeline import router as admin_import_pipeline_router
from routers.admin_import_queue import router as admin_import_queue_router
from routers.admin_ops import router as admin_ops_router
from routers.admin_read_models import router as admin_read_models_router
from routers.admin_reviews import router as admin_reviews_router
from routers.admin_route_health import router as admin_route_health_router
from routers.admin_route_ops import router as admin_route_ops_router
from routers.admin_route_eligibility import router as admin_route_eligibility_router
from routers.admin_place_ops import router as admin_place_ops_router
from routers.admin_place_search import router as admin_place_search_router
from routers.admin_place_change_review import router as admin_place_change_review_router
from routers.admin_publication_policy import router as admin_publication_policy_router
from routers.admin_publication_reconciliation import router as admin_publication_reconciliation_router
from routers.admin_platform import router as admin_platform_router
from routers.admin_taxonomy import router as admin_taxonomy_router
from routers.ai import router as ai_router
from routers.categories import router as categories_router
from routers.city_expansion import router as city_expansion_router
from routers.cities import router as cities_router
from routers.collection_places import router as collection_places_router
from routers.collections import router as collections_router
from routers.geo import router as geo_router
from routers.itinerary import router as itinerary_router
from routers.nearby import router as nearby_router
from routers.navigation_events import router as nav_events_router
from routers.open_now import router as open_now_router
from routers.place_coverage import router as place_coverage_router
from routers.place_enrichment import router as place_enrichment_router
from routers.place_discovery import router as place_discovery_router
from routers.place_image_review import router as place_image_review_router
from routers.place_import_logs import router as place_import_logs_router
from routers.place_search import router as place_search_router
from routers.place_seed_dry_run import router as place_seed_dry_run_router
from routers.place_seed_import import router as place_seed_import_router
from routers.place_seed_validation import router as place_seed_validation_router
from routers.place_tags import router as place_tags_router
from routers.place_taxonomy import router as place_taxonomy_router
from routers.place_taxonomy_diagnostics import router as taxonomy_diagnostics_router
from routers.place_verification import admin_router as place_verification_admin_router
from routers.place_verification import router as place_verification_router
from routers.places import router as places_router
from routers.recommendations import router as recommendations_router
from routers.route_analytics import router as route_analytics_router
from routers.route_feedback import router as route_feedback_router
from routers.route_drafts import router as route_drafts_router
from routers.route_places import router as route_places_router
from routers.route_sessions import router as route_sessions_router
from routers.routes import router as routes_router
from routers.tags import router as tags_router
from routers.telegram_bot_webhook import router as telegram_bot_webhook_router
from routers.user_routes import router as user_routes_router
from routers.user_signals import router as user_signals_router
from routers.verification import router as verification_router


def include_app_routers(app: FastAPI) -> None:
    tuple(map(app.include_router, _ROOT_ROUTERS))
    app.include_router(recommendations_router)
    app.include_router(recommendations_router, prefix="/v1")
    app.include_router(user_routes_router, prefix="/v1")
    app.include_router(user_signals_router)
    app.include_router(verification_router, prefix="/v1")


_ROOT_ROUTERS = (
    admin_taxonomy_router,
    admin_router,
    admin_read_models_router,
    admin_reviews_router,
    admin_br_model_router,
    admin_ai_router,
    admin_background_operations_router,
    admin_bot_analytics_router,
    admin_coverage_gaps_router,
    admin_data_pipeline_router,
    admin_data_quality_router,
    admin_emergency_hide_router,
    admin_import_queue_router,
    admin_import_jobs_router,
    admin_import_pipeline_router,
    admin_ops_router,
    admin_route_health_router,
    admin_route_ops_router,
    admin_route_eligibility_router,
    admin_place_ops_router,
    admin_place_search_router,
    admin_place_change_review_router,
    admin_publication_policy_router,
    admin_publication_reconciliation_router,
    admin_platform_router,
    ai_router,
    categories_router,
    city_expansion_router,
    cities_router,
    collections_router,
    geo_router,
    collection_places_router,
    itinerary_router,
    nav_events_router,
    nearby_router,
    open_now_router,
    place_coverage_router,
    place_enrichment_router,
    place_discovery_router,
    place_image_review_router,
    place_import_logs_router,
    place_search_router,
    place_seed_dry_run_router,
    place_seed_import_router,
    place_seed_validation_router,
    place_taxonomy_router,
    taxonomy_diagnostics_router,
    place_verification_router,
    place_verification_admin_router,
    places_router,
    route_analytics_router,
    route_feedback_router,
    route_drafts_router,
    routes_router,
    route_places_router,
    route_sessions_router,
    tags_router,
    place_tags_router,
    telegram_bot_webhook_router,
)
