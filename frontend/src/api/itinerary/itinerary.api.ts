// Контракт стартового контекста для запроса генерации маршрута.
// Нужен, чтобы frontend мог передать backend точку старта маршрута.
export type StartContextInput = {
  // Тип источника стартовой точки.
  source_type:
    | 'current_location'
    | 'typed_address'
    | 'selected_map_point'
    | 'place_id'
    | 'stay_location'
    | 'arrival_point'
    | 'saved_base'
    | 'area_anchor'
    | 'city_fallback'

  // Идентификатор place, если стартуем от точки из базы.
  place_id?: number | null

  // Координаты старта.
  lat?: number | null
  lng?: number | null

  // Текстовый адрес.
  address?: string | null

  // Район/зона старта.
  area?: string | null
}

// Точка маршрута в ответе backend.
export type ItineraryPoint = {
  // Идентификатор места.
  place_id: number

  // Порядок точки в маршруте.
  position: number

  // Slug места для перехода на detail.
  place_slug?: string | null

  // Название точки.
  place_title?: string | null

  // Краткое объяснение, почему точка попала в маршрут.
  reason?: string | null
}

// Нормализованный стартовый контекст в ответе.
export type StartContextRead = {
  // Итоговый тип стартовой точки.
  source_type:
    | 'current_location'
    | 'typed_address'
    | 'selected_map_point'
    | 'place_id'
    | 'stay_location'
    | 'arrival_point'
    | 'saved_base'
    | 'area_anchor'
    | 'city_fallback'

  // Координаты старта.
  lat?: number | null
  lng?: number | null

  // Человекочитаемая подпись старта.
  label?: string | null

  // Place ID, если старт идёт от точки в нашей БД.
  place_id?: number | null
}

// Запрос на генерацию маршрута.
export type ItineraryGenerateRequest = {
  // Город, в котором строим маршрут.
  city_slug: string

  // Необязательный user_id для персонализации.
  user_id?: number | null

  // Свободный текст пользователя.
  query?: string | null

  // Режим времени маршрута.
  time_mode?: 'explicit_budget' | 'open_duration'

  // Явный бюджет времени в минутах.
  time_budget_minutes?: number | null

  // Предпочтительный режим передвижения.
  route_mode?: 'walk' | 'public_transport' | 'mixed' | null

  // Количество дней.
  trip_days?: number | null

  // Контекст пользователя.
  with_dog?: boolean | null
  with_children?: boolean | null
  indoor_only?: boolean | null
  outdoor_only?: boolean | null

  // Бюджетный уровень.
  budget_level?: number | null

  // Нужно ли вернуть маршрут обратно к старту.
  return_to_start?: boolean

  // Максимальное количество точек.
  max_places?: number | null

  // Стартовая точка маршрута.
  start_context?: StartContextInput | null
}

// Ответ backend на генерацию маршрута.
export type ItineraryGenerateResponse = {
  // Технический статус ответа.
  status: string

  // Название маршрута.
  title: string

  // Краткое summary.
  summary: string

  // Режим работы со временем.
  time_mode: 'explicit_budget' | 'open_duration'

  // Запрошенная длительность.
  requested_duration_minutes?: number | null

  // Расчетная длительность.
  estimated_duration_minutes?: number | null

  // Расчетная дистанция.
  distance_km?: number | null

  // Режим передвижения маршрута.
  route_mode: 'walk' | 'public_transport' | 'mixed'

  // Насколько хорошо маршрут попал в нужную длительность.
  duration_fit_score?: number | null

  // Нормализованный стартовый контекст.
  start_context?: StartContextRead | null

  // Список точек маршрута.
  points: ItineraryPoint[]

  // Общее объяснение, почему маршрут такой.
  explanation?: string | null
}

// Базовый URL backend.
// Локально по умолчанию ходим в FastAPI на localhost.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

// Отправляет запрос на генерацию маршрута.
// Пока backend возвращает MVP draft response.
export const generateItinerary = async (
  payload: ItineraryGenerateRequest,
): Promise<ItineraryGenerateResponse> => {
  const response = await fetch(`${API_BASE_URL}/routes/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  // Если backend вернул ошибку — пробрасываем её выше.
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: ItineraryGenerateResponse = await response.json()
  return data
}
