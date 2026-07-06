import { useMemo, useState } from 'react'
import type {
  ActiveRouteSession,
  RecommendationRoutePoint,
  RecommendationRouteResponse,
  RouteQualityStatus,
  UserRouteCorrectionAction,
} from '../../api/recommendations/recommendationRoute.types'
import { sendRouteFeedback, startActiveRouteSession, updateActiveRouteSession } from '../../api/recommendations/recommendationRoute.api'
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
import { DiagnosticsPanel } from '../../shared/debug/DiagnosticsPanel'

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

const RouteMapPreview = ({ points }: { points: RecommendationRoutePoint[] }) => {
  const mapPoints = useMemo(() => toMapPoints(points), [points])
  const [activePointId, setActivePointId] = useState<number | null>(null)
  const [walkingRoute, setWalkingRoute] = useState<MapRouteState | null>(null)
  const activePoint = mapPoints.find((point) => point.id === activePointId) ?? null

  if (mapPoints.length === 0) return <div className="route-map-preview route-map-preview-empty"><strong>Карта появится после сборки маршрута</strong><span>Для визуализации нужны корректные координаты точек.</span></div>

  return <div className="route-map-preview" aria-label="Карта маршрута">
    <MapLibreMap className="route-map-canvas" points={mapPoints} activePointId={activePointId} routeLine interactiveSelection={false} onPointSelect={setActivePointId} onRouteStateChange={setWalkingRoute} />
    <div className="route-map-caption" aria-live="polite"><strong>{activePoint ? `${activePoint.order}. ${activePoint.title}` : `${mapPoints.length} точек на маршруте`}</strong><span>{activePoint ? 'Выбрана точка маршрута.' : walkingRoute?.status === 'routed' ? `Путь построен по пешеходным улицам: ${formatMeters(walkingRoute.distanceMeters)}.` : 'Строим безопасный пешеходный путь между точками.'}</span></div>
  </div>
}

export const RouteResultPanel = ({ route, loading, onAddCandidate, onCorrect, onMovePoint, onRemovePoint, onReplacePoint }: Props) => {
  const [ratingStatus, setRatingStatus] = useState<string | null>(null)
  const [session, setSession] = useState<ActiveRouteSession | null>(null)
  const [sessionStatus, setSessionStatus] = useState<string | null>(null)
  const summary = route.explanation?.summary ?? `Маршрут ${route.route_id}`
  const quality = route.quality_score ?? 0
  const qualityStatus = normalizeQualityStatus(route)
  const hasPoints = route.total_places > 0
  const meaningfulRoute = route.points.length >= 2
  const isPartial = route.status === 'partial_route'
  const isEmpty = route.status === 'no_route' || !hasPoints || qualityStatus === 'failed'
  const debug = isDebugEnabled()
  const walkKm = Math.round((route.total_walk_distance_meters ?? route.estimated_distance * 1000) / 100) / 10
  const reasons = Object.fromEntries((route.explanation?.points ?? []).map((point) => [point.place_id, point.reason]))
  const currentPlaceId = session?.current_place_id ?? route.points[0]?.place_id ?? null
  const currentPoint = route.points.find((point) => point.place_id === currentPlaceId) ?? route.points[0] ?? null
  const nextPoint = session?.next_place_id ? route.points.find((point) => point.place_id === session.next_place_id) ?? null : route.points[1] ?? null
  const sessionTerminal = session?.status === 'completed' || session?.status === 'abandoned'

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

  const startSession = async () => {
    try {
      setSessionStatus('Запускаю маршрут...')
      const nextSession = await startActiveRouteSession(route)
      setSession(nextSession)
      setSessionStatus('Маршрут начат.')
    } catch (error) {
      console.error(error)
      setSessionStatus('Не удалось начать маршрут.')
    }
  }

  const applySessionAction = async (action: 'complete_point' | 'skip_point' | 'pause' | 'resume' | 'finish', placeId?: string | null) => {
    if (!session) {
      await startSession()
      return
    }
    try {
      setSessionStatus('Обновляю прогулку...')
      const nextSession = await updateActiveRouteSession(session.session_id, action, placeId ?? currentPlaceId)
      setSession(nextSession)
      setSessionStatus('Прогулка обновлена.')
    } catch (error) {
      console.error(error)
      setSessionStatus('Не удалось обновить прогулку.')
    }
  }

  const sessionCopy = !session ? 'Маршрут ещё не начат.' : session.status === 'completed' ? 'Маршрут завершён.' : session.status === 'paused' ? 'Маршрут на паузе.' : `Текущая точка: ${currentPoint?.title ?? 'следующая точка'}`

  return <section className="route-result-grid route-result-grid-mobile-first">
    <div className="route-result-tile route-result-summary">
      <div className="route-result-top"><div><p className="route-eyebrow">{statusLabel(route.status ?? 'ready')} · {meaningfulRoute ? QUALITY_LABELS[qualityStatus] : 'Одна точка для старта'}</p><h2>{!meaningfulRoute && hasPoints ? 'Пока мало данных для прогулки' : isEmpty ? emptyTitle(route.partial_reason) : summary}</h2></div>{debug ? <strong className={`route-grade route-grade-${qualityStatus}`}><ShieldCheck size={18} />{Math.round(quality * 100)}%</strong> : null}</div>
      <p className={`route-quality-banner route-quality-${qualityStatus}`}>{!meaningfulRoute && hasPoints ? 'Нашли одну полезную точку. Для полноценной прогулки нужно больше подходящих мест рядом.' : QUALITY_COPY[qualityStatus]}</p>
      {isEmpty ? <p className="route-empty-copy">{emptyCopy(route.partial_reason)}</p> : null}
      {isPartial ? <p className="route-empty-copy">Маршрут слабый: нашли мало точек, но честно показываем результат и действия для улучшения.</p> : null}
      <div className="route-metrics route-metrics-primary"><span><Map size={16} /> {route.total_places} мест</span><span><Clock size={16} /> {route.total_estimated_minutes} мин</span><span>{walkKm} км пешком</span>{debug ? <span>Качество {Math.round(quality * 100)}%</span> : null}</div>
      <div className="route-main-actions"><button type="button" disabled={loading} onClick={() => onCorrect('rebuild_from_here')}><RefreshCw size={16} /> Пересобрать</button><button type="button" disabled={loading} onClick={() => onCorrect('extend_route')}><Plus size={16} /> Добавить место</button><button type="button" disabled={loading || !route.points[0]} onClick={() => route.points[0] && onReplacePoint?.(route.points[0].place_id)}><Wand2 size={16} /> Заменить точку</button>{hasPoints ? <button type="button" disabled={loading || !meaningfulRoute || session?.status === 'active'} onClick={() => void startSession()}><Play size={16} /> Начать маршрут</button> : null}</div>
      <RouteInsights route={route} />
      <div className="route-correction-bar" aria-label="Оценка маршрута">{[1, 2, 3, 4, 5].map((rating) => <button key={rating} type="button" disabled={loading} onClick={() => void rateRoute(rating)}><Star size={16} /> {rating}</button>)}</div>
      {ratingStatus ? <p className="route-feedback-status">{ratingStatus}</p> : null}<RouteDataNotes route={route} />
    </div>
    <RouteWarnings route={route} />
    {hasPoints ? <div className="route-result-tile route-active-session"><h2>Активная прогулка</h2><p>{sessionCopy}</p>{nextPoint ? <p className="route-muted">Дальше: {nextPoint.title ?? 'следующая точка'}</p> : null}{sessionStatus ? <p className="route-start-note">{sessionStatus}</p> : null}<div className="route-main-actions"><button type="button" disabled={!hasPoints || sessionTerminal} onClick={() => void applySessionAction('complete_point')}><CheckCircle2 size={16} /> Я на месте</button><button type="button" disabled={!hasPoints || sessionTerminal} onClick={() => void applySessionAction('skip_point')}><SkipForward size={16} /> Пропустить</button><button type="button" disabled={!hasPoints || sessionTerminal} onClick={() => void applySessionAction(session?.status === 'paused' ? 'resume' : 'pause')}><Pause size={16} /> {session?.status === 'paused' ? 'Продолжить' : 'Пауза'}</button><button type="button" disabled={!hasPoints || sessionTerminal} onClick={() => void applySessionAction('finish')}><StopCircle size={16} /> Завершить маршрут</button></div></div> : null}
    {hasPoints ? <div className="route-result-tile route-map-tile"><h2>Карта</h2><RouteMapPreview points={route.points} /></div> : null}
    <DiagnosticsPanel compact={!debug} payload={{ screen: 'route', category: 'route', severity: route.user_warnings?.length ? 'warning' : 'info', city_slug: route.city_slug, request_id: route.request_id, route_id: route.route_id, title: 'Route diagnostics', summary: `${route.points.length} точек · ${route.user_warnings?.length ?? 0} предупреждений`, warnings: route.user_warnings ?? [], debug_trace: route.debug_trace, response_summary: { quality_score: route.quality_score, total_places: route.total_places, status: route.status } }} details={route} />
    {debug ? <RouteDebugTrace route={route} /> : null}
    {hasPoints ? <div className="route-result-tile"><h2>Куда идти</h2><RoutePointList disabled={loading} points={route.points} reasons={reasons} activePlaceId={currentPlaceId} onMove={onMovePoint} onRemove={onRemovePoint} onReplace={onReplacePoint} /></div> : null}
    {hasPoints ? <details className="route-result-tile route-leg-list"><summary>Переходы между точками</summary>{route.points.slice(0, -1).map((point, index) => <div key={`${point.place_id}-leg`} className="route-leg-row"><span>{index + 1} → {index + 2}</span><strong>{nextLegText(point)}</strong></div>)}</details> : null}
    <RouteCandidateOptions disabled={loading} options={route.candidate_options} onAdd={onAddCandidate} />
  </section>
}
