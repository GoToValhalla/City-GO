"""
Загрузка настроек приложения из переменных окружения и опционально из `.env`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "City Guide API"
    app_env: str = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/city_guide"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    db_statement_timeout_ms: int = 15_000
    db_lock_timeout_ms: int = 5_000

    # Local persistent cache for import/enrichment external calls. This is not distributed state.
    local_cache_enabled: bool = True
    local_cache_dir: str = "/app/.cache/city-go"
    local_cache_default_ttl_seconds: int = 2_592_000
    local_cache_size_limit_bytes: int = 1_073_741_824
    local_cache_shards: int = 8

    # Pedestrian routing provider. The default is a public OSRM foot instance and can be
    # replaced with a self-hosted compatible endpoint without frontend changes.
    walking_router_url: str = "https://routing.openstreetmap.de/routed-foot/route/v1/driving"
    walking_router_timeout_seconds: int = 12
    walking_router_user_agent: str = "CityGoWalkingRouter/1.0"

    # Optional Geoapify key. Если ключ не задан, typed address не геокодится,
    # а маршрут строится от координат, которые пришли от клиента.
    geoapify_api_key: str = ""
    geocoding_timeout_seconds: int = 10

    # OpenAI API for controlled admin AI enrichment. Key is runtime-only and must not be committed.
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_quality_model: str = "gpt-4.1"
    openai_timeout_seconds: int = 45

    # Data quality foundation: diagnostic by default, never a publication blocker unless explicitly enabled.
    data_quality_low_confidence_threshold: float = 0.5
    data_quality_hard_gates_enabled: bool = False

    # Nominatim User-Agent для backfill адресов. Без example.com и пустых значений.
    place_address_geocoder_user_agent: str = "CityGoAddressBackfill/1.0"

    # Telegram Bot — токен API бота (Long Poll / webhook).
    bot_token: str = ""
    bot_webhook_secret: str = ""

    # Telegram runtime alerts — чат, куда уходят ошибки import-worker/enrichment.
    # TELEGRAM_BOT_TOKEN переиспользует того же бота, что и CI/deploy notifications.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_admin_user_ids: str = ""

    # Mobile debug reports: stored in DB; Telegram is opt-in and best-effort.
    citygo_debug_reports_telegram_enabled: bool = False
    citygo_debug_reports_telegram_chat_id: str = ""
    citygo_debug_reports_admin_base_url: str = ""

    # Backend URL for Telegram bot — базовый URL этого FastAPI для запросов из бота.
    backend_base_url: str = "http://127.0.0.1:8000"

    # Public HTTPS frontend URL opened by Telegram Web App buttons.
    telegram_mini_app_url: str = ""

    # Telegram Bot defaults — город по умолчанию в сценариях бота (slug).
    default_city_slug: str = "zelenogradsk"

    # Optional filters for coffee places — опциональные id категории/тега для сценария «кофе».
    coffee_category_id: int | None = None
    coffee_tag_id: int | None = None

    # Optional filters for food places — опциональные id для сценария «еда».
    food_category_id: int | None = None
    food_tag_id: int | None = None

    # Optional filters for walking places — опциональные id для dog-friendly подборок.
    walks_category_id: int | None = None
    walks_tag_id: int | None = None

    # Optional filters for dog-friendly places — опциональные id для dog-friendly подборок.
    dog_friendly_category_id: int | None = None
    dog_friendly_tag_id: int | None = None

    # Admin API token — Bearer-токен для всех /admin/* endpoints.
    # В production обязателен (app завершится при отсутствии).
    # В local/staging задаётся явно, без значения по умолчанию.
    admin_api_token: str = ""

    # Scheduled place re-verification enqueue — включается явно в окружении.
    verification_scheduler_enabled: bool = False
    verification_scheduler_interval_hours: int = 24
    verification_scheduler_city_slugs: str = ""

    # Admin import worker fallback scheduler. Production web runtime enables it
    # implicitly so queued admin imports are consumed even without a separate daemon.
    import_worker_scheduler_enabled: bool = False
    import_worker_scheduler_interval_seconds: int = 15
    import_worker_scheduler_batch_limit: int = 1

    # POST /admin/import-queue/run-once must NOT execute heavy worker iterations
    # inside the web process by default — it shares RAM/CPU/GIL/DB pool with
    # public traffic, so a slow enrichment run there is a production risk even
    # when dispatched off the shared threadpool. This is an explicit, narrow
    # emergency/local override, not a general execution mode.
    admin_allow_in_web_worker_run_once: bool = False

    # Import-worker safety framework (added after the 2026-07-10 OOM incident:
    # a full Kaliningrad import ran on a ~1GB host with no swap, the worker was
    # OOM-killed, and the backend became unreachable behind nginx). Defaults are
    # local-dev-permissive (safe_mode off, no full-import block) so existing
    # local/CI workflows are unaffected; production compose sets these explicitly.
    import_worker_safe_mode: bool = False
    import_worker_max_runtime_seconds: int = 300
    import_worker_backend_health_url: str = "http://backend:8000/ready"
    import_worker_min_available_memory_mb: int = 256
    # 0 means: block ALL full-import/heavy jobs in safe mode on this host,
    # regardless of the target city's actual place count — the current
    # production host cannot safely run a full import at any size.
    import_worker_max_full_import_places_low_memory: int = 0

    # Destination-first foundation (phased rollout; defaults keep legacy city flow).
    destination_foundation_enabled: bool = False
    destination_catalog_reads_enabled: bool = False
    destination_route_reads_enabled: bool = False
    destination_import_enabled: bool = False

    # Dark-launch user foundation flags. Defaults must keep the current public
    # product flow unchanged: no login, no visible profile, no public reviews,
    # no fake ratings, no server-side favorites/history writes.
    feature_auth_enabled: bool = False
    feature_profile_enabled: bool = False
    feature_favorites_enabled: bool = False
    feature_saved_routes_enabled: bool = False
    feature_route_history_enabled: bool = False
    feature_reviews_enabled: bool = False
    feature_public_reviews_enabled: bool = False
    feature_review_votes_enabled: bool = False
    feature_user_photos_enabled: bool = False
    feature_suggestions_enabled: bool = False
    feature_moderation_enabled: bool = False
    feature_telegram_identity_enabled: bool = False
    feature_account_linking_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
