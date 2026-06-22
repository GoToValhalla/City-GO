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

    # Local persistent cache for import/enrichment external calls. This is not distributed state.
    local_cache_enabled: bool = True
    local_cache_dir: str = "/app/.cache/city-go"
    local_cache_default_ttl_seconds: int = 2_592_000
    local_cache_size_limit_bytes: int = 1_073_741_824
    local_cache_shards: int = 8

    # Optional Geoapify key. Если ключ не задан, typed address не геокодится,
    # а маршрут строится от координат, которые пришли от клиента.
    geoapify_api_key: str = ""
    geocoding_timeout_seconds: int = 10

    # Nominatim User-Agent для backfill адресов. Без example.com и пустых значений.
    place_address_geocoder_user_agent: str = "CityGoAddressBackfill/1.0"

    # Telegram Bot — токен API бота (Long Poll / webhook).
    bot_token: str = ""

    # Telegram runtime alerts — чат, куда уходят ошибки import-worker/enrichment.
    # TELEGRAM_BOT_TOKEN переиспользует того же бота, что и CI/deploy notifications.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Backend URL for Telegram bot — базовый URL этого FastAPI для запросов из бота.
    backend_base_url: str = "http://127.0.0.1:8000"

    # Telegram Bot defaults — город по умолчанию в сценариях бота (slug).
    default_city_slug: str = "zelenogradsk"

    # Optional filters for coffee places — опциональные id категории/тега для сценария «кофе».
    coffee_category_id: int | None = None
    coffee_tag_id: int | None = None

    # Optional filters for food places — опциональные id для сценария «еда».
    food_category_id: int | None = None
    food_tag_id: int | None = None

    # Optional filters for walking places — опциональные id для сценария «прогулки».
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()