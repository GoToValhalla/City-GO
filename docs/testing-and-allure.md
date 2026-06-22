# Testing And Allure

Дата актуализации: 2026-06-22.

## Backend

Локальный запуск focused backend tests:

```bash
.venv/bin/python -m pytest --no-cov tests/test_admin_taxonomy_api_new.py tests/test_admin_city_workspace_api_new.py -q --alluredir=artifacts/allure-results/local
```

CI запускает backend regression с JUnit и raw Allure results:

```bash
python -m pytest -q --no-cov --junitxml=artifacts/junit/backend.xml --alluredir=artifacts/allure-results/backend
```

Если в runner доступен Allure CLI, workflow дополнительно генерирует HTML report в:

```text
artifacts/allure-report/backend
```

Если CLI недоступен, CI не падает: raw `allure-results` остаются артефактом для внешней генерации отчёта.

## Markers

Основные маркеры:

```text
admin, api, auth, taxonomy, cities, places, import_pipeline, enrichment, routing,
unit, integration, slow, critical, smoke, regression
```

Новые admin tests должны помечаться минимум доменным маркером и уровнем проверки, например:

```python
pytestmark = [pytest.mark.admin, pytest.mark.taxonomy, pytest.mark.api]
```

## Frontend

Основные проверки:

```bash
npm run lint
npm run test:ci
npm run build
```

`test:ci` пишет JUnit в `artifacts/junit/frontend.xml`, после чего `scripts/ci_test_summary.py` формирует короткий текстовый summary для GitHub artifacts и Telegram.

## Notifications

CI и deploy используют optional Telegram notification через secrets:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Если secrets отсутствуют или Telegram недоступен, notification step не должен блокировать deploy. В сообщениях указываются job status, commit SHA и ссылка на GitHub Actions run; значения secrets не логируются.
