const REASON_LABELS: Record<string, string> = {
  selected: 'Выбрано в маршрут.',
  score: 'Высокая оценка для маршрута.',
  close_to_start: 'Рядом со стартом маршрута.',
  category_match: 'Подходит под выбранные интересы.',
  city_not_published: 'Город не опубликован. Сначала опубликуйте город.',
  city_inactive: 'Город выключен. Включите город перед сборкой маршрутов.',
  missing_city_id: 'У места не указан город.',
  place_not_published: 'Место не опубликовано.',
  unpublished_place: 'Место не опубликовано.',
  place_not_visible_in_catalog: 'Место скрыто в каталоге.',
  hidden_place: 'Место скрыто в каталоге.',
  route_eligible_false: 'Место не подтверждено для маршрутов.',
  place_inactive: 'Место выключено.',
  inactive_place: 'Место выключено.',
  place_status_not_active: 'Статус места не активен.',
  lifecycle_not_active: 'Место не в активном жизненном цикле.',
  missing_coordinates: 'Нет координат.',
  no_coordinates: 'Нет координат.',
  invalid_coordinates: 'Координаты выглядят неверными.',
  missing_canonical_category: 'Не определена категория места.',
  spam_poi: 'Место похоже на служебную или мусорную точку.',
  duplicate_suspected: 'Место похоже на дубль.',
  critical_field_expired: 'Ключевые данные устарели, нужна проверка.',
  place_archived: 'Место в архиве.',
  no_photo: 'Нет фото.',
  no_address: 'Нет адреса.',
  no_description: 'Нет описания.',
  low_quality: 'Низкое качество карточки места.',
  route_failed_no_places: 'Не удалось собрать маршрут: нет подходящих точек.',
  route_incomplete: 'Маршрут не собран до конца.',
  route_short_due_to_time_budget: 'Маршрут короткий из-за малого бюджета времени.',
  route_short_due_to_low_place_density: 'Маршрут короткий: мало подходящих мест.',
  route_built_without_selected_interests: 'Маршрут собран без выбранных интересов.',
  long_initial_transfer: 'Старт далеко от первой точки маршрута.',
  budget_swallowed_by_transfer: 'Дорога до первой точки съела большую часть бюджета времени.',
  visit_time_clamped_to_fit_budget: 'Время визита сокращено, чтобы уложиться в бюджет.',
  start_coordinates_replaced_with_city_center: 'Стартовые координаты были некорректны, использован центр города.',
  some_places_have_no_address: 'У части точек нет адреса.',
  some_places_have_no_photo: 'У части точек нет фото.',
  some_places_have_weak_description: 'У части точек слабое описание.',
  route_has_long_walk_segments: 'Есть длинные пешие переходы.',
  category_diversity_limited: 'Ограничено разнообразие категорий.',
  interest_removed_due_to_avoidance: 'Часть интересов убрана, потому что она попала в исключения.',
}

const CATEGORY_LABELS: Record<string, string> = {
  attraction: 'достопримечательность',
  bar: 'бар',
  cafe: 'кафе',
  coffee: 'кофе',
  culture: 'культура',
  food: 'еда',
  gallery: 'галерея',
  historic: 'историческое место',
  history: 'история',
  landmark: 'ориентир',
  monument: 'памятник',
  museum: 'музей',
  outdoor: 'на улице',
  park: 'парк',
  promenade: 'прогулочная зона',
  restaurant: 'ресторан',
  service: 'сервис',
  sightseeing: 'осмотр города',
  viewpoint: 'смотровая точка',
  walk: 'прогулка',
}

const QUALITY_LABELS: Record<string, string> = {
  gold: 'отлично',
  silver: 'хорошо',
  bronze: 'можно проверить',
  draft: 'черновик',
  rejected: 'отклонено',
  unknown: 'неизвестно',
}

export const routeReasonText = (code: string | null | undefined) => {
  if (!code) return '—'
  if (code.startsWith('forbidden_category:')) {
    return `Категория не подходит для маршрутов: ${categoryText(code.split(':')[1])}.`
  }
  if (code.startsWith('quality_tier_not_route_allowed:')) {
    return `Низкий уровень качества места: ${qualityText(code.split(':')[1])}.`
  }
  return REASON_LABELS[code] ?? humanizeCode(code)
}

export const categoryText = (category: string | null | undefined) => {
  if (!category) return '—'
  return CATEGORY_LABELS[category] ?? humanizeCode(category)
}

export const qualityText = (quality: string | null | undefined) => {
  if (!quality) return '—'
  return QUALITY_LABELS[quality] ?? humanizeCode(quality)
}

export const humanizeCode = (code: string) => code.replace(/[_-]+/g, ' ')
