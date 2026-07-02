import { useMemo, useState } from 'react'
import type {
  RecommendationRoutePoint,
  RecommendationRouteResponse,
  RouteQualityStatus,
  UserRouteCorrectionAction,
} from '../../api/recommendations/recommendationRoute.types'
import { sendRouteFeedback } from '../../api/recommendations/recommendationRoute.api'
import { CheckCircle2, Clock, Map, Pause, Play, Plus, RefreshCw, ShieldCheck, SkipForward, Star, StopCircle, Wand2 } from 'lucide-react'
import { MapLibreMap } from '../../shared/map/MapLibreMap'
import type { MapPoint, MapRouteState } from '../../shared/map/mapTypes'
import { RouteCandidateOptions } from './RouteCandidateOptions'
import { RouteDataNotes } from './RouteDataNotes'
import { RouteDebugTrace } from './RouteDebugTrace'
import { RouteInsights } from './RouteInsights'
import { RoutePointList } from './RoutePointList'
import { RouteWarnings } from './RouteWarnings'
import { emptyCopy, emptyTitle, statusLabel } from './routeResultStatusText'
import { isDebugEnabled } from '../../shared/config/debug'

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
  failed: 'Не удалось собрать готовый маршрут. Измени параметры и попробуй снова.',
}

type ActiveRouteStatus = 'planned' | 'active' | 'paused' | 'completed' | 'abandoned'

type ActiveRouteSession = {
  status: ActiveRouteStatus
  currentIndex: number
  startedAt: string | null
  completedAt: string | null
  pointCompletedAt: Record<string, string>
}

type Props = {
  route: RecommendationRouteResponse
  loading: boolean
  onAddCandidate: (placeId: string) => void
  onCorrect: (action: UserRouteCorrectionAction, targetPlaceId?: string | null) => void
  onMovePoint?: (placeId: string, direction: 'up' | 'down') => void
  onRemovePoint?: (placeId: string) => void
  onReplacePoint?: (placeId: string) => void
}

const normalizeQualityStatus = (route: RecommendationRouteResponse): RouteQualityStatus => {
  const direct = route.quality_status
  if (direct === 'good' || direct === 'acceptable' || direct === 'weak' || direct === 'failed') return direct
  const breakdownStatus = route.quality_breakdown?.status
  if (breakdownStatus === 'good' || breakdownStatus === 'acceptable' || breakdownStatus === 'weak' || breakdownStatus === 'failed') return breakdownStatus
  if (route.status === 'no_route' || route.total_places === 0) return 'failed'
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
  return [{ id: Number.isFinite(parsedId) ? parsedId : index + 1, latitude, longitude, title: point.title?.trim() || `Точка ${index + 1}`, category: point.category, order: index + 1 }]
})

const formatMeters = (meters?: number | null): string => {
  if (!meters || meters <= 0) return 'дистанция уточняется'
  if (meters < 1000) return `${Math.round(meters)} м`
  return `${Math.round(meters / 100) / 10} км`
}

const nextLegText = (point: RecommendationRoutePoint): string => {
  const minutes = typeof point.estimated_walk_minutes === 'number' ? point.estimated_walk_minutes : null
  const distance = formatMeters(point.estimated_distance_meters)
  if (minutes === null || minutes <= 0) return distance
  return `${minutes} мин · ${distance}`
}

const initialSession = (): ActiveRouteSession => ({ status: 'planned', currentIndex: 0, startedAt: null, completedAt: null, pointCompletedAt: {} })

const RouteMapPreview = ({ points }: { points: RecommendationRoutePoint[] }) => {
  const mapPoints = useMemo(() => toMapPoints(points), [points])
  const [activePointId, setActivePointId] = useState<number | null>(null)
  const [walkingRoute, setWalkingRoute] = useState<MapRouteState | null>(null)
  const activePoint = mapPoints.find((point) => point.id === activePointId) ?? null

  if (mapPoints.length === 0) {
    return <div className="route-map-preview route-map-preview-empty"><strong>Карта появится после сборки маршрута</strong><span>Для визуализации нужны корректные координаты точек.</span></div>
  }

  return <div className="route-map-preview" aria-label="Карта маршрута">
    <MapLibreMap className="route-map-canvas" points={mapPoints} activePointId={activePointId} routeLine interactiveSelection={false} onPointSelect={setActivePointId} onRouteStateChange={setWalkingRoute} />
    <div className="route-map-caption" aria-live="polite">
      <strong>{activePoint ? `${activePoint.order}. ${activePoint.title}` : `${mapPoints.length} точек на маршруте`}</strong>
      <span>{activePoint ? 'Выбрана точка маршрута.' : walkingRoute?.status === 'routed' ? `Путь построен по пешеходным улицам: ${formatMeters(walkingRoute.distanceMeters)}.` : 'Строим безопасный пешеходный путь между точками.'}</span>
    </div>
  </div>
}

export const RouteResultPanel = ({ route, loading, onAddCandidate, onCorrect, onMovePoint, onRemovePoint, onReplacePoint }: Props) => {
  const [ratingStatus, setRatingStatus] = useState<string | null>(null)
  const [session, setSession] = useState<ActiveRouteSession>(initialSession)
  const summary = route.explanation?.summary ?? `Маршрут ${route.route_id}`
  const quality = route.quality_score ?? 0
  const qualityStatus = normalizeQualityStatus(route)
  const hasPoints = route.total_places > 0
  const isPartial = route.status === 'partial_route'
  const isEmpty = route.status === 'no_route' || !hasPoints || qualityStatus === 'failed'
  const walkKm = Math.round((route.total_walk_distance_meters ?? route.estimated_distance * 1000) / 100) / 10
  const reasons = Object.fromEntries((route.explanation?.points ?? []).map((point) => [point.place_id, point.reason]))
  const currentPoint = route.points[session.currentIndex] ?? null
  const nextPoint = route.points[session.currentIndex + 1] ?? null

  const rateRoute = async (rating: number) => {
    try {
      setRatingStatus('Сохраняю оценку...')
      await sendRouteFeedback(route, rating)
      setRatingStatus('Оценка сохранена. Будем учитывать в рекомендациях.')
    } catch (error) {
      console.error(error)
      setRatingStatus('Не удалось сохранить оценку')
    }
  }

  const startSession = () => setSession({ ...initialSession(), status: 'active', startedAt: new Date().toISOString() })
  const pauseSession = () => setSession((value) => ({ ...value, status: value.status === 'paused' ? 'active' : 'paused' }))
  const completePoint = () => setSession((value) => {
    const point = route.points[value.currentIndex]
    const completed = point ? { ...value.pointCompletedAt, [point.place_id]: new Date().toISOString() } : value.pointCompletedAt
    const isLast = value.currentIndex >= route.points.length - 1
    return { ...value, pointCompletedAt: completed, currentIndex: isLast ? value.currentIndex : value.currentIndex + 1, status: isLast ? 'completed' : 'active', completedAt: isLast ? new Date().toISOString() : value.completedAt }
  })
  const skipPoint = () => setSession((value) => ({ ...value, currentIndex: Math.min(route.points.length - 1, value.currentIndex + 1), status: 'active' }))
  const finishSession = () => setSession((value) => ({ ...value, status: 'completed', completedAt: new Date().toISOString() }))

  return <section className="route-result-grid route-result-grid-mobile-first">
    <div className="route-result-tile route-result-summary">
      <div className="route-result-top"><div>
        <p className="route-eyebrow">{statusLabel(route.status ?? 'ready')} · {QUALITY_LABELS[qualityStatus]}</p>
        <h2>{isEmpty ? emptyTitle(route.partial_reason) : summary}</h2>
      </div><strong className={`route-grade route-grade-${qualityStatus}`}><ShieldCheck size={18} />{Math.round(quality * 100)}%</strong></div>
      <p className={`route-quality-banner route-quality-${qualityStatus}`}>{QUALITY_COPY[qualityStatus]}</p>
      {isEmpty ? <p className="route-empty-copy">{emptyCopy(route.partial_reason)}</p> : null}
      {isPartial ? <p className="route-empty-copy">Маршрут слабый: нашли мало точек, но честно показываем результат и действия для улучшения.</p> : null}
      <div className="route-metrics route-metrics-primary">
        <span><Map size={16} /> {route.total_places} мест</span><span><Clock size={16} /> {route.total_estimated_minutes} мин</span>
        <span>{walkKm} км пешком</span><span>Качество {Math.round(quality * 100)}%</span>
      </div>
      <div className="route-main-actions">
        <button type="button" disabled={loading} onClick={() => onCorrect('rebuild_from_here')}><RefreshCw size={16} /> Пересобрать</button>
        <button type="button" disabled={loading} onClick={() => onCorrect('extend_route')}><Plus size={16} /> Добавить место</button>
        <button type="button" disabled={loading || !route.points[0]} onClick={() => route.points[0] && onReplacePoint?.(route.points[0].place_id)}><Wand2 size={16} /> Заменить точку</button>
        {hasPoints ? <button type="button" disabled={loading || session.status === 'active'} onClick={startSession}><Play size={16} /> Начать маршрут</button> : null}
      </div>
      <RouteInsights route={route} />
      <div className="route-correction-bar" aria-label="Оценка маршрута">{[1, 2, 3, 4, 5].map((rating) => (
        <button key={rating} type="button" disabled={loading} onClick={() => void rateRoute(rating)}><Star size={16} /> {rating}</button>
      ))}</div>
      {ratingStatus ? <p className="route-feedback-status">{ratingStatus}</p> : null}<RouteDataNotes route={route} />
    </div>
    <RouteWarnings route={route} />
    {hasPoints ? <div className="route-result-tile route-active-session"><h2>Активная прогулка</h2><p>{session.status === 'planned' ? 'Маршрут ещё не начат.' : session.status === 'completed' ? 'Маршрут завершён.' : session.status === 'paused' ? 'Маршрут на паузе.' : `Текущая точка: ${currentPoint?.title ?? 'следующая точка'}`}</p>{nextPoint ? <p className="route-muted">Дальше: {nextPoint.title ?? `точка ${session.currentIndex + 2}`}</p> : null}<div className="route-main-actions"><button type="button" disabled={!hasPoints || session.status === 'completed'} onClick={completePoint}><CheckCircle2 size={16} /> Я на месте</button><button type="button" disabled={!hasPoints || session.status === 'completed'} onClick={skipPoint}><SkipForward size={16} /> Пропустить</button><button type="button" disabled={!hasPoints || session.status === 'completed'} onClick={pauseSession}><Pause size={16} /> {session.status === 'paused' ? 'Продолжить' : 'Пауза'}</button><button type="button" disabled={!hasPoints || session.status === 'completed'} onClick={finishSession}><StopCircle size={16} /> Завершить маршрут</button></div></div> : null}
    {hasPoints ? <div className="route-result-tile route-map-tile"><h2>Карта</h2><RouteMapPreview points={route.points} /></div> : null}
    {isDebugEnabled() ? <RouteDebugTrace route={route} /> : null}
    {hasPoints ? <div className="route-result-tile"><h2>Куда идти</h2><RoutePointList disabled={loading} points={route.points} reasons={reasons} activePlaceId={currentPoint?.place_id ?? null} onMove={onMovePoint} onRemove={onRemovePoint} onReplace={onReplacePoint} /></div> : null}
    {hasPoints ? <details className="route-result-tile route-leg-list"><summary>Переходы между точками</summary>{route.points.slice(0, -1).map((point, index) => (
      <div key={`${point.place_id}-leg`} className="route-leg-row"><span>{index + 1} → {index + 2}</span><strong>{nextLegText(point)}</strong></div>
    ))}</details> : null}
    <RouteCandidateOptions disabled={loading} options={route.candidate_options} onAdd={onAddCandidate} />
  </section>
}
