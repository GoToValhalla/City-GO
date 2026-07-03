import { useEffect, useState, type FormEvent } from 'react'
import { addPlaceToUserRoute, ApiRequestError, buildRecommendationRoute, correctUserRoute, replacePlaceInUserRoute, updateUserRouteOrder } from '../../api/recommendations/recommendationRoute.api'
import type { RecommendationRouteResponse, UserRouteCorrectionAction } from '../../api/recommendations/recommendationRoute.types'
import { buildRecommendationRouteRequest, toggleListValue, type RecommendationRouteFormState } from '../../features/routes/model/recommendationRouteForm'
import { routeMatchesCity } from '../../features/routes/model/routeCityGuard'
import { AppHeader } from '../../components/ui/AppHeader'
import { buildApiUrl } from '../../shared/api/http'
import { getCurrentCity, getCurrentCityCoordinates, type CityOption } from '../../shared/city/currentCity'
import { useLocationProvider } from '../../shared/location/useLocationProvider'
import { RouteHeroPreview } from '../../widgets/recommendation-route/RouteHeroPreview'
import { RouteRequestForm } from '../../widgets/recommendation-route/RouteRequestForm'
import { RouteResultPanel } from '../../widgets/recommendation-route/RouteResultPanel'
import { filterInterestsForFeatures } from '../../widgets/recommendation-route/chipOptions'
import { RandomRouteDraftEditor } from '../../widgets/route-draft/RandomRouteDraftEditor'
import { initialRouteForm } from './routeInitialForm'
import './GenerateRoutePage.css'
import './GenerateRouteControls.css'
import './GenerateRouteMobile.css'
import '../../styles/route-refinements.css'

type RouteDebugInfo = { title: string; timestamp: string; citySlug: string; api?: { method: string; url: string; status: number; responseBody: unknown }; requestPayload?: unknown; error?: string }
type DebugInfoRow = { label: string; value: unknown }

const loadFeatures = async (citySlug: string): Promise<string[]> => {
  const response = await fetch(buildApiUrl('/place-coverage/' + citySlug))
  if (!response.ok) return []
  const data = await response.json()
  return Array.isArray(data.route_features) ? data.route_features : []
}

const routeRenderKey = (route: RecommendationRouteResponse): string => [route.route_id, route.revision, route.total_places, route.total_estimated_minutes, route.total_walk_distance_meters, route.points.map((point) => point.place_id).join('-')].join(':')

const buildDebugInfo = (err: unknown, citySlug: string, requestPayload?: unknown): RouteDebugInfo => {
  if (err instanceof ApiRequestError) return { title: 'Route API error', timestamp: new Date().toISOString(), citySlug, api: { method: err.method, url: err.url, status: err.status, responseBody: err.responseBody }, requestPayload: err.requestBody ?? requestPayload, error: err.message }
  return { title: 'Frontend route error', timestamp: new Date().toISOString(), citySlug, requestPayload, error: err instanceof Error ? `${err.name}: ${err.message}` : String(err) }
}

const getNoRouteMessage = (reason?: string | null): string => {
  const messages: Record<string, string> = {
    no_places_in_city: 'В этом городе пока нет мест.',
    radius_too_small: 'Нет мест рядом со стартовой точкой.',
    all_places_closed: 'Все подходящие места сейчас закрыты.',
    budget_too_strict: 'Не нашли мест в выбранный бюджет.',
    time_budget_too_tight: 'Слишком мало времени.',
    interests_not_matched: 'Нет точных мест по выбранным интересам.',
    filters_too_strict: 'Слишком много ограничений.',
    not_enough_route_points: 'Не хватило подходящих точек для маршрута.',
    slot_constructor_no_matches: 'Не удалось заполнить слоты сценария.',
  }
  return messages[reason ?? ''] ?? 'Не удалось построить маршрут.'
}

const getPartialRouteMessage = (route: RecommendationRouteResponse): string => {
  const firstWarning = route.user_warnings?.[0]?.user_message
  if (firstWarning) return firstWarning
  if (route.partial_reason === 'slot_constructor_missing_required_slot') return 'Маршрут собран частично: часть слотов сценария не найдена.'
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
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return [{ label: prefix || 'value', value: payload }]
  return Object.entries(payload as Record<string, unknown>).flatMap(([key, value]) => {
    const label = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) return flattenDebugInfo(value, label)
    return [{ label, value }]
  })
}

const renderDebugInfo = (debugInfo: RouteDebugInfo) => <section className="route-debug-tile route-debug-page"><div className="route-debug-header"><strong>Route debug</strong><span>{debugInfo.timestamp}</span></div><div className="route-debug-summary-grid">{flattenDebugInfo(debugInfo).map((row) => <div key={row.label}><span>{row.label}</span><strong>{formatDebugValue(row.value)}</strong></div>)}</div></section>

export const GenerateRoutePage = () => {
  const location = useLocationProvider()
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
        setError(null)
        setGeoError(null)
        setForm((current) => ({ ...current, lat: nextCoordinates.lat, lng: nextCoordinates.lng, startSource: 'city_center', interests: filterInterestsForFeatures(current.interests, nextFeatures) }))
        setGeoStatus('Старт маршрута установлен от центра города.')
      } catch (err) {
        console.error(err)
        setError('У города нет координат центра.')
        setForm((current) => ({ ...current, lat: '', lng: '', startSource: '', interests: filterInterestsForFeatures(current.interests, nextFeatures) }))
      }
    }
    void syncCity()
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  const patchForm = (patch: Partial<RecommendationRouteFormState>) => setForm((current) => ({ ...current, ...patch }))

  const useCityCenter = () => {
    try {
      const coordinates = getCurrentCityCoordinates(city.slug)
      setGeoError(null)
      setGeoStatus('Старт маршрута установлен от центра города.')
      patchForm({ lat: coordinates.lat, lng: coordinates.lng, startAddress: '', startSource: 'city_center' })
    } catch (err) {
      console.error(err)
      setGeoError('У города не заданы координаты центра.')
    }
  }

  const useCurrentLocation = async () => {
    setGeoError(null)
    setGeoStatus('Определяем местоположение...')
    const result = await location.request({ scenario: 'route_build' })
    if (!('coordinates' in result)) {
      setGeoStatus(null)
      setGeoError(result.message)
      return
    }
    patchForm({ lat: String(result.coordinates.latitude), lng: String(result.coordinates.longitude), startAddress: '', startSource: 'current_location' })
    setGeoStatus('Геолокация получена.')
  }

  const applyNextRoute = (nextRoute: RecommendationRouteResponse, requestPayload: unknown, mismatchTitle: string): boolean => {
    if (!routeMatchesCity(nextRoute, city.slug)) {
      setError('Маршрут содержит точки другого города. Пересобери маршрут после смены города.')
      setDebugInfo({ title: mismatchTitle, timestamp: new Date().toISOString(), citySlug: city.slug, requestPayload, error: `Expected city ${city.slug}, got route context ${nextRoute.context?.city_id ?? 'unknown'}` })
      setRoute(null)
      return false
    }
    if (nextRoute.status === 'no_route' || nextRoute.status === 'failed') {
      setError(getNoRouteMessage(nextRoute.partial_reason))
      setRoute(nextRoute)
      return false
    }
    setRouteWarning(nextRoute.status === 'partial_route' ? getPartialRouteMessage(nextRoute) : null)
    setRoute(nextRoute)
    return true
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const sanitizedForm = { ...form, interests: filterInterestsForFeatures(form.interests, features) }
    const payload = buildRecommendationRouteRequest(sanitizedForm, city.slug)
    if (!payload.ok) {
      setError(payload.error)
      setRouteWarning(null)
      setRoute(null)
      setDebugInfo({ title: 'Frontend validation error', timestamp: new Date().toISOString(), citySlug: city.slug, requestPayload: sanitizedForm, error: payload.error })
      return
    }
    try {
      setLoading(true)
      setError(null)
      setRouteWarning(null)
      setDebugInfo(null)
      const nextRoute = await buildRecommendationRoute(payload.value)
      applyNextRoute(nextRoute, payload.value, 'Route city mismatch')
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

  const correct = async (action: UserRouteCorrectionAction, targetPlaceId?: string | null) => {
    if (!route) return
    try {
      setLoading(true)
      setError(null)
      setRouteWarning(null)
      setDebugInfo(null)
      const nextRoute = await correctUserRoute(route, action, targetPlaceId)
      applyNextRoute(nextRoute, { route, action, targetPlaceId }, 'Correction city mismatch')
    } catch (err) {
      console.error(err)
      setError('Не удалось скорректировать маршрут')
      setDebugInfo(buildDebugInfo(err, city.slug, { route, action, targetPlaceId }))
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
      applyNextRoute(nextRoute, { route, placeId }, 'Add place city mismatch')
    } catch (err) {
      console.error(err)
      setError('Не удалось добавить место в маршрут')
      setDebugInfo(buildDebugInfo(err, city.slug, { route, placeId }))
    } finally {
      setLoading(false)
    }
  }

  const movePoint = async (placeId: string, direction: 'up' | 'down') => {
    if (!route) return
    const index = route.points.findIndex((point) => point.place_id === placeId)
    const swapIndex = direction === 'up' ? index - 1 : index + 1
    if (index < 0 || swapIndex < 0 || swapIndex >= route.points.length) return
    const ids = route.points.map((point) => point.place_id)
    const nextIds = [...ids]
    nextIds[index] = ids[swapIndex]
    nextIds[swapIndex] = ids[index]
    try {
      setLoading(true)
      const nextRoute = await updateUserRouteOrder(route, nextIds)
      applyNextRoute(nextRoute, { route, orderedPlaceIds: nextIds }, 'Update route order city mismatch')
    } catch (err) {
      console.error(err)
      setError('Не удалось изменить порядок точек')
      setDebugInfo(buildDebugInfo(err, city.slug, { route, placeId, direction }))
    } finally {
      setLoading(false)
    }
  }

  const replacePoint = async (placeId: string) => {
    if (!route) return
    const candidate = route.candidate_options?.find((point) => !route.points.some((current) => current.place_id === point.place_id))
    if (!candidate) {
      await correct('remove_place', placeId)
      return
    }
    try {
      setLoading(true)
      const nextRoute = await replacePlaceInUserRoute(route, placeId, candidate.place_id)
      applyNextRoute(nextRoute, { route, oldPlaceId: placeId, newPlaceId: candidate.place_id }, 'Replace place city mismatch')
    } catch (err) {
      console.error(err)
      setError('Не удалось заменить точку')
      setDebugInfo(buildDebugInfo(err, city.slug, { route, placeId }))
    } finally {
      setLoading(false)
    }
  }

  const routeForm = <RouteRequestForm citySlug={city.slug} features={features} form={form} loading={loading} geoStatus={geoStatus} geoError={geoError} onUseCurrentLocation={useCurrentLocation} onUseCityCenter={useCityCenter} onChange={patchForm} onToggleInterest={(value) => patchForm({ interests: toggleListValue(form.interests, value) })} onToggleAvoided={(value) => patchForm({ avoidedCategories: toggleListValue(form.avoidedCategories, value) })} onSubmit={submit} />
  const slotCount = form.routeSlots?.length ?? 0
  const compactFormSummary = `${city.name} · ${form.useTimeBudget ? `${form.timeBudgetMinutes} мин` : 'без лимита'} · ${slotCount ? `${slotCount} слотов` : form.interests.length ? form.interests.join(', ') : 'без интересов'}`

  return <div className="app-screen"><div className="app-container route-design"><AppHeader /><main className="route-page"><section className="route-hero-tile"><div className="route-hero-copy"><p className="route-eyebrow">Маршрут · {city.name}</p><h1>Собери прогулку</h1><p>Выбери время, старт, интересы или сценарий из слотов.</p></div><RouteHeroPreview cityName={city.name} citySlug={city.slug} /></section><section className={`route-config-tile ${route ? 'route-config-compact' : ''}`}>{route ? <details className="route-form-details"><summary>Настройки маршрута: {compactFormSummary}</summary>{routeForm}</details> : routeForm}</section>{!route ? <RandomRouteDraftEditor citySlug={city.slug} features={features} /> : null}{error ? <section className="route-error-tile">{error}</section> : null}{routeWarning ? <section className="route-error-tile">{routeWarning}</section> : null}{debugInfo ? renderDebugInfo(debugInfo) : null}{route ? <RouteResultPanel key={routeRenderKey(route)} route={route} loading={loading} onAddCandidate={addCandidate} onCorrect={correct} onMovePoint={movePoint} onRemovePoint={(placeId) => void correct('remove_place', placeId)} onReplacePoint={(placeId) => void replacePoint(placeId)} /> : null}</main></div></div>
}
