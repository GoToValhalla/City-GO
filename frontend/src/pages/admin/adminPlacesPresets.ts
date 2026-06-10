export type PlacePreset = { id: string; label: string }

export const PLACE_PRESETS: PlacePreset[] = [
  { id: '', label: 'Все места' },
  { id: 'problematic', label: 'Проблемные места' },
  { id: 'no_photo', label: 'Без фото' },
  { id: 'no_address', label: 'Без адреса' },
  { id: 'no_description', label: 'Без описания' },
  { id: 'needs_review', label: 'Требуют проверки' },
  { id: 'low_confidence', label: 'Низкая уверенность' },
  { id: 'suspicious_names', label: 'Подозрительные названия' },
  { id: 'junk_categories', label: 'Мусорные категории' },
  { id: 'service_places', label: 'Служебные места' },
  { id: 'in_routes', label: 'В маршрутах' },
  { id: 'not_in_routes', label: 'Не в маршрутах' },
]

export const PUB_STATUS_OPTIONS = [
  { value: '', label: 'Любой статус' },
  { value: 'published', label: 'Опубликовано' },
  { value: 'draft', label: 'Черновик' },
  { value: 'hidden', label: 'Скрыто' },
  { value: 'unpublished', label: 'Снято с публикации' },
  { value: 'needs_review', label: 'На проверке' },
]

export const VERIFY_STATUS_OPTIONS = [
  { value: '', label: 'Любая верификация' },
  { value: 'verified', label: 'Верифицировано' },
  { value: 'unverified', label: 'Не проверено' },
  { value: 'needs_recheck', label: 'Нужна перепроверка' },
]

export const CATEGORY_OPTIONS = [
  '', 'coffee', 'food', 'walk', 'museum', 'attraction', 'beach', 'park', 'bar', 'hotel', 'service',
]

export const CATEGORY_OPTIONS_RU = [
  { value: 'attraction', label: 'Достопримечательность' },
  { value: 'museum', label: 'Музей' },
  { value: 'park', label: 'Парк' },
  { value: 'walk', label: 'Прогулка' },
  { value: 'coffee', label: 'Кофейня' },
  { value: 'food', label: 'Еда' },
  { value: 'bar', label: 'Бар' },
  { value: 'beach', label: 'Пляж' },
  { value: 'hotel', label: 'Проживание' },
  { value: 'service', label: 'Сервис' },
]
