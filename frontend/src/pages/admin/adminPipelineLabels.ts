export const counterLabels: Record<string, string> = {
  found: 'Найдено',
  enriched: 'Обогащено',
  fields_enriched: 'Заполнено полей',
  source_observations: 'Ответы источников',
  source_conflicts: 'Конфликты',
  provider_errors: 'Ошибки источников',
  auto_published: 'Автопубликация',
  limited_published: 'Ограниченная публикация',
  review_required: 'Нужна проверка',
  rejected: 'Отклонено',
  failed: 'Ошибки',
}

export const statusLabel = (value: string) =>
  ({ queued: 'в очереди', running: 'выполняется', success: 'успешно', partial_success: 'частично успешно', failed: 'ошибка' }[value] ?? value)

export const stepLabel = (value: string) => ({
  collect_places: 'Сбор мест',
  normalize_categories: 'Категории',
  backfill_addresses: 'Адреса',
  enrich_external_sources: 'Внешние источники',
  generate_ai_descriptions: 'Описания',
  fetch_photo_candidates: 'Фото',
  calculate_field_confidence: 'Доверие',
  apply_publication_decisions: 'Публикация',
}[value] ?? value)

export const fieldLabel = (value: string) =>
  ({ description: 'Описание', address: 'Адрес', website: 'Сайт', phone: 'Телефон', photo: 'Фото', opening_hours: 'Часы работы', place: 'Место' }[value] ?? value)

export const reasonLabel = (value: string) =>
  ({ low_confidence: 'Низкое доверие', description_missing: 'Нет описания', missing_after_enrichment: 'Не найдено после обогащения', source_conflict: 'Источники расходятся', non_tourist_category: 'Не туристическая категория' }[value] ?? value)
