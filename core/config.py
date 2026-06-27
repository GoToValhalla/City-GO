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

    # Nominatim User-Agent для backfill адресов. Без example.com и пустых значений.
    place_address_geocoder_user_agent: str = "CityGoAddressBackfill/1.0"

    # Telegram Bot — токен API бота (Long Poll / webhook).
    bot_token: str = ""
    bot_webhook_secret: str = ""

    # Telegram runtime alerts — чат, куда уходят ошибки import-worker/enrichment.
    # TELEGRAM_BOT_TOKEN переиспользует того же бота, что и CI/deploy notifications.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

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

    # Controlled admin AI selector. Defaults are intentionally conservative:
    # fake provider is available for zero-cost shadow checks, real calls require explicit env opt-in.
    ai_enabled: bool = False
    ai_shadow_mode: bool = True
    ai_apply_mode: bool = False
    ai_enabled_tasks: str = "explain_review_reason"
    ai_openai_model: str = "gpt-5-nano"
    openai_api_key: str = ""
    ai_provider_timeout_seconds: int = 12
    ai_monthly_budget_usd: float = 5.0
    ai_monthly_stop_usd: float = 4.5
    ai_daily_budget_usd: float = 0.25
    ai_max_job_cost_usd: float = 0.10
    ai_max_place_batch_size: int = 1
    ai_max_input_tokens_per_place: int = 1200
    ai_max_output_tokens_per_place: int = 300

    # Scheduled place re-verification enqueue — включается явно в окружении.
    verification_scheduler_enabled: bool = False
    verification_scheduler_interval_hours: int = 24
    verification_scheduler_city_slugs: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()