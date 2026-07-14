import { useEffect, useState } from 'react'
import { addPlaceToUserRoute, correctUserRoute, replacePlaceInUserRoute, updateUserRouteOrder } from '../../api/recommendations/recommendationRoute.api'
import type { ActiveRouteSession, RecommendationRouteResponse, UserRouteCorrectionAction } from '../../api/recommendations/recommendationRoute.types'
import { EmptyState } from '../../components/ui/EmptyState'
import { getCurrentCity } from '../../shared/city/currentCity'
import { RouteResultPanel } from '../../widgets/recommendation-route/RouteResultPanel'
import { clearTmaRoute, clearTmaRouteSession, restoreTmaRoute, restoreTmaRouteSession, saveTmaRoute, saveTmaRouteSession } from './tmaRouteStorage'
import { TmaShell } from './TmaShell'

export const TmaRoutePage = () => {
  const [route, setRoute] = useState<RecommendationRouteResponse | null>(null)
  const [initialSession, setInitialSession] = useState<ActiveRouteSession | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const city = getCurrentCity()
    const restored = restoreTmaRoute()
    const matchesCity = restored && restored.city_slug === city.slug
    setRoute(matchesCity ? restored : null)
    // A route for a different/no-longer-restorable city means its session
    // (if any) is stale local state too — never show progress for a route
    // that is no longer the active one.
    setInitialSession(matchesCity ? restoreTmaRouteSession(restored!.route_id) : null)
    if (!matchesCity) clearTmaRouteSession()
  }, [])

  const onSessionChange = (session: ActiveRouteSession | null) => {
    if (session) saveTmaRouteSession(session)
    else clearTmaRouteSession()
  }

  const apply = async (operation: Promise<RecommendationRouteResponse>) => {
    try {
      setLoading(true)
      setError(null)
      const next = await operation
      setRoute(next)
      saveTmaRoute(next)
    } catch (err) {
      console.error(err)
      setError('Не удалось обновить маршрут')
    } finally {
      setLoading(false)
    }
  }

  const correct = (action: UserRouteCorrectionAction, targetPlaceId?: string | null) => {
    if (!route) return
    void apply(correctUserRoute(route, action, targetPlaceId))
  }

  return <TmaShell title="Маршрут">
    {error ? <p className="route-error-inline">{error}</p> : null}
    {!route ? (
      <EmptyState
        title="Маршрут пока пуст"
        description="Добавьте места из каталога кнопкой «Добавить в маршрут» на странице места."
      />
    ) : (
      <RouteResultPanel
        route={route}
        loading={loading}
        initialSession={initialSession}
        onSessionChange={onSessionChange}
        onAddCandidate={(placeId) => void apply(addPlaceToUserRoute(route, placeId))}
        onCorrect={correct}
        onMovePoint={(placeId, direction) => {
          const index = route.points.findIndex((point) => point.place_id === placeId)
          const swapIndex = direction === 'up' ? index - 1 : index + 1
          if (index < 0 || swapIndex < 0 || swapIndex >= route.points.length) return
          const ids = route.points.map((point) => point.place_id)
          const nextIds = [...ids]
          nextIds[index] = ids[swapIndex]
          nextIds[swapIndex] = ids[index]
          void apply(updateUserRouteOrder(route, nextIds))
        }}
        onRemovePoint={(placeId) => correct('remove_place', placeId)}
        onReplacePoint={(placeId) => {
          const candidate = route.candidate_options?.find((point) => !route.points.some((current) => current.place_id === point.place_id))
          if (!candidate) { correct('remove_place', placeId); return }
          void apply(replacePlaceInUserRoute(route, placeId, candidate.place_id))
        }}
      />
    )}
    {route ? <button type="button" className="cg-button cg-button--ghost" onClick={() => { clearTmaRoute(); setRoute(null); setInitialSession(null) }}>Очистить маршрут</button> : null}
  </TmaShell>
}
