export type PlacePreset = { id: string; label: string }

export const PLACE_PRESETS: PlacePreset[] = [
  { id: '', label: 'Все места' },
  { id: 'problematic', label: 'Есть проблемы с данными' },
  { id: 'no_photo', label: 'Без фото' },
  { id: 'no_address', label: 'Без адреса' },
  { id: 'no_description', label: 'Без описания' },
  { id: 'no_contacts', label: 'Без телефона и сайта' },
  { id: 'no_hours', label: 'Без часов работы' },
  { id: 'needs_review', label: 'Требуют проверки' },
  { id: 'low_confidence', label: 'Низкая уверенность' },
  { id: 'suspicious_names', label: 'Подозрительные названия' },
  { id: 'generic_osm_placeholders', label: 'OSM-заглушки' },
  { id: 'junk_categories', label: 'Неразобранные категории' },
  { id: 'service_places', label: 'Городская инфраструктура' },
  { id: 'in_routes', label: 'Участвуют в маршрутах' },
  { id: 'not_in_routes', label: 'Исключены из маршрутов' },
  { id: 'route_unknown', label: 'Маршруты: нужно пересчитать' },
  { id: 'published_not_route_eligible', label: 'Опубликовано, но не в маршрутах' },
  { id: 'route_eligible_no_photo', label: 'Маршрутные без фото' },
  { id: 'route_eligible_no_address', label: 'Маршрутные без адреса' },
]

export const PUB_STATUS_OPTIONS = [
  { value: '', label: 'Любой статус' },
  { value: 'published', label: 'Опубликовано' },
  { value: 'draft', label: 'Черновик' },
  { value: 'hidden', label: 'Скрыто' },
  { value: 'unpublished', label: 'Снято с публикации' },
  { value: 'needs_review', label: 'На проверке' },
  { value: 'rejected', label: 'Отклонено' },
]

export const VERIFY_STATUS_OPTIONS = [
  { value: '', label: 'Любая проверка' },
  { value: 'verified', label: 'Подтверждено' },
  { value: 'unverified', label: 'Не проверено' },
  { value: 'needs_recheck', label: 'Нужна перепроверка' },
  { value: 'rejected', label: 'Отклонено' },
  { value: 'not_found', label: 'Не найдено' },
  { value: 'closed', label: 'Закрыто' },
]
