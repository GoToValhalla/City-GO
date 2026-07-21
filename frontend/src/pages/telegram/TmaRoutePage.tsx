import { useEffect, useState } from 'react'
import { addPlaceToUserRoute, correctUserRoute, replacePlaceInUserRoute, updateUserRouteOrder, validateActiveRouteSession } from '../../api/recommendations/recommendationRoute.api'
import type { ActiveRouteSession, RecommendationRouteResponse, UserRouteCorrectionAction } from '../../api/recommendations/recommendationRoute.types'
import { EmptyState } from '../../components/ui/EmptyState'
import { getCurrentCity } from '../../shared/city/currentCity'
import { RouteResultPanel } from '../../widgets/recommendation-route/RouteResultPanel'
import { clearTmaRoute, clearTmaRouteSession, restoreTmaRoute, restoreTmaRouteSession, saveTmaRoute, saveTmaRouteSession } from './tmaRouteStorage'
import { TmaShell } from './TmaShell'

export const TmaRoutePage = () => {
  const [route, setRoute] = useState<RecommendationRouteResponse | null>(null)
  const [initialSession, setInitialSession] = useState<ActiveRouteSession | null>(null)
  const [restoring, setRestoring] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recoveryNotice, setRecoveryNotice] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const restore = async () => {
      const city = getCurrentCity()
      const restoredRoute = restoreTmaRoute()
      const matchesCity = Boolean(restoredRoute && restoredRoute.city_slug === city.slug)

      if (!matchesCity || !restoredRoute) {
        if (restoredRoute) clearTmaRoute()
        else clearTmaRouteSession()
        if (!cancelled) {
          setRoute(null)
          setInitialSession(null)
          setRestoring(false)
        }
        return
      }

      const restoredSession = restoreTmaRouteSession(restoredRoute.route_id)
      if (!cancelled) setRoute(restoredRoute)

      if (!restoredSession) {
        if (!cancelled) setRestoring(false)
        return
      }

      try {
        await validateActiveRouteSession(restoredSession)
        if (!cancelled) setInitialSession(restoredSession)
      } catch (restoreError) {
        console.error(restoreError)
        clearTmaRouteSession()
        if (!cancelled) {
          setInitialSession(null)
          setRecoveryNotice('Сохранённую прогулку не удалось продолжить. Маршрут можно начать заново.')
        }
      } finally {
        if (!cancelled) setRestoring(false)
      }
    }

    void restore()
    return () => { cancelled = true }
  }, [])

  const onSessionChange = (session: ActiveRouteSession | null) => {
    if (session) saveTmaRouteSession(session)
    else clearTmaRouteSession()
  }

  const apply = async (operation: Promise<RecommendationRouteResponse>) => {
    if (loading) return
    try {
      setLoading(true)
      setError(null)
      const next = await operation
      setRoute(next)
      saveTmaRoute(next)
      if (initialSession && initialSession.route_id !== next.route_id) {
        clearTmaRouteSession()
        setInitialSession(null)
      }
    } catch (applyError) {
      console.error(applyError)
      setError('Не удалось обновить маршрут. Повторите действие.')
    } finally {
      setLoading(false)
    }
  }

  const correct = (action: UserRouteCorrectionAction, targetPlaceId?: string | null) => {
    if (!route || loading) return
    void apply(correctUserRoute(route, action, targetPlaceId))
  }

  return <TmaShell title="Маршрут">
    {restoring ? <p role="status" aria-live="polite">Проверяем сохранённый маршрут…</p> : null}
    {error ? <p className="route-error-inline" role="alert">{error}</p> : null}
    {recoveryNotice ? <p className="route-start-note" role="status">{recoveryNotice}</p> : null}
    {!restoring && !route ? (
      <EmptyState
        title="Маршрут пока пуст"
        description="Добавьте места из каталога кнопкой «Добавить в маршрут» на странице места."
      />
    ) : route ? (
      <RouteResultPanel
        route={route}
        loading={loading || restoring}
        initialSession={restoring ? null : initialSession}
        onSessionChange={onSessionChange}
        onAddCandidate={(placeId) => void apply(addPlaceToUserRoute(route, placeId))}
        onCorrect={correct}
        onMovePoint={(placeId, direction) => {
          if (loading) return
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
          if (loading) return
          const candidate = route.candidate_options?.find((point) => !route.points.some((current) => current.place_id === point.place_id))
          if (!candidate) {
            correct('remove_place', placeId)
            return
          }
          void apply(replacePlaceInUserRoute(route, placeId, candidate.place_id))
        }}
      />
    ) : null}
    {route ? <button type="button" className="cg-button cg-button--ghost" disabled={loading || restoring} onClick={() => {
      clearTmaRoute()
      setRoute(null)
      setInitialSession(null)
      setRecoveryNotice(null)
    }}>Очистить маршрут</button> : null}
  </TmaShell>
}
