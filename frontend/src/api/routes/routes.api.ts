import { buildApiUrl } from '../../shared/api/http'

// Точка маршрута, которую backend возвращает внутри detail-ответа.
export type RoutePoint = {
  place_id: number
  position: number
  place_slug?: string | null
  place_title?: string | null
}

// Базовая схема маршрута для списка и detail.
export type Route = {
  id: number
  city_id: number
  slug: string
  title: string
  short_description?: string | null
  duration_minutes?: number | null
  distance_km?: number | null
  route_mode?: string | null
  is_active: boolean
}

// Расширенная схема маршрута с точками.
export type RouteDetail = Route & {
  points: RoutePoint[]
}

// Загружает один маршрут по slug с backend.
export const getRouteBySlug = async (slug: string): Promise<RouteDetail> => {
  // Формируем URL detail-эндпоинта маршрута.
  const response = await fetch(buildApiUrl(`/routes/by-slug/${slug}`))

  // Если backend вернул ошибку — пробрасываем её выше.
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  // Преобразуем JSON-ответ в типизированный объект маршрута.
  const data: RouteDetail = await response.json()
  return data
}

// Загружает список маршрутов по city_slug.
export const getRoutesByCity = async (citySlug: string): Promise<Route[]> => {
  // Формируем URL списка маршрутов по городу.
  const response = await fetch(
    buildApiUrl(`/routes/?city_slug=${encodeURIComponent(citySlug)}`),
  )

  // Если backend вернул ошибку — пробрасываем её выше.
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  // Преобразуем JSON-ответ в массив маршрутов.
  const data: Route[] = await response.json()
  return data
}