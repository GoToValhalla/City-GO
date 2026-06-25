# Тестирование и Allure

Дата актуализации: 2026-06-25.

## Цель отчёта

Allure используется как рабочий отчёт по продуктовым функциям. Технический `nodeid` нужен для поиска теста в коде, но не является названием сценария.

Иерархия отчёта:

```text
Epic: крупный продуктовый контур
  Feature: функция продукта
    Story: пользовательский или операционный сценарий
      Test: понятное название на русском языке
        Step: Дано / Когда / Тогда
```

Верхнеуровневые Epic:

- Платформа данных;
- Маршруты;
- Каталог мест;
- Операционный центр;
- Территории;
- Каналы;
- Пользователи;
- Платформа.

## Обязательный формат функционального теста

Интеграционные, API, critical, smoke и сквозные regression-тесты оформляются через `tests.allure_support`:

```python
import allure
import pytest

from tests.allure_support import attach_json, given, scenario, then, when

pytestmark = [pytest.mark.integration, pytest.mark.regression]


@scenario(
    "Автоматическое описание сохраняется как проверяемый черновик",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Генерация описания с контролем происхождения",
    severity=allure.severity_level.CRITICAL,
)
def test_generated_description_is_reviewable(...):
    with given("создано доверенное место без описания"):
        ...

    with when("pipeline формирует описание"):
        result = ...
        attach_json("Результат pipeline", result)

    with then("черновик имеет низкую уверенность"):
        assert ...
```

Требования:

- название теста и шагов пишется на русском;
- один шаг содержит одно логическое действие или группу связанных проверок;
- assertion находится в том `then`, к которому относится;
- входные параметры и сложный результат прикладываются JSON-вложением;
- токены, пароли и персональные данные во вложения не попадают;
- `_new` не используется в новых именах файлов и тестов;
- маркер `allure_scenario` добавляется декоратором автоматически.

## Автоматические шаги

Для всех backend-тестов `conftest.py` создаёт шаги жизненного цикла:

1. `Подготовка тестового окружения`;
2. `Выполнение проверки`;
3. `Очистка тестового окружения`.

Если fixture падает до тела теста, Allure показывает падение на подготовке. Ошибка assertion или вызова сервиса отображается внутри выполнения проверки. Ошибка rollback/cleanup отображается в очистке.

Функциональные тесты должны дополнительно содержать вложенные `Дано / Когда / Тогда`. Автоматические lifecycle-шаги не заменяют продуктовые шаги.

## Unit-тесты

Короткий unit-тест одной функции не требуется искусственно разбивать на `Дано / Когда / Тогда`. Для него общий hook формирует:

- продуктовый Epic и Feature по расположению файла;
- русифицированный fallback title;
- severity;
- lifecycle steps;
- attachment с фазой и traceback при падении.

Если unit-тест проверяет несколько веток или сложный state transition, он переводится в явный `@scenario`.

## Backend запуск

```bash
python -m pytest -q --no-cov \
  --junitxml=artifacts/junit/backend.xml \
  --alluredir=artifacts/allure-results/backend
```

CI всегда генерирует HTML:

```text
backend-test-artifacts/allure-report/backend/index.html
```

В отчёт добавляются environment, commit, branch, executor URL, severity, markers, test file, node id и фаза падения.

## Frontend

```bash
cd frontend
npm run lint
npm run test:ci
npm run build
```

Vitest создаёт JUnit `artifacts/junit/frontend.xml`. Telegram summary показывает название теста, модуль, файл и строку, exception, вероятную причину и действие.

## Markers

```text
admin, api, auth, taxonomy, cities, places, import_pipeline, enrichment, routing,
unit, integration, slow, critical, smoke, regression, allure_scenario
```

## Уведомления

Backend и frontend отправляются отдельными Telegram-сообщениями. Полный traceback и вложения остаются в Allure/JUnit artifacts, чтобы сообщения не обрезались лимитом Telegram.
