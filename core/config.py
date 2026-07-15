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

    local_cache_enabled: bool = True
    local_cache_dir: str = "/app/.cache/city-go"
    local_cache_default_ttl_seconds: int = 2_592_000
    local_cache_size_limit_bytes: int = 1_073_741_824
    local_cache_shards: int = 8

    walking_router_url: str = "https://routing.openstreetmap.de/routed-foot/route/v1/driving"
    walking_router_timeout_seconds: int = 12
    walking_router_user_agent: str = "CityGoWalkingRouter/1.0"

    geoapify_api_key: str = ""
    geocoding_timeout_seconds: int = 10

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_quality_model: str = "gpt-4.1"
    openai_timeout_seconds: int = 45

    data_quality_low_confidence_threshold: float = 0.5
    data_quality_hard_gates_enabled: bool = False

    place_address_geocoder_user_agent: str = "CityGoAddressBackfill/1.0"

    bot_token: str = ""
    bot_webhook_secret: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_admin_user_ids: str = ""

    citygo_debug_reports_telegram_enabled: bool = False
    citygo_debug_reports_telegram_chat_id: str = ""
    citygo_debug_reports_admin_base_url: str = ""

    backend_base_url: str = "http://127.0.0.1:8000"
    telegram_mini_app_url: str = ""
    default_city_slug: str = "zelenogradsk"

    coffee_category_id: int | None = None
    coffee_tag_id: int | None = None
    food_category_id: int | None = None
    food_tag_id: int | None = None
    walks_category_id: int | None = None
    walks_tag_id: int | None = None
    dog_friendly_category_id: int | None = None
    dog_friendly_tag_id: int | None = None

    admin_api_token: str = ""

    verification_scheduler_enabled: bool = False
    verification_scheduler_interval_hours: int = 24
    verification_scheduler_city_slugs: str = ""

    import_worker_scheduler_enabled: bool = False
    import_worker_scheduler_interval_seconds: int = 15
    import_worker_scheduler_batch_limit: int = 1

    admin_allow_in_web_worker_run_once: bool = False

    # Import-worker safety. Local/CI defaults keep safe mode disabled; production
    # Compose supplies the measured host/cgroup contract explicitly.
    import_worker_safe_mode: bool = False
    import_worker_max_runtime_seconds: int = 300
    import_worker_backend_health_url: str = "http://backend:8000/ready"
    import_worker_min_available_memory_mb: int = 256
    # Separate from import_worker_min_available_memory_mb (the pre-container
    # startup floor, checked once before the container exists). The worker
    # container's own baseline overhead (Python process, DB pool, imports)
    # legitimately costs 60-90 MB of host MemAvailable once running, so
    # reusing the startup floor here as the per-job claim gate makes a
    # healthy post-start host self-deadlock: the queued job is skipped
    # forever even though nothing is actually unsafe.
    import_worker_min_job_claim_memory_mb: int = 350
    import_worker_min_container_memory_mb: int = 512
    import_worker_min_container_headroom_mb: int = 400
    import_worker_runtime_host_floor_mb: int = 256
    import_worker_runtime_cgroup_percent: int = 85
    # Legacy explicit heavy-job switch: <=0 blocks; positive enables only after
    # the independent host/cgroup resource preflight succeeds.
    import_worker_max_full_import_places_low_memory: int = 0

    destination_foundation_enabled: bool = False
    destination_catalog_reads_enabled: bool = False
    destination_route_reads_enabled: bool = False
    destination_import_enabled: bool = False

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
