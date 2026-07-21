import { useMemo, useState } from 'react'
import { CheckCircle2, Clock, Map, Pause, Play, Plus, RefreshCw, SkipForward, Star, StopCircle, Wand2 } from 'lucide-react'
import type {
  ActiveRouteAction,
  ActiveRouteSession,
  RecommendationRoutePoint,
  RecommendationRouteResponse,
  RouteQualityStatus,
  UserRouteCorrectionAction,
} from '../../api/recommendations/recommendationRoute.types'
import { sendRouteFeedback, startActiveRouteSession, updateActiveRouteSession } from '../../api/recommendations/recommendationRoute.api'
import { MapLibreMap } from '../../shared/map/MapLibreMap'
import type { MapPoint, MapRouteState } from '../../shared/map/mapTypes'
import { isDebugEnabled } from '../../shared/config/debug'
import { DiagnosticsPanel } from '../../shared/debug/DiagnosticsPanel'
import { RouteCandidateOptions } from './RouteCandidateOptions'
import { RouteDataNotes } from './RouteDataNotes'
import { RouteDebugTrace } from './RouteDebugTrace'
import { RouteInsights } from './RouteInsights'
import { RoutePointList } from './RoutePointList'
import { RouteWarnings } from './RouteWarnings'
import { emptyCopy, emptyTitle, statusLabel } from './routeResultStatusText'
import { isSessionInvalidError } from './sessionErrors'

const QUALITY_LABELS: Record<RouteQualityStatus, string> = {
  good: 'Хороший маршрут',
  acceptable: 'Нормальный маршрут',
  weak: 'Слабый маршрут',
  failed: 'Маршрут не собран',
}

const QUALITY_COPY: Record<RouteQualityStatus, string> = {
  good: 'Точки, расстояния и данные выглядят сбалансированно.',
  acceptable: 'Маршрут можно пройти, но есть небольшие компромиссы.',
  weak: 'Маршрут слабый: лучше добавить место, заменить точку или пересобрать.',
  failed: 'Не удалось собрать готовый маршрут. Измените параметры и попробуйте снова.',
}

const ROUTE_FAILURE_STATUSES = new Set(['preview_failed', 'failed', 'no_route', 'empty'])
const ROUTE_READY_STATUSES = new Set(['ready', 'partial_route'])
const FEEDBACK_PROBLEMS = [
  ['bad_route', 'Маршрут не подходит'],
  ['wrong_place', 'Проблема с местом'],
  ['too_long', 'Слишком длинный'],
  ['too_short', 'Слишком короткий'],
] as const

type Props = {
  route: RecommendationRouteResponse
  loading: boolean
  onAddCandidate: (placeId: string) => void
  onCorrect: (action: UserRouteCorrectionAction, targetPlaceId?: string | null) => void
  onMovePoint?: (placeId: string, direction: 'up' | 'down') => void
  onRemovePoint?: (placeId: string) => void
  onReplacePoint?: (placeId: string) => void
  initialSession?: ActiveRouteSession | null
  onSessionChange?: (session: ActiveRouteSession | null) => void
}

const normalizeQualityStatus = (route: RecommendationRouteResponse): RouteQualityStatus => {
  const direct = route.quality_status
  if (direct === 'good' || direct === 'acceptable' || direct === 'weak' || direct === 'failed') return direct
  const breakdownStatus = route.quality_breakdown?.status
  if (breakdownStatus === 'good' || breakdownStatus === 'acceptable' || breakdownStatus === 'weak' || breakdownStatus === 'failed') return breakdownStatus
  if (ROUTE_FAILURE_STATUSES.has(route.status ?? '') || route.points.length === 0) return 'failed'
  if ((route.quality_score ?? 0) >= 0.75) return 'good'
  if ((route.quality_score ?? 0) >= 0.5) return 'acceptable'
  return 'weak'
}

const toMapPoints = (points: RecommendationRoutePoint[]): MapPoint[] => points.flatMap((point, index) => {
  const latitude = Number(point.lat)
  const longitude = Number(point.lng)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return []
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || (latitude === 0 && longitude === 0)) return []
  const parsedId = Number(point.place_id)
  return [{
    id: Number.isFinite(parsedId) ? parsedId : index + 1,
    latitude,
    longitude,
    title: point.title?.trim() || `Точка ${index + 1}`,
    category: point.category,
    order: index + 1,
  }]
})

const formatMeters = (meters?: number | null): string => {
  if (!meters || meters <= 0) return 'дистанция уточняется'
  if (meters < 1000) return `${Math.round(meters)} м`
  return `${Math.round(meters / 100) / 10} км`
}

const nextLegText = (point: RecommendationRoutePoint): string => {
  const minutes = typeof point.estimated_walk_minutes === 'number' ? point.estimated_walk_minutes : null
  const distance = formatMeters(point.estimated_distance_meters)
  return minutes && minutes > 0 ? `${minutes} мин · ${distance}` : distance
}

const RouteMapPreview = ({ points }: { points: RecommendationRoutePoint[] }) => {
  const mapPoints = useMemo(() => toMapPoints(points), [points])
  const [activePointId, setActivePointId] = useState<number | null>(null)
  const [walkingRoute, setWalkingRoute] = useState<MapRouteState | null>(null)
  const activePoint = mapPoints.find((point) => point.id === activePointId) ?? null

  if (mapPoints.length === 0) {
    return <div className="route-map-preview route-map-preview-empty" role="status">
      <strong>Карта пока недоступна</strong>
      <span>Для визуализации нужны корректные координаты точек.</span>
    </div>
  }

  return <div className="route-map-preview" aria-label="Карта маршрута">
    <MapLibreMap
      className="route-map-canvas"
      points={mapPoints}
      activePointId={activePointId}
      routeLine
      interactiveSelection={false}
      onPointSelect={setActivePointId}
      onRouteStateChange={setWalkingRoute}
    />
    <div className="route-map-caption" aria-live="polite">
      <strong>{activePoint ? `${activePoint.order}. ${activePoint.title}` : `${mapPoints.length} точек на маршруте`}</strong>
      <span>{activePoint
        ? 'Выбрана точка маршрута.'
        : walkingRoute?.status === 'routed'
          ? `Путь построен: ${formatMeters(walkingRoute.distanceMeters)}.`
          : 'Строим пешеходный путь между точками.'}</span>
    </div>
  </div>
}

export const RouteResultPanel = ({
  route,
  loading,
  onAddCandidate,
  onCorrect,
  onMovePoint,
  onRemovePoint,
  onReplacePoint,
  initialSession = null,
  onSessionChange,
}: Props) => {
  const [rating, setRating] = useState<number | null>(null)
  const [feedbackComment, setFeedbackComment] = useState('')
  const [feedbackProblems, setFeedbackProblems] = useState<string[]>([])
  const [feedbackPending, setFeedbackPending] = useState(false)
  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null)
  const [session, setSessionState] = useState<ActiveRouteSession | null>(initialSession)
  const [sessionPending, setSessionPending] = useState(false)
  const [sessionStatus, setSessionStatus] = useState<string | null>(null)
  const [sessionInvalid, setSessionInvalid] = useState(false)
  const [seededForRouteId, setSeededForRouteId] = useState(route.route_id)

  if (route.route_id !== seededForRouteId) {
    setSeededForRouteId(route.route_id)
    setSessionState(initialSession)
    setSessionInvalid(false)
  }

  const setSession = (next: ActiveRouteSession | null) => {
    setSessionState(next)
    onSessionChange?.(next)
    if (next) setSessionInvalid(false)
  }

  const routeStatus = route.status ?? 'ready'
  const qualityStatus = normalizeQualityStatus(route)
  const hasPoints = route.points.length > 0
  const meaningfulRoute = route.points.length >= 2
  const routeFailed = ROUTE_FAILURE_STATUSES.has(routeStatus)
  const routeStartable = ROUTE_READY_STATUSES.has(routeStatus) && meaningfulRoute
  const isPartial = routeStatus === 'partial_route'
  const debug = isDebugEnabled()
  const quality = route.quality_score ?? 0
  const summary = route.explanation?.summary?.trim() || `Маршрут ${route.route_id}`
  const walkMeters = route.total_walk_distance_meters ?? Math.max(0, route.estimated_distance || 0) * 1000
  const reasons = Object.fromEntries((route.explanation?.points ?? []).map((point) => [point.place_id, point.reason]))
  const currentPlaceId = session?.current_place_id ?? route.points[0]?.place_id ?? null
  const currentPoint = route.points.find((point) => point.place_id === currentPlaceId) ?? route.points[0] ?? null
  const nextPoint = session?.next_place_id
    ? route.points.find((point) => point.place_id === session.next_place_id) ?? null
    : session ? null : route.points[1] ?? null
  const sessionTerminal = session?.status === 'completed' || session?.status === 'abandoned'
  const controlsDisabled = loading || sessionPending
  const canCompleteOrSkip = Boolean(session && (session.status === 'active' || session.status === 'paused') && currentPlaceId && !sessionTerminal)
  const canPause = session?.status === 'active'
  const canResume = session?.status === 'paused'
  const canFinish = Boolean(session && (session.status === 'active' || session.status === 'paused' || session.status === 'planned'))
  const canStart = routeStartable && (!session || sessionTerminal || sessionInvalid)

  const submitFeedback = async () => {
    if (!rating || feedbackPending) return
    try {
      setFeedbackPending(true)
      setFeedbackStatus('Отправляем отзыв…')
      await sendRouteFeedback(route, rating, feedbackComment, feedbackProblems)
      setFeedbackStatus('Спасибо. Отзыв сохранён.')
    } catch (error) {
      console.error(error)
      setFeedbackStatus('Не удалось отправить отзыв. Попробуйте ещё раз.')
    } finally {
      setFeedbackPending(false)
    }
  }

  const startSession = async () => {
    if (!canStart || sessionPending) return
    try {
      setSessionPending(true)
      setSessionStatus('Запускаем маршрут…')
      const nextSession = await startActiveRouteSession(route, sessionInvalid ? null : session?.ownership_token)
      setSession(nextSession)
      setSessionStatus('Маршрут начат.')
    } catch (error) {
      console.error(error)
      if (isSessionInvalidError(error)) {
        setSession(null)
        setSessionInvalid(true)
        setSessionStatus('Сохранённая прогулка больше не действует. Начните маршрут заново.')
      } else {
        setSessionStatus('Не удалось начать маршрут. Попробуйте ещё раз.')
      }
    } finally {
      setSessionPending(false)
    }
  }

  const applySessionAction = async (action: ActiveRouteAction, placeId?: string | null) => {
    if (sessionPending || !session) return
    try {
      setSessionPending(true)
      setSessionStatus('Обновляем прогулку…')
      const nextSession = await updateActiveRouteSession(session, action, placeId ?? currentPlaceId)
      setSession(nextSession)
      setSessionStatus(action === 'finish' ? 'Маршрут завершён.' : 'Прогулка обновлена.')
    } catch (error) {
      console.error(error)
      if (isSessionInvalidError(error) || !session.ownership_token?.trim()) {
        setSession(null)
        setSessionInvalid(true)
        setSessionStatus('Сохранённая прогулка больше не действует. Начните маршрут заново.')
      } else {
        setSessionStatus('Не удалось обновить прогулку. Повторите действие.')
      }
    } finally {
      setSessionPending(false)
    }
  }

  const sessionCopy = sessionInvalid
    ? 'Сохранённая прогулка больше не действует. Начните маршрут заново.'
    : !session
      ? 'Маршрут ещё не начат.'
      : session.status === 'completed'
        ? 'Маршрут завершён.'
        : session.status === 'abandoned'
          ? 'Маршрут прекращён.'
          : session.status === 'paused'
            ? 'Маршрут на паузе.'
            : session.status === 'planned'
              ? 'Маршрут подготовлен к началу.'
              : `Текущая точка: ${currentPoint?.title?.trim() || 'следующая точка'}`

  return <section className="route-result-grid route-result-grid-mobile-first" aria-busy={loading || sessionPending || feedbackPending}>
    <div className="route-result-tile route-result-summary">
      <div className="route-result-top">
        <div>
          <p className="route-eyebrow">{statusLabel(routeStatus)} · {meaningfulRoute ? QUALITY_LABELS[qualityStatus] : 'Недостаточно точек'}</p>
          <h2>{routeFailed ? emptyTitle(route.partial_reason) : !meaningfulRoute ? 'Пока мало данных для прогулки' : summary}</h2>
        </div>
      </div>
      <p className={`route-quality-banner route-quality-${qualityStatus}`}>{QUALITY_COPY[qualityStatus]}</p>
      {routeFailed ? <p className="route-empty-copy">{emptyCopy(route.partial_reason)}</p> : null}
      {isPartial ? <p className="route-empty-copy">Нашли меньше подходящих точек, чем планировалось. Результат показан без искусственного статуса успеха.</p> : null}
      <div className="route-metrics route-metrics-primary">
        <span><Map size={16} /> {route.points.length} мест</span>
        <span><Clock size={16} /> {route.total_estimated_minutes > 0 ? `${route.total_estimated_minutes} мин` : 'время уточняется'}</span>
        <span>{formatMeters(walkMeters)} пешком</span>
        {debug ? <span>Качество {Math.round(quality * 100)}%</span> : null}
      </div>
      <div className="route-main-actions">
        <button type="button" disabled={loading} onClick={() => onCorrect('rebuild_from_here')}><RefreshCw size={16} /> Пересобрать</button>
        <button type="button" disabled={loading} onClick={() => onCorrect('extend_route')}><Plus size={16} /> Добавить место</button>
        <button type="button" disabled={loading || !route.points[0]} onClick={() => route.points[0] && onReplacePoint?.(route.points[0].place_id)}><Wand2 size={16} /> Заменить точку</button>
        {hasPoints && canStart ? <button type="button" disabled={controlsDisabled} onClick={() => void startSession()}><Play size={16} /> {sessionTerminal ? 'Начать заново' : 'Начать маршрут'}</button> : null}
      </div>
      <RouteInsights route={route} />
      <fieldset className="route-correction-bar" disabled={feedbackPending}>
        <legend>Оценка маршрута</legend>
        <div>{[1, 2, 3, 4, 5].map((value) => <button key={value} type="button" aria-pressed={rating === value} onClick={() => setRating(value)}><Star size={16} /> {value}</button>)}</div>
        {rating && rating <= 3 ? <div>{FEEDBACK_PROBLEMS.map(([value, label]) => <label key={value}><input type="checkbox" checked={feedbackProblems.includes(value)} onChange={(event) => setFeedbackProblems((current) => event.target.checked ? [...current, value] : current.filter((item) => item !== value))} /> {label}</label>)}</div> : null}
        <label>Комментарий<textarea value={feedbackComment} maxLength={1000} onChange={(event) => setFeedbackComment(event.target.value)} /></label>
        <button type="button" disabled={!rating || feedbackPending} onClick={() => void submitFeedback()}>Отправить отзыв</button>
      </fieldset>
      {feedbackStatus ? <p className="route-feedback-status" aria-live="polite">{feedbackStatus}</p> : null}
      <RouteDataNotes route={route} />
    </div>

    <RouteWarnings route={route} />

    {hasPoints ? <div className="route-result-tile route-active-session">
      <h2>Активная прогулка</h2>
      <p>{sessionCopy}</p>
      {nextPoint && session && !sessionTerminal ? <p className="route-muted">Дальше: {nextPoint.title?.trim() || 'следующая точка'}</p> : null}
      {sessionStatus ? <p className="route-start-note" role="status" aria-live="polite">{sessionStatus}</p> : null}
      <div className="route-main-actions">
        <button type="button" disabled={controlsDisabled || !canCompleteOrSkip} onClick={() => void applySessionAction('complete_point')}><CheckCircle2 size={16} /> Я на месте</button>
        <button type="button" disabled={controlsDisabled || !canCompleteOrSkip} onClick={() => void applySessionAction('skip_point')}><SkipForward size={16} /> Пропустить</button>
        {canPause ? <button type="button" disabled={controlsDisabled} onClick={() => void applySessionAction('pause')}><Pause size={16} /> Пауза</button> : null}
        {canResume ? <button type="button" disabled={controlsDisabled} onClick={() => void applySessionAction('resume')}><Play size={16} /> Продолжить</button> : null}
        <button type="button" disabled={controlsDisabled || !canFinish} onClick={() => void applySessionAction('finish')}><StopCircle size={16} /> Завершить маршрут</button>
      </div>
    </div> : null}

    {hasPoints ? <div className="route-result-tile route-map-tile"><h2>Карта</h2><RouteMapPreview points={route.points} /></div> : null}
    {debug ? <DiagnosticsPanel compact={false} payload={{ screen: 'route', category: 'route', severity: route.user_warnings?.length ? 'warning' : 'info', city_slug: route.city_slug, request_id: route.request_id, route_id: route.route_id, title: 'Route diagnostics', summary: `${route.points.length} точек · ${route.user_warnings?.length ?? 0} предупреждений`, warnings: route.user_warnings ?? [], debug_trace: route.debug_trace, response_summary: { quality_score: route.quality_score, total_places: route.points.length, status: route.status } }} details={route} /> : null}
    {debug ? <RouteDebugTrace route={route} /> : null}
    {hasPoints ? <div className="route-result-tile"><h2>Куда идти</h2><RoutePointList disabled={loading || sessionPending || Boolean(session && !sessionTerminal)} points={route.points} reasons={reasons} activePlaceId={currentPlaceId} onMove={onMovePoint} onRemove={onRemovePoint} onReplace={onReplacePoint} /></div> : null}
    {hasPoints ? <details className="route-result-tile route-leg-list"><summary>Переходы между точками</summary>{route.points.slice(0, -1).map((point, index) => <div key={`${point.place_id}-leg`} className="route-leg-row"><span>{index + 1} → {index + 2}</span><strong>{nextLegText(point)}</strong></div>)}</details> : null}
    <RouteCandidateOptions disabled={loading || sessionPending || Boolean(session && !sessionTerminal)} options={route.candidate_options} onAdd={onAddCandidate} />
  </section>
}
