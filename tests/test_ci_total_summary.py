import json

import allure
import pytest

from scripts.ci_total_summary import TotalReport, enrich_with_allure, parse_junit, render_report
from tests.allure_support import given, scenario, then, when

pytestmark = [pytest.mark.unit, pytest.mark.regression]


@scenario(
    "Итоговый CI-отчёт считает все тесты и группирует их по типу и функционалу",
    epic="Платформа",
    feature="Инфраструктура и CI",
    story="Единый отчёт полного прогона",
    severity=allure.severity_level.CRITICAL,
)
def test_total_report_groups_backend_and_frontend_tests(tmp_path, monkeypatch) -> None:
    with given("backend и frontend JUnit содержат успешные тесты разных групп"):
        backend = tmp_path / "backend.xml"
        backend.write_text(
            """<testsuite>
<testcase classname="tests.test_routes" name="test_route_build" time="1">
  <properties>
    <property name="display_title" value="Маршрут строится из подходящих мест" />
    <property name="test_type" value="API" />
    <property name="functional_group" value="Построение и прохождение маршрута" />
  </properties>
</testcase>
</testsuite>""",
            encoding="utf-8",
        )
        frontend = tmp_path / "frontend.xml"
        frontend.write_text(
            """<testsuite>
<testcase classname="src/pages/places/PlacesPage.test.tsx" name="показывает карточки мест" time="2" />
</testsuite>""",
            encoding="utf-8",
        )
        monkeypatch.setenv("GITHUB_RUN_NUMBER", "1027")
        monkeypatch.setenv("GITHUB_SHA", "1234567890")

    with when("генератор собирает единый отчёт"):
        cases = parse_junit(backend, "backend") + parse_junit(frontend, "frontend")
        message = render_report(TotalReport(cases=cases, stages={"Backend tests": "success", "Frontend tests": "success"}))
        allure.attach(message, "Единый отчёт", allure.attachment_type.TEXT)

    with then("в отчёте отображается общий total"):
        assert "Всего: 2 · пройдено: 2 · упало: 0" in message

    with then("в отчёте есть разрез по API, UI и функциональным областям"):
        assert "API: 1/1" in message
        assert "UI: 1/1" in message
        assert "Построение и прохождение маршрута: 1/1" in message
        assert "Каталог мест: 1/1" in message


@scenario(
    "Итоговый CI-отчёт показывает русское название теста и точный упавший шаг",
    epic="Платформа",
    feature="Инфраструктура и CI",
    story="Диагностика падения",
    severity=allure.severity_level.CRITICAL,
)
def test_total_report_uses_deepest_failed_allure_step(tmp_path) -> None:
    with given("JUnit содержит падение, а Allure содержит вложенный упавший шаг"):
        junit = tmp_path / "backend.xml"
        junit.write_text(
            """<testsuite>
<testcase classname="tests.test_import_pipeline" name="test_import_keeps_category" time="0.5">
  <properties>
    <property name="test_type" value="Integration" />
    <property name="functional_group" value="Импорт и обогащение" />
  </properties>
  <failure message="AssertionError: category mismatch">tests/test_import_pipeline.py:42: AssertionError</failure>
</testcase>
</testsuite>""",
            encoding="utf-8",
        )
        allure_dir = tmp_path / "allure"
        allure_dir.mkdir()
        (allure_dir / "case-result.json").write_text(json.dumps({
            "name": "Импорт сохраняет нормализованную категорию",
            "fullName": "tests.test_import_pipeline#test_import_keeps_category",
            "status": "failed",
            "labels": [
                {"name": "node_id", "value": "tests/test_import_pipeline.py::test_import_keeps_category"},
                {"name": "feature", "value": "Импорт и обогащение"},
            ],
            "steps": [{
                "name": "Выполнение проверки",
                "status": "failed",
                "steps": [{"name": "Тогда: категория соответствует taxonomy", "status": "failed"}],
            }],
        }, ensure_ascii=False), encoding="utf-8")

    with when("JUnit дополняется данными Allure"):
        cases = parse_junit(junit, "backend")
        enrich_with_allure(cases, allure_dir)
        message = render_report(TotalReport(cases=cases, stages={"Backend tests": "failure"}))
        allure.attach(message, "Отчёт о падении", allure.attachment_type.TEXT)

    with then("отчёт использует понятное название сценария"):
        assert "Импорт сохраняет нормализованную категорию" in message

    with then("отчёт указывает самый глубокий упавший шаг и файл"):
        assert "Шаг: Выполнение проверки → Тогда: категория соответствует taxonomy" in message
        assert "Файл: tests/test_import_pipeline.py:42" in message


@scenario(
    "Итоговый CI-отчёт различает падение теста и падение технического этапа",
    epic="Платформа",
    feature="Инфраструктура и CI",
    story="Диагностика этапов workflow",
    severity=allure.severity_level.NORMAL,
)
def test_total_report_shows_failed_stage_without_fake_test_failure() -> None:
    with given("все тесты успешны, но frontend build завершился ошибкой"):
        report = TotalReport(cases=[], stages={"Backend tests": "success", "Frontend build": "failure"})

    with when("формируется итоговое уведомление"):
        message = render_report(report)

    with then("этап отмечается отдельно от падений тестов"):
        assert "❌ Frontend build" in message
        assert "ошибка произошла вне выполнения теста" in message
