from __future__ import annotations

from pathlib import Path

import allure
import pytest

from services.local_persistent_cache import stable_cache_key
from tests.allure_support import given, scenario, then, when

pytestmark = [pytest.mark.unit, pytest.mark.regression]


@scenario(
    "Ключ локального кеша не зависит от порядка полей",
    epic="Платформа данных",
    feature="Локальный кеш",
    story="Стабильные ключи кеша",
)
def test_stable_cache_key_is_deterministic() -> None:
    with given("одинаковые параметры переданы в разном порядке"):
        left_payload = {"b": 2, "a": 1}
        right_payload = {"a": 1, "b": 2}

    with when("для параметров формируются ключи кеша"):
        left = stable_cache_key("namespace", left_payload)
        right = stable_cache_key("namespace", right_payload)

    with then("ключи совпадают и содержат namespace"):
        assert left == right
        assert left.startswith("namespace:")


@scenario(
    "Версия diskcache закреплена в backend-зависимостях",
    epic="Платформа данных",
    feature="Локальный кеш",
    story="Воспроизводимые зависимости",
)
def test_diskcache_dependency_is_pinned() -> None:
    with given("файл backend-зависимостей"):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

    with then("diskcache закреплён на согласованной версии"):
        assert "diskcache==5.6.3" in requirements


@scenario(
    "Docker Compose сохраняет локальный кеш между перезапусками",
    epic="Платформа данных",
    feature="Локальный кеш",
    story="Постоянное хранилище кеша",
)
def test_compose_mounts_local_cache_volume() -> None:
    with given("конфигурацию Docker Compose"):
        compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    with then("volume и путь локального кеша подключены к сервисам"):
        assert "local_cache:" in compose
        assert "LOCAL_CACHE_DIR: /app/.cache/city-go" in compose
        assert "- local_cache:/app/.cache/city-go" in compose


@scenario(
    "Обогащение адресов и фотографий использует локальный кеш",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Кеширование внешних источников",
)
def test_import_enrichment_uses_cache_layer() -> None:
    with given("реализацию геокодирования и загрузки изображений"):
        geocode = Path("services/place_address_geocode.py").read_text(encoding="utf-8")
        images = Path("data/scripts/enrich_place_images.py").read_text(encoding="utf-8")

    with then("оба контура читают и записывают ответы через кеш"):
        assert "get_cached_json" in geocode
        assert "set_cached_json" in geocode
        assert "provider:nominatim" in geocode
        assert "get_cached_text" in images
        assert "set_cached_text" in images
        assert "image_enrichment_http_text_v1" in images


@scenario(
    "Админское API публикует статистику локального кеша",
    epic="Операционный центр",
    feature="Админка",
    story="Наблюдаемость кеша",
)
def test_admin_local_cache_stats_endpoint_is_registered() -> None:
    with given("роутер операционных endpoint-ов"):
        admin_ops = Path("routers/admin_ops.py").read_text(encoding="utf-8")

    with then("endpoint статистики кеша зарегистрирован"):
        assert '@router.get("/cache/local")' in admin_ops
        assert "cache_stats" in admin_ops


@scenario(
    "Import-worker ограничивает нагрузку настройками окружения",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Управление нагрузкой import-worker",
    severity=allure.severity_level.CRITICAL,
)
def test_import_worker_uses_environment_throttling() -> None:
    with given("Docker Compose и реализацию постоянного import-worker"):
        compose = Path("docker-compose.yml").read_text(encoding="utf-8")
        worker = Path("data/scripts/run_admin_import_worker.py").read_text(encoding="utf-8")

    with when("проверяется команда запуска worker и её настройки"):
        resource_preflight_is_configured = "check_import_worker_resources.py" in compose
        worker_command_is_current = "run_admin_import_worker.py" in compose
        batch_limit_is_configured = "IMPORT_WORKER_BATCH_LIMIT: 1" in compose
        sleep_is_configured = "IMPORT_WORKER_SLEEP_SECONDS: 60" in compose

    with then("Docker Compose запускает resource preflight перед актуальным worker"):
        assert resource_preflight_is_configured
        assert worker_command_is_current

    with then("лимит очереди и пауза задаются через окружение"):
        assert batch_limit_is_configured
        assert sleep_is_configured
        assert 'os.getenv("IMPORT_WORKER_BATCH_LIMIT", "1")' in worker
        assert 'os.getenv("IMPORT_WORKER_SLEEP_SECONDS", "60")' in worker


@scenario(
    "Админские действия импорта используют очередь базы данных",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Надёжная очередь импортов",
)
def test_admin_import_actions_use_db_queue() -> None:
    with given("роутер, задачи и сервис import job"):
        router = Path("routers/admin_import_jobs.py").read_text(encoding="utf-8")
        tasks = Path("services/admin_city_import_tasks.py").read_text(encoding="utf-8")
        job_service = Path("services/admin_city_import_job_service.py").read_text(encoding="utf-8")

    with then("роутер ставит операции в очередь вместо BackgroundTasks"):
        assert "BackgroundTasks" not in router
        assert '@router.get("/import-jobs/queue")' in router
        assert "queue_city_import_job" in router
        assert "queue_city_enrichment_job" in router

    with then("очередь поддерживает сводку и отдельный enrichment-only источник"):
        assert "import_queue_summary" in tasks
        assert "SOURCE_ENRICHMENT_ONLY" in job_service
