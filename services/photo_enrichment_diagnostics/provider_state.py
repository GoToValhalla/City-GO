"""Provider status resolution for photo enrichment diagnostics."""

from __future__ import annotations


def provider_state(
    run: dict[str, object],
    *,
    without_photo: int,
    eligible: int,
    created: int,
    scanned: int,
    step_status: str | None,
    dependency_step: str | None,
) -> tuple[str, str | None, str | None, str | None]:
    if step_status == "skipped":
        return "step_skipped_due_to_dependency_failure", "dependency_failed", f"Шаг пропущен: зависимость {dependency_step or 'collecting_places'} не выполнена.", None
    if step_status == "blocked":
        return "blocked", "prerequisites_not_met", "Добор фото не запущен: не выполнены предварительные условия (нет мест в городе).", None
    if not run and without_photo > 0:
        return "no_photo_enrichment_run", "photo_enrichment_not_run", "Добор фото ещё не запускался для текущего состояния города.", None
    if eligible <= 0 and without_photo > 0:
        return "no_eligible_places", "no_eligible_places", "Места без image_url не проходят фильтр активного пула добора фото.", None
    provider_error = _first_provider_error(run.get("errors") if isinstance(run.get("errors"), list) else [])
    if provider_error:
        return provider_error["status"], provider_error["zero_reason"], provider_error["warning"], provider_error["message"]
    raw_status = str(run.get("provider_status") or "")
    if created > 0:
        return "success", None, None, None
    if scanned > 0 and created == 0 and int(run.get("candidates_found") or 0) == 0:
        pre_provider_filtered = (
            int(run.get("skipped_ineligible") or 0)
            + int(run.get("skipped_has_approved") or 0)
            + int(run.get("skipped_duplicates") or 0)
        )
        if pre_provider_filtered >= scanned:
            return "all_places_filtered_out", "all_places_filtered_out", "Все просмотренные места отфильтрованы до вызова источников.", None
        if raw_status == "source_evidence_exhausted":
            return "no_candidates_from_provider", "no_candidates_from_provider", "Источники OSM/Wikimedia/Openverse не вернули кандидатов.", None
        return "no_candidates_from_provider", "no_candidates_from_provider", "Провайдеры не вернули кандидатов для просмотренных мест.", None
    if without_photo <= 0:
        return "success", None, None, None
    return "no_candidates_from_provider", "no_candidates_from_provider", "Кандидаты на проверку не созданы.", None


def admin_hint(status: str, without_photo: int, created: int, pending_existing: int, zero_reason: str | None) -> str | None:
    hints = {
        "no_photo_enrichment_run": "Фото-блокер: запустите «Добрать фото» или полный импорт с шагом finding_images.",
        "no_candidates_from_provider": "Фото-блокер: источники не нашли кандидатов. Проверьте OSM tags, Wikimedia/Openverse и лимит сканирования.",
        "all_places_filtered_out": "Фото-блокер: места отфильтрованы (категория, неактивные, дубликаты, лимит).",
        "no_eligible_places": "Фото-блокер: нет мест в активном пуле добора (нужен status=active и отсутствие публичного фото).",
        "step_skipped_due_to_dependency_failure": "Фото-блокер: шаг finding_images пропущен из-за ошибки предыдущего шага.",
        "provider_auth_error": "Фото-блокер: ошибка авторизации внешнего источника фото.",
        "provider_quota_error": "Фото-блокер: квота/rate limit внешнего источника фото.",
        "provider_request_error": "Фото-блокер: ошибка запроса к внешнему источнику фото.",
    }
    if status == "step_skipped_due_to_dependency_failure":
        return hints[status]
    if without_photo <= 0 or created > 0 or pending_existing > 0:
        return None
    return hints.get(status) or hints.get(str(zero_reason or "")) or "Фото-блокер: много мест без фото, кандидатов на проверку нет — см. photo_diagnostics."


def _first_provider_error(errors: list[object]) -> dict[str, str] | None:
    for item in errors:
        if not isinstance(item, dict):
            continue
        message = str(item.get("error") or "")
        lowered = message.lower()
        if "401" in lowered or "403" in lowered or "auth" in lowered:
            return {"status": "provider_auth_error", "zero_reason": "provider_auth_error", "warning": "Ошибка авторизации внешнего источника.", "message": message[:500]}
        if "429" in lowered or "quota" in lowered or "rate limit" in lowered:
            return {"status": "provider_quota_error", "zero_reason": "provider_quota_error", "warning": "Исчерпана квота или rate limit внешнего источника.", "message": message[:500]}
        if message:
            return {"status": "provider_request_error", "zero_reason": "provider_request_error", "warning": "Ошибка запроса к внешнему источнику фото.", "message": message[:500]}
    return None
