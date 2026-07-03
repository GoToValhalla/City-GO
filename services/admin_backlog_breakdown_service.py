"""Read-only decomposition of admin data backlog queues."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session

from models.place import Place
from services.admin_backlog_clauses import content_gap_clause, queue_clause, reason_clause

REQUIRED_QUEUES = ("route_blockers", "route_unknown", "route_excluded", "no_photo", "no_address", "no_description", "low_confidence", "auto_backlog", "manual_review", "needs_verification")
AUTO_FIXABLE_QUEUES = ("auto_backlog", "needs_verification", "no_photo", "no_address", "no_description", "low_confidence")
MANUAL_QUEUES = ("manual_review", "route_blockers", "route_unknown", "route_excluded")
CONTENT_GAP_QUEUES = ("no_photo", "no_address", "no_description")


@dataclass(frozen=True)
class ReasonSpec:
    code: str
    title: str
    auto_fixable: bool
    manual_required: bool


@dataclass(frozen=True)
class QueueSpec:
    code: str
    title: str
    recommended_action: str
    auto_fixable: bool
    manual_required: bool
    reasons: tuple[ReasonSpec, ...]


QUEUE_SPECS = (
    QueueSpec("route_blockers", "Проблемы маршрутов", "Сначала разберите причины блокировки.", False, True, (
        ReasonSpec("manual_disabled", "Отключены вручную", False, True),
        ReasonSpec("missing_coordinates", "Нет координат", False, True),
        ReasonSpec("unknown_category", "Неизвестная категория", False, True),
        ReasonSpec("service_category", "Сервисная категория", False, True),
        ReasonSpec("other_policy_blocker", "Другая причина блокировки", False, True),
    )),
    QueueSpec("route_unknown", "Неизвестные категории", "Назначить понятные категории.", False, True, (
        ReasonSpec("unknown_category", "Категория не распознана", False, True),
        ReasonSpec("empty_category", "Категория не заполнена", False, True),
        ReasonSpec("unmapped_category", "Категория не сопоставлена", False, True),
        ReasonSpec("placeholder_category", "Слишком общая категория", False, True),
    )),
    QueueSpec("route_excluded", "Сервисные точки", "Проверить, что сервисные POI скрыты из маршрутов.", False, True, (
        ReasonSpec("pharmacy_medical", "Аптеки и медицина", False, True),
        ReasonSpec("bank_atm", "Банки и банкоматы", False, True),
        ReasonSpec("transport_bus_stop", "Остановки и транспорт", False, True),
        ReasonSpec("parking_fuel", "Парковки и топливо", False, True),
        ReasonSpec("other_service", "Другие сервисные точки", False, True),
    )),
    QueueSpec("no_photo", "Без фото", "Запустить подбор фото или добавить вручную.", True, False, (
        ReasonSpec("published_without_any_photo", "Опубликовано без фото", True, False),
        ReasonSpec("route_ready_without_photo", "Маршрутные места без фото", True, False),
        ReasonSpec("catalog_without_photo", "Каталог без фото", True, False),
    )),
    QueueSpec("no_address", "Без адреса", "Запустить восстановление адресов.", True, False, (
        ReasonSpec("address_null", "Адрес отсутствует", True, False),
        ReasonSpec("address_empty", "Адрес пустой", True, False),
        ReasonSpec("address_placeholder", "Адрес-заглушка", True, False),
        ReasonSpec("coordinates_without_address", "Есть координаты, нет адреса", True, False),
    )),
    QueueSpec("no_description", "Без описания", "Сгенерировать или написать описания.", True, False, (
        ReasonSpec("description_null", "Описание отсутствует", True, False),
        ReasonSpec("description_empty", "Описание пустое", True, False),
        ReasonSpec("description_equals_title", "Описание повторяет название", True, False),
        ReasonSpec("description_too_short", "Описание слишком короткое", True, False),
        ReasonSpec("placeholder_description", "Описание-заглушка", True, False),
    )),
    QueueSpec("low_confidence", "Низкая уверенность", "Запустить автоматическую перепроверку данных.", True, False, (
        ReasonSpec("data_confidence_low", "Низкая уверенность в данных", True, False),
        ReasonSpec("confidence_unknown", "Уверенность не определена", True, False),
        ReasonSpec("category_confidence_low", "Слабая уверенность категории", True, False),
        ReasonSpec("mixed_low_confidence", "Несколько слабых сигналов", True, False),
    )),
    QueueSpec("auto_backlog", "Автоисправление", "Запустить автоматическую обработку.", True, False, (
        ReasonSpec("auto_draft", "Черновики для автообработки", True, False),
        ReasonSpec("auto_backlog_status", "Очередь автообработки", True, False),
        ReasonSpec("auto_low_confidence_status", "Автообработка низкой уверенности", True, False),
    )),
    QueueSpec("manual_review", "Очередь разбора", "Разобрать по причинам и отделить автоматическое.", False, True, (
        ReasonSpec("explicit_manual_review", "Явная ручная проверка", False, True),
        ReasonSpec("publication_review_backlog", "Очередь публикации", True, False),
        ReasonSpec("legacy_needs_review", "Старые элементы проверки", True, False),
        ReasonSpec("overlaps_with_auto_backlog", "Пересекается с автоочередью", True, False),
        ReasonSpec("overlaps_with_verification", "Пересекается с автопроверкой", True, False),
        ReasonSpec("overlaps_with_content_gaps", "Есть пробелы контента", True, False),
        ReasonSpec("overlaps_with_low_confidence", "Есть низкая уверенность", True, False),
    )),
    QueueSpec("needs_verification", "Автоперепроверка", "Запустить автоматическую проверку данных.", True, False, (
        ReasonSpec("needs_recheck", "Нужна повторная проверка", True, False),
        ReasonSpec("unverified", "Ещё не проверено", True, False),
        ReasonSpec("verification_overlaps_with_manual_review", "Пересекается с очередью разбора", True, False),
        ReasonSpec("verification_overlaps_with_low_confidence", "Есть низкая уверенность", True, False),
        ReasonSpec("verification_overlaps_with_content_gaps", "Есть пробелы контента", True, False),
        ReasonSpec("route_relevant_verification", "Важны для маршрутов", True, False),
    )),
)


def build_admin_backlog_breakdown(db: Session) -> dict[str, object]:
    queue_counts = {code: _count(db, queue_clause(code)) for code in REQUIRED_QUEUES}
    queues = [_queue_payload(db, spec, queue_counts[spec.code]) for spec in QUEUE_SPECS]
    overlaps = _overlaps(db)
    summary = {
        "unique_problem_places": _count(db, _any_queue_clause(REQUIRED_QUEUES)),
        "total_problem_signals": sum(queue_counts.values()),
        "route_blocker_places": queue_counts["route_blockers"],
        "auto_fixable_places": _count(db, _any_queue_clause(AUTO_FIXABLE_QUEUES)),
        "manual_places": queue_counts["manual_review"],
        "verification_backlog_places": queue_counts["needs_verification"],
        "content_gap_places": _count(db, content_gap_clause()),
    }
    return {"generated_at": datetime.utcnow(), "summary": summary, "queues": queues, "overlaps": overlaps}


def _queue_payload(db: Session, spec: QueueSpec, total: int) -> dict[str, object]:
    reasons = [_reason_payload(db, spec.code, reason) for reason in spec.reasons]
    return {
        "code": spec.code,
        "title": spec.title,
        "total_count": total,
        "unique_places_count": total,
        "total_problem_signals": sum(int(reason["count"]) for reason in reasons),
        "auto_fixable_count": sum(int(reason["count"]) for reason in reasons if reason["auto_fixable"]),
        "manual_count": sum(int(reason["count"]) for reason in reasons if reason["manual_required"]),
        "overlap_count": sum(int(reason["count"]) for reason in reasons if str(reason["code"]).startswith("overlaps_with_")),
        "recommended_action": spec.recommended_action,
        "severity": _severity(total),
        "sample_endpoint": f"/admin/places/search?preset={spec.code}",
        "reasons": reasons,
    }


def _reason_payload(db: Session, queue_code: str, spec: ReasonSpec) -> dict[str, object]:
    reason = reason_clause(_normalized_reason(queue_code, spec.code))
    queue = queue_clause(queue_code)
    count = _count(db, queue & reason if queue is not None and reason is not None else None)
    return {
        "code": spec.code,
        "title": spec.title,
        "count": count,
        "auto_fixable": spec.auto_fixable,
        "manual_required": spec.manual_required,
        "sample_endpoint": f"/admin/places/search?preset={queue_code}&reason={_normalized_reason(queue_code, spec.code)}",
    }


def _normalized_reason(queue_code: str, reason_code: str) -> str:
    return reason_code


def _overlaps(db: Session) -> list[dict[str, object]]:
    pairs = (
        ("manual_review", "needs_verification"),
        ("manual_review", "auto_backlog"),
        ("manual_review", "low_confidence"),
        ("manual_review", "no_description"),
        ("needs_verification", "low_confidence"),
        ("needs_verification", "no_description"),
        ("route_blockers", "route_unknown"),
    )
    return [{"left": left, "right": right, "count": _count(db, queue_clause(left) & queue_clause(right))} for left, right in pairs]


def _any_queue_clause(codes: tuple[str, ...]):
    return or_(*tuple(queue_clause(code) for code in codes))


def _count(db: Session, clause) -> int:
    if clause is None:
        return 0
    return int(db.query(func.count(distinct(Place.id))).filter(clause).scalar() or 0)


def _severity(count: int) -> str:
    if count >= 1000:
        return "warning"
    if count:
        return "info"
    return "ok"
