import { useEffect, useState } from 'react'
import { addPlaceToUserRoute, ApiRequestError, buildRecommendationRoute, correctUserRoute } from '../../api/recommendations/recommendationRoute.api'
import type {
  RecommendationRouteResponse,
  UserRouteCorrectionAction,
} from '../../api/recommendations/recommendationRoute.types'
import {
  buildRecommendationRouteRequest,
  toggleListValue,
  type RecommendationRouteFormState,
} from '../../features/routes/model/recommendationRouteForm'
import { routeMatchesCity } from '../../features/routes/model/routeCityGuard'
import { AppHeader } from '../../components/ui/AppHeader'
import { buildApiUrl } from '../../shared/api/http'
import { getCurrentCity, getCurrentCityCoordinates, type CityOption } from '../../shared/city/currentCity'
import { RouteHeroPreview } from '../../widgets/recommendation-route/RouteHeroPreview'
import { RouteRequestForm } from '../../widgets/recommendation-route/RouteRequestForm'
import { RouteResultPanel } from '../../widgets/recommendation-route/RouteResultPanel'
import { filterInterestsForFeatures } from '../../widgets/recommendation-route/chipOptions'
import { RandomRouteDraftEditor } from '../../widgets/route-draft/RandomRouteDraftEditor'
import { initialRouteForm } from './routeInitialForm'
import './GenerateRoutePage.css'
import './GenerateRouteControls.css'

const GEO_SESSION_KEY = 'citygo:last-route-geolocation'

type RouteDebugInfo = {
  title: string
  timestamp: string
  citySlug: string
  api?: {
    method: string
    url: string
    status: number
    responseBody: unknown
  }
  requestPayload?: unknown
  responseBody?: unknown
  error?: string
}

type DebugInfoRow = {
  label: string
  value: unknown
}

const loadFeatures = async (citySlug: string): Promise<string[]> => {
  const response = await fetch(buildApiUrl('/place-coverage/' + citySlug))
  if (!response.ok) return []
  const data = await response.json()
  return Array.isArray(data.route_features) ? data.route_features : []
}

const readStoredGeolocation = (): { lat: string; lng: string } | null => {
  try {
    const raw = window.sessionStorage.getItem(GEO_SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { lat?: unknown; lng?: unknown }
    if (typeof parsed.lat !== 'string' || typeof parsed.lng !== 'string') return null
    return { lat: parsed.lat, lng: parsed.lng }
  } catch {
    return null
  }
}

const saveStoredGeolocation = (lat: string, lng: string) => {
  window.sessionStorage.setItem(GEO_SESSION_KEY, JSON.stringify({ lat, lng }))
}

const routeRenderKey = (route: RecommendationRouteResponse): string => [
  route.route_id,
  route.revision,
  route.total_places,
  route.total_estimated_minutes,
  route.total_walk_distance_meters,
  route.points.map((point) => point.place_id).join('-'),
].join(':')

const buildDebugInfo = (err: unknown, citySlug: string, requestPayload?: unknown): RouteDebugInfo => {
  if (err instanceof ApiRequestError) {
    return {
      title: 'Route API error',
      timestamp: new Date().toISOString(),
      citySlug,
      api: {
        method: err.method,
        url: err.url,
        status: err.status,
        responseBody: err.responseBody,
      },
      requestPayload: err.requestBody ?? requestPayload,
      error: err.message,
    }
  }
  return {
    title: 'Frontend route error',
    timestamp: new Date().toISOString(),
    citySlug,
    requestPayload,
    error: err instanceof Error ? `${err.name}: ${err.message}\n${err.stack ?? ''}` : String(err),
  }
}

const getNoRouteMessage = (reason?: string | null): string => {
  const messages: Record<string, string> = {
    no_places_in_city: 'В этом городе пока нет мест. Скоро добавим.',
    radius_too_small: 'Нет мест рядом со стартовой точкой. Попробуй другую точку старта.',
    all_places_closed: 'Все подходящие места сейчас закрыты. Попробуй другое время.',
    budget_too_strict: 'Не нашли мест в выбранный бюджет. Попробуй увеличить бюджет.',
    time_budget_too_tight: 'Слишком мало времени. Попробуй выбрать от 60 минут.',
    interests_not_matched: 'Нет точных мест по выбранным интересам. Попробуй другие категории.',
    filters_too_strict: 'Слишком много ограничений. Попробуй сбросить часть фильтров.',
    not_enough_route_points: 'Не хватило подходящих точек для маршрута. Попробуй увеличить время или изменить интересы.',
  }
  return messages[reason ?? ''] ?? 'Не удалось построить маршрут. Попробуй изменить параметры.'
}

const getPartialRouteMessage = (route: RecommendationRouteResponse): string => {
  const firstWarning = route.user_warnings?.[0]?.user_message
  if (firstWarning) return firstWarning
  if (route.partial_reason === 'not_enough_route_points') {
    return 'Маршрут получился коротким. Показываем то, что удалось собрать.'
  }
  return 'Маршрут собран частично. Проверь предупреждения перед стартом.'
}

const formatDebugValue = (value: unknown): string => {
  if (value === undefined || value === null || value === '') return '-'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.length ? value.map(formatDebugValue).join(', ') : '-'
  return JSON.stringify(value)
}

const flattenDebugInfo = (payload: unknown, prefix = ''): DebugInfoRow[] => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return [{ label: prefix || 'value', value: payload }]
  }
  return Object.entries(payload as Record<string, unknown>).flatMap(([key, value]) => {
    const label = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return flattenDebugInfo(value, label)
    }
    return [{ label, value }]
  })
}

const renderDebugInfo = (debugInfo: RouteDebugInfo) => (
  <section className="route-debug-tile route-debug-page">
    <div className="route-debug-header">
      <strong>Route debug</strong>
      <span>{debugInfo.timestamp}</span>
    </div>
    <div className="route-debug-summary-grid">
      {flattenDebugInfo(debugInfo).map((row) => (
        <div key={row.label}>
          <span>{row.label}</span>
          <strong>{formatDebugValue(row.value)}</strong>
        </div>
      ))}
    </div>
  </section>
)

export const GenerateRoutePage = () => {
  const [city, setCity] = useState<CityOption>(getCurrentCity())
  const [features, setFeatures] = useState<string[]>([])
  const [form, setForm] = useState(initialRouteForm)
  const [loading, setLoading] = useState(false)
  const [geoStatus, setGeoStatus] = useState<string | null>(null)
  const [geoError, setGeoError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [routeWarning, setRouteWarning] = useState<string | null>(null)
  const [debugInfo, setDebugInfo] = useState<RouteDebugInfo | null>(null)
  const [route, setRoute] = useState<RecommendationRouteResponse | null>(null)

  useEffect(() => {
    const syncCity = async () => {
      const nextCity = getCurrentCity()
      setCity(nextCity)
      setRoute(null)
      setRouteWarning(null)
      setDebugInfo(null)
      const nextFeatures = await loadFeatures(nextCity.slug)
      setFeatures(nextFeatures)

      try {
        const nextCoordinates = getCurrentCityCoordinates(nextCity.slug)
        const storedLocation = readStoredGeolocation()
        setError(null)
        setGeoError(null)
        setForm((current) => ({
          ...current,
          lat: storedLocation?.lat ?? nextCoordinates.lat,
          lng: storedLocation?.lng ?? nextCoordinates.lng,
          startSource: storedLocation ? 'current_location' : 'city_center',
          interests: filterInterestsForFeatures(current.interests, nextFeatures),
        }))
        setGeoStatus(storedLocation ? 'Используем сохранённую геолокацию из этой сессии.' : 'Старт маршрута установлен от центра города.')
      } catch (err) {
        console.error(err)
        setError('У выбранного города нет координат центра. Выбери геолокацию или добавь координаты города в БД.')
        setForm((current) => ({
          ...current,
          lat: '',
          lng: '',
          startSource: '',
          interests: filterInterestsForFeatures(current.interests, nextFeatures),
        }))
      }
    }

    void syncCity()
    window.addEventListener('citygo:city-changed', syncCity)

    return () => {
      window.removeEventListener('citygo:city-changed', syncCity)
    }
  }, [])

  const patchForm = (patch: Partial<RecommendationRouteFormState>) => {
    setForm((current) => ({ ...current, ...patch }))
  }

  const useCityCenter = () => {
    try {
      const coordinates = getCurrentCityCoordinates(city.slug)
      setGeoError(null)
      setGeoStatus('Старт маршрута установлен от центра города.')
      patchForm({
        lat: coordinates.lat,
        lng: coordinates.lng,
        startAddress: '',
        startSource: 'city_center',
      })
    } catch (err) {
      console.error(err)
      setGeoError('У города не заданы координаты центра.')
    }
  }

  const useCurrentLocation = () => {
    if (!window.navigator.geolocation) {
      setGeoError('Браузер не поддерживает геолокацию.')
      return
    }
    setGeoError(null)
    setGeoStatus('Запрашиваем геолокацию браузера...')
    window.navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = String(position.coords.latitude)
        const lng = String(position.coords.longitude)
        saveStoredGeolocation(lat, lng)
        setGeoStatus('Геолокация получена. Маршрут стартует от текущего места.')
        patchForm({
          lat,
          lng,
          startAddress: '',
          startSource: 'current_location',
        })
      },
      (geoErr) => {
        console.error(geoErr)
        setGeoStatus(null)
        setGeoError('Не удалось получить геолокацию. Проверь разрешение браузера или используй центр города.')
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      },
    )
  }

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const sanitizedForm = {
      ...form,
      interests: filterInterestsForFeatures(form.interests, features),
    }
    const payload = buildRecommendationRouteRequest(sanitizedForm, city.slug)
    if (!payload.ok) {
      setError(payload.error)
      setRouteWarning(null)
      setRoute(null)
      setDebugInfo({
        title: 'Frontend validation error',
        timestamp: new Date().toISOString(),
        citySlug: city.slug,
        requestPayload: sanitizedForm,
        error: payload.error,
      })
      return
    }

    try {
      setLoading(true)
      setError(null)
      setRouteWarning(null)
      setDebugInfo(null)
      const nextRoute = await buildRecommendationRoute(payload.value)
      if (!routeMatchesCity(nextRoute, city.slug)) {
        setError('Маршрут содержит точки другого города. Пересобери маршрут после смены города.')
        setDebugInfo({
          title: 'Route city mismatch',
          timestamp: new Date().toISOString(),
          citySlug: city.slug,
          requestPayload: payload.value,
          error: `Expected city ${city.slug}, got route context ${nextRoute.context?.city_id ?? 'unknown'}`,
        })
        setRoute(null)
        return
      }

      if (nextRoute.status === 'no_route' || nextRoute.status === 'failed') {
        setError(getNoRouteMessage(nextRoute.partial_reason))
        setRoute(nextRoute)
        return
      }

      if (nextRoute.status === 'partial_route') {
        setRouteWarning(getPartialRouteMessage(nextRoute))
      }
      setRoute(nextRoute)
    } catch (err) {
      console.error(err)
      setError('Технический сбой. Попробуй ещё раз.')
      setRouteWarning(null)
      setDebugInfo(buildDebugInfo(err, city.slug, payload.value))
      setRoute(null)
    } finally {
      setLoading(false)
    }
  }

  const correct = async (action: UserRouteCorrectionAction) => {
    if (!route) return
    try {
      setLoading(true)
      setError(null)
      setRouteWarning(null)
      setDebugInfo(null)
      const nextRoute = await correctUserRoute(route, action)
      if (!routeMatchesCity(nextRoute, city.slug)) {
        setError('Коррекция вернула точки другого города. Пересобери маршрут.')
        setDebugInfo({
          title: 'Correction city mismatch',
          timestamp: new Date().toISOString(),
          citySlug: city.slug,
          requestPayload: { route, action },
          error: `Expected city ${city.slug}, got route context ${nextRoute.context?.city_id ?? 'unknown'}`,
        })
        return
      }
      setRouteWarning(nextRoute.status === 'partial_route' ? getPartialRouteMessage(nextRoute) : null)
      setRoute(nextRoute)
    } catch (err) {
      console.error(err)
      setError('Не удалось скорректировать маршрут')
      setDebugInfo(buildDebugInfo(err, city.slug, { route, action }))
    } finally {
      setLoading(false)
    }
  }

  const addCandidate = async (placeId: string) => {
    if (!route) return
    try {
      setLoading(true)
      setError(null)
      setRouteWarning(null)
      setDebugInfo(null)
      const nextRoute = await addPlaceToUserRoute(route, placeId)
      if (!routeMatchesCity(nextRoute, city.slug)) {
        setError('Добавление вернуло точки другого города. Пересобери маршрут.')
        setDebugInfo({
          title: 'Add place city mismatch',
          timestamp: new Date().toISOString(),
          citySlug: city.slug,
          requestPayload: { route, placeId },
          error: `Expected city ${city.slug}, got route context ${nextRoute.context?.city_id ?? 'unknown'}`,
        })
        return
      }
      setRouteWarning(nextRoute.status === 'partial_route' ? getPartialRouteMessage(nextRoute) : null)
      setRoute(nextRoute)
    } catch (err) {
      console.error(err)
      setError('Не удалось добавить место в маршрут')
      setDebugInfo(buildDebugInfo(err, city.slug, { route, placeId }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-screen">
      <div className="app-container route-design">
        <AppHeader />
        <main className="route-page">
          <section className="route-hero-tile">
            <div className="route-hero-copy">
              <p className="route-eyebrow">Маршрут · {city.name}</p>
              <h1>Собери прогулку без лишних вопросов</h1>
              <p>Выбери время, настроение и ограничения. City Go покажет точки,
                адреса, порядок остановок и примерную длительность.</p>
            </div>
            <RouteHeroPreview features={features} />
          </section>
          <section className="route-config-tile">
            <RouteRequestForm
              features={features}
              form={form}
              loading={loading}
              geoStatus={geoStatus}
              geoError={geoError}
              onUseCurrentLocation={useCurrentLocation}
              onUseCityCenter={useCityCenter}
              onChange={patchForm}
              onToggleInterest={(value) => patchForm({ interests: toggleListValue(form.interests, value) })}
              onToggleAvoided={(value) => patchForm({
                avoidedCategories: toggleListValue(form.avoidedCategories, value),
              })}
              onSubmit={submit}
            />
          </section>
          <RandomRouteDraftEditor citySlug={city.slug} features={features} />
          {error ? <section className="route-error-tile">{error}</section> : null}
          {routeWarning ? <section className="route-error-tile">{routeWarning}</section> : null}
          {debugInfo ? renderDebugInfo(debugInfo) : null}
          {route ? <RouteResultPanel key={routeRenderKey(route)} route={route} loading={loading} onAddCandidate={addCandidate} onCorrect={correct} /> : null}
        </main>
      </div>
    </div>
  )
}
