export const counterLabels: Record<string, string> = {
  found: 'Найдено',
  enriched: 'Обогащено',
  auto_published: 'Автопубликация',
  limited_published: 'Ограниченная публикация',
  review_required: 'Нужна проверка',
  rejected: 'Отклонено',
  failed: 'Ошибки',
}

export const statusLabel = (value: string) =>
  ({ success: 'успешно', partial_success: 'частично успешно', failed: 'ошибка' }[value] ?? value)

export const stepLabel = (value: string) => ({
  collect_places: 'Сбор мест',
  normalize_categories: 'Категории',
  backfill_addresses: 'Адреса',
  generate_ai_descriptions: 'Описания',
  fetch_photo_candidates: 'Фото',
  calculate_field_confidence: 'Доверие',
  apply_publication_decisions: 'Публикация',
}[value] ?? value)

export const fieldLabel = (value: string) =>
  ({ description: 'Описание', address: 'Адрес', photo: 'Фото', opening_hours: 'Часы работы', place: 'Место' }[value] ?? value)

export const reasonLabel = (value: string) =>
  ({ low_confidence: 'Низкое доверие', description_missing: 'Нет описания', non_tourist_category: 'Не туристическая категория' }[value] ?? value)
