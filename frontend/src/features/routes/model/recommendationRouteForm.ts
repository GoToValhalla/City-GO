import type { RecommendationRouteRequest, RouteStartType } from '../../../api/recommendations/recommendationRoute.types'

export type RecommendationRouteFormState = {
  lat: string
  lng: string
  startAddress: string
  startSource: string
  timeBudgetMinutes: string
  timeOfDay: string
  routeTimeMode: string
  useTimeBudget: boolean
  interests: string[]
  avoidedCategories: string[]
  budgetLevel: string
  paceMode: string
  isVisiting: boolean
  userId: string
}

type BuildResult =
  | { ok: true; value: RecommendationRouteRequest }
  | { ok: false; error: string }

// Интересы в UI — это мягкая настройка, а не обязательное условие построения маршрута.
// Если пользователь ничего не выбрал, строим обычную прогулку вместо пустого/непонятного запроса.
export const DEFAULT_ROUTE_INTERESTS = ['walk']

const parseNumber = (value: string): number | null => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export const toggleListValue = (values: string[], value: string): string[] => {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

export const normalizeRouteInterests = (interests: string[]): string[] => {
  const cleaned = interests.map((interest) => interest.trim()).filter(Boolean)
  return cleaned.length ? cleaned : DEFAULT_ROUTE_INTERESTS
}

export const buildRecommendationRouteRequest = (
  form: RecommendationRouteFormState,
  citySlug: string,
): BuildResult => {
  const lat = parseNumber(form.lat)
  const lng = parseNumber(form.lng)
  const startAddress = form.startAddress.trim()
  const startType = normalizeStartType(form.startSource)

  if ((startType === 'current_location' || startType === 'map_point' || startType === 'city_center') && (lat === null || lng === null)) {
    return { ok: false, error: 'Не удалось определить стартовую точку маршрута' }
  }

  if (startType === 'address' && !startAddress) {
    return { ok: false, error: 'Укажи адрес старта' }
  }

  const budget = form.useTimeBudget ? parseNumber(form.timeBudgetMinutes) : null
  if (form.useTimeBudget && (budget === null || budget < 15 || budget > 1440)) {
    return { ok: false, error: 'Укажи время от 15 до 1440 минут' }
  }

  return {
    ok: true,
    value: {
      lat: lat ?? 0,
      lng: lng ?? 0,
      start_address: startAddress || null,
      start_source: startType,
      start: {
        type: startType,
        lat,
        lng,
        address: startAddress || null,
      },
      build_mode: 'by_categories',
      time_budget_minutes: budget,
      time_of_day: form.timeOfDay || null,
      route_time_mode: form.routeTimeMode || 'flexible',
      interests: normalizeRouteInterests(form.interests),
      avoided_categories: form.avoidedCategories,
      excluded_place_ids: [],
      budget_level: form.budgetLevel ? Number(form.budgetLevel) : null,
      pace_mode: form.paceMode || null,
      is_visiting: form.isVisiting,
      city_id: citySlug,
      visit_city_id: null,
      visit_days: form.isVisiting ? 1 : null,
      user_id: form.userId.trim() || null,
    } as RecommendationRouteRequest,
  }
}

const normalizeStartType = (value: string): RouteStartType => {
  if (value === 'current_location' || value === 'map_point' || value === 'address' || value === 'place') {
    return value
  }
  return 'city_center'
}
