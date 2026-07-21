import { useEffect, useState } from 'react'
import { addPlaceToUserRoute, correctUserRoute, replacePlaceInUserRoute, updateUserRouteOrder, validateActiveRouteSession } from '../../api/recommendations/recommendationRoute.api'
import type { ActiveRouteSession, RecommendationRouteResponse, UserRouteCorrectionAction } from '../../api/recommendations/recommendationRoute.types'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { getCurrentCity } from '../../shared/city/currentCity'
import { RouteResultPanel } from '../../widgets/recommendation-route/RouteResultPanel'
import { isRouteStateConflictError } from '../../widgets/recommendation-route/sessionErrors'
import { clearTmaRoute, clearTmaRouteSession, restoreTmaRoute, restoreTmaRouteSession, saveTmaRoute, saveTmaRouteSession } from './tmaRouteStorage'
import { TmaShell } from './TmaShell'

type RouteMutation = () => Promise<RecommendationRouteResponse>

// A synchronous, non-React lock for route mutations: React `loading` state
// cannot prevent a second concurrent call from a rapid double-tap, because
// state updates are batched/async. Every mutation entry point below
// (onAddCandidate, onCorrect, onMovePoint, onReplacePoint) funnels through
// `apply`, so a single module-level flag, set/checked synchronously, closes
// the race for all of them.
let mutationInFlight = false

export const TmaRoutePage = () => {
  const [route, setRoute] = useState<RecommendationRouteResponse | null>(null)
  const [activeSession, setActiveSession] = useState<ActiveRouteSession | null>(null)
  const [restoring, setRestoring] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mutationStatus, setMutationStatus] = useState<string | null>(null)
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
          setActiveSession(null)
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
        if (!cancelled) setActiveSession(restoredSession)
      } catch (restoreError) {
        console.error(restoreError)
        clearTmaRouteSession()
        if (!cancelled) {
          setActiveSession(null)
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
    setActiveSession(session)
    if (session) saveTmaRouteSession(session)
    else clearTmaRouteSession()
  }

  const apply = async (operation: RouteMutation, pendingMessage: string, successMessage: string) => {
    if (mutationInFlight) return
    mutationInFlight = true
    try {
      setLoading(true)
      setError(null)
      setMutationStatus(pendingMessage)
      const next = await operation()
      setRoute(next)
      saveTmaRoute(next)
      setMutationStatus(successMessage)
      if (activeSession && activeSession.route_id !== next.route_id) {
        clearTmaRouteSession()
        setActiveSession(null)
        setRecoveryNotice('Маршрут изменился. Активную прогулку нужно начать заново.')
      }
    } catch (applyError) {
      console.error(applyError)
      setError(
        isRouteStateConflictError(applyError)
          ? 'Маршрут уже изменился в другом месте. Обновите страницу и повторите действие.'
          : 'Не удалось обновить маршрут. Повторите действие.',
      )
      setMutationStatus(null)
    } finally {
      mutationInFlight = false
      setLoading(false)
    }
  }

  const correct = (action: UserRouteCorrectionAction, targetPlaceId?: string | null) => {
    if (!route || mutationInFlight) return
    const messages: Record<UserRouteCorrectionAction, [string, string]> = {
      remove_place: ['Удаляем точку…', 'Точка удалена.'],
      shorten_route: ['Сокращаем маршрут…', 'Маршрут сокращён.'],
      rebuild_from_here: ['Пересобираем маршрут…', 'Маршрут пересобран.'],
      avoid_category: ['Обновляем предпочтения…', 'Категория исключена.'],
      extend_route: ['Добавляем место…', 'Маршрут дополнен.'],
    }
    const [pending, success] = messages[action]
    void apply(() => correctUserRoute(route, action, targetPlaceId), pending, success)
  }

  return <TmaShell title="Маршрут">
    {restoring ? <div role="status" aria-live="polite" aria-busy="true"><p>Проверяем сохранённый маршрут…</p><Skeleton /><Skeleton /></div> : null}
    {!restoring && error ? <ErrorState title="Маршрут не обновился" description={error} /> : null}
    {!restoring && mutationStatus ? <p className="route-start-note" role="status" aria-live="polite">{mutationStatus}</p> : null}
    {!restoring && recoveryNotice ? <p className="route-start-note" role="status" aria-live="polite">{recoveryNotice}</p> : null}
    {!restoring && !route ? (
      <EmptyState
        title="Маршрут пока пуст"
        description="Добавьте места из каталога кнопкой «Добавить в маршрут» на странице места."
      />
    ) : !restoring && route ? (
      <RouteResultPanel
        key={`${route.route_id}:${activeSession?.session_id ?? 'none'}`}
        route={route}
        loading={loading}
        initialSession={activeSession}
        onSessionChange={onSessionChange}
        onAddCandidate={(placeId) => void apply(() => addPlaceToUserRoute(route, placeId), 'Добавляем место…', 'Место добавлено в маршрут.')}
        onCorrect={correct}
        onMovePoint={(placeId, direction) => {
          if (mutationInFlight) return
          const index = route.points.findIndex((point) => point.place_id === placeId)
          const swapIndex = direction === 'up' ? index - 1 : index + 1
          if (index < 0 || swapIndex < 0 || swapIndex >= route.points.length) return
          const ids = route.points.map((point) => point.place_id)
          const nextIds = [...ids]
          nextIds[index] = ids[swapIndex]
          nextIds[swapIndex] = ids[index]
          void apply(() => updateUserRouteOrder(route, nextIds), 'Меняем порядок точек…', 'Порядок точек обновлён.')
        }}
        onRemovePoint={(placeId) => correct('remove_place', placeId)}
        onReplacePoint={(placeId) => {
          if (mutationInFlight) return
          const candidate = route.candidate_options?.find((point) => !route.points.some((current) => current.place_id === point.place_id))
          if (!candidate) {
            setError('Для этой точки сейчас нет подходящей замены. Попробуйте добавить место или пересобрать маршрут.')
            setMutationStatus(null)
            return
          }
          void apply(() => replacePlaceInUserRoute(route, placeId, candidate.place_id), 'Подбираем замену…', 'Точка заменена.')
        }}
      />
    ) : null}
    {!restoring && route ? <button type="button" className="cg-button cg-button--ghost" disabled={loading} onClick={() => {
      clearTmaRoute()
      setRoute(null)
      setActiveSession(null)
      setRecoveryNotice(null)
      setMutationStatus(null)
      setError(null)
    }}>Очистить маршрут</button> : null}
  </TmaShell>
}
