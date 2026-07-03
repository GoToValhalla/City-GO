import type { RecommendationRouteRequest, RouteBuilderSlot, RouteBuildMode, RouteStartType } from '../../../api/recommendations/recommendationRoute.types'

export type RecommendationRouteFormState = {
  lat: string
  lng: string
  startAddress: string
  startSource: string
  timeBudgetMinutes: string
  timeOfDay: string
  routeTimeMode: string
  useTimeBudget: boolean
  buildMode: RouteBuildMode
  interests: string[]
  avoidedCategories: string[]
  budgetLevel: string
  paceMode: string
  isVisiting: boolean
  userId: string
  routeSlots: RouteBuilderSlot[]
}

type BuildResult =
  | { ok: true; value: RecommendationRouteRequest }
  | { ok: false; error: string }

const parseNumber = (value: string): number | null => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export const toggleListValue = (values: string[], value: string): string[] => {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

export const normalizeRouteInterests = (interests: string[]): string[] => {
  return interests.map((interest) => interest.trim()).filter(Boolean)
}

export const buildRecommendationRouteRequest = (form: RecommendationRouteFormState, citySlug: string): BuildResult => {
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

  const routeSlots = normalizeRouteSlots(form.routeSlots)
  const interests = normalizeRouteInterests(form.interests)
  const buildMode = routeSlots.length ? 'constructor' : interests.length ? 'by_categories' : form.buildMode === 'constructor' ? 'constructor' : 'auto'
  if (buildMode === 'constructor' && routeSlots.length === 0) {
    return { ok: false, error: 'Добавь хотя бы один слот сценария' }
  }

  return {
    ok: true,
    value: {
      lat: lat ?? 0,
      lng: lng ?? 0,
      start_address: startAddress || null,
      start_source: startType,
      start: { type: startType, lat, lng, address: startAddress || null },
      build_mode: buildMode,
      time_budget_minutes: budget,
      time_of_day: form.timeOfDay || null,
      route_time_mode: form.routeTimeMode || 'flexible',
      interests,
      avoided_categories: form.avoidedCategories,
      excluded_place_ids: [],
      budget_level: form.budgetLevel ? Number(form.budgetLevel) : null,
      pace_mode: form.paceMode || null,
      is_visiting: form.isVisiting,
      city_id: citySlug,
      visit_city_id: null,
      visit_days: form.isVisiting ? 1 : null,
      user_id: form.userId.trim() || null,
      selected_place_ids: routeSlots.flatMap((slot) => (slot.selected_place_id ? [slot.selected_place_id] : [])),
      route_slots: routeSlots,
    } as RecommendationRouteRequest,
  }
}

export const normalizeRouteSlots = (slots: RouteBuilderSlot[]): RouteBuilderSlot[] => slots.flatMap((slot, index) => {
  const category = String(slot.category || slot.type || '').trim()
  if (!category) return []
  return [{
    slot_id: slot.slot_id || `slot-${index + 1}`,
    type: category,
    category,
    min_count: slot.required === false ? 0 : 1,
    max_count: 1,
    required: slot.required !== false,
    duration: slot.duration ?? null,
    selected_place_id: slot.selected_place_id ?? null,
  }]
})

const normalizeStartType = (value: string): RouteStartType => {
  if (value === 'current_location' || value === 'map_point' || value === 'address' || value === 'place') return value
  return 'city_center'
}
