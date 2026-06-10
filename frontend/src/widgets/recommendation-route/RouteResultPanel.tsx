import { useMemo, useState } from 'react'
import type {
  RecommendationRoutePoint,
  RecommendationRouteResponse,
  RouteQualityStatus,
  UserRouteCorrectionAction,
} from '../../api/recommendations/recommendationRoute.types'
import { sendRouteFeedback } from '../../api/recommendations/recommendationRoute.api'
import { Clock, Map, Plus, RefreshCw, Scissors, ShieldCheck, Star } from 'lucide-react'
import { RouteCandidateOptions } from './RouteCandidateOptions'
import { RouteDataNotes } from './RouteDataNotes'
import { RouteDebugTrace } from './RouteDebugTrace'
import { RouteInsights } from './RouteInsights'
import { RoutePointList } from './RoutePointList'
import { RouteWarnings } from './RouteWarnings'
import { emptyCopy, emptyTitle, statusLabel } from './routeResultStatusText'

const QUALITY_LABELS: Record<RouteQualityStatus, string> = {
  good: 'Хороший маршрут',
  acceptable: 'Нормальный маршрут',
  weak: 'Слабый маршрут',
  failed: 'Маршрут не собран',
}

const QUALITY_COPY: Record<RouteQualityStatus, string> = {
  good: 'Точки, расстояния и данные выглядят сбалансированно.',
  acceptable: 'Маршрут можно пройти, но есть небольшие компромиссы.',
  weak: 'Маршрут показываем, но лучше проверить предупреждения и точки.',
  failed: 'Не удалось собрать готовый маршрут. Измени параметры и попробуй снова.',
}

type Props = {
  route: RecommendationRouteResponse
  loading: boolean
  onAddCandidate: (placeId: string) => void
  onCorrect: (action: UserRouteCorrectionAction) => void
}

type MapPoint = RecommendationRoutePoint & { x: number; y: number }

const normalizeQualityStatus = (route: RecommendationRouteResponse): RouteQualityStatus => {
  const direct = route.quality_status
  if (direct === 'good' || direct === 'acceptable' || direct === 'weak' || direct === 'failed') return direct
  const breakdownStatus = route.quality_breakdown?.status
  if (breakdownStatus === 'good' || breakdownStatus === 'acceptable' || breakdownStatus === 'weak' || breakdownStatus === 'failed') {
    return breakdownStatus
  }
  if (route.status === 'no_route' || route.total_places === 0) return 'failed'
  if ((route.quality_score ?? 0) >= 0.75) return 'good'
  if ((route.quality_score ?? 0) >= 0.5) return 'acceptable'
  return 'weak'
}

const normalizePointsForMap = (points: RecommendationRoutePoint[]): MapPoint[] => {
  const valid = points.filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng))
  if (valid.length === 0) return []

  const minLat = Math.min(...valid.map((point) => point.lat))
  const maxLat = Math.max(...valid.map((point) => point.lat))
  const minLng = Math.min(...valid.map((point) => point.lng))
  const maxLng = Math.max(...valid.map((point) => point.lng))
  const latSpan = Math.max(maxLat - minLat, 0.00001)
  const lngSpan = Math.max(maxLng - minLng, 0.00001)

  return valid.map((point) => ({
    ...point,
    x: 8 + ((point.lng - minLng) / lngSpan) * 84,
    y: 92 - ((point.lat - minLat) / latSpan) * 84,
  }))
}

const routePath = (points: MapPoint[]): string => points
  .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
  .join(' ')

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
  const mapPoints = useMemo(() => normalizePointsForMap(points), [points])
  const path = routePath(mapPoints)

  if (mapPoints.length === 0) {
    return (
      <div className="route-map-preview route-map-preview-empty">
        <strong>Карта появится после сборки маршрута</strong>
        <span>Для визуализации нужны координаты точек.</span>
      </div>
    )
  }

  return (
    <div className="route-map-preview" aria-label="Карта маршрута">
      <svg viewBox="0 0 100 100" role="img" aria-label="Линия маршрута и точки">
        <defs>
          <pattern id="route-grid" width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,.12)" strokeWidth=".4" />
          </pattern>
        </defs>
        <rect width="100" height="100" rx="4" fill="url(#route-grid)" />
        {mapPoints.length > 1 ? <path d={path} className="route-map-line" /> : null}
        {mapPoints.map((point, index) => (
          <g key={`${point.place_id}-${index}`} transform={`translate(${point.x} ${point.y})`}>
            <circle r="4.6" className="route-map-marker" />
            <text textAnchor="middle" dominantBaseline="central" className="route-map-marker-text">{index + 1}</text>
          </g>
        ))}
      </svg>
      <div className="route-map-caption">
        <strong>{mapPoints.length} точек на маршруте</strong>
        <span>Линия показывает порядок прохождения. Точный путь можно открыть в навигаторе из карточки точки.</span>
      </div>
    </div>
  )
}

export const RouteResultPanel = ({ route, loading, onAddCandidate, onCorrect }: Props) => {
  const [ratingStatus, setRatingStatus] = useState<string | null>(null)
  const summary = route.explanation.summary ?? `Маршрут ${route.route_id}`
  const quality = route.quality_score ?? 0
  const qualityStatus = normalizeQualityStatus(route)
  const hasPoints = route.total_places > 0
  const isPartial = route.status === 'partial_route'
  const isEmpty = route.status === 'no_route' || !hasPoints || qualityStatus === 'failed'
  const walkKm = Math.round((route.total_walk_distance_meters ?? route.estimated_distance * 1000) / 100) / 10
  const reasons = Object.fromEntries(
    (route.explanation.points ?? []).map((point) => [point.place_id, point.reason]),
  )

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

  return (
    <section className="route-result-grid">
      <div className="route-result-tile route-result-summary">
        <div className="route-result-top">
          <div>
            <p className="route-eyebrow">{statusLabel(route.status ?? 'ready')} · {QUALITY_LABELS[qualityStatus]}</p>
            <h2>{isEmpty ? emptyTitle(route.partial_reason) : summary}</h2>
          </div>
          <strong className={`route-grade route-grade-${qualityStatus}`}><ShieldCheck size={18} />{Math.round(quality * 100)}%</strong>
        </div>
        <p className={`route-quality-banner route-quality-${qualityStatus}`}>{QUALITY_COPY[qualityStatus]}</p>
        {isEmpty ? <p className="route-empty-copy">{emptyCopy(route.partial_reason)}</p> : null}
        {isPartial ? <p className="route-empty-copy">Нашли мало точек, но показываем то, что уже можно пройти.</p> : null}
        <div className="route-metrics">
          <span><Map size={16} /> {route.total_places} мест</span>
          <span><Clock size={16} /> {route.total_estimated_minutes} мин</span>
          <span>{walkKm} км пешком</span>
          {route.has_warnings ? <span>{route.warning_count} нюанс.</span> : null}
        </div>
        <RouteInsights route={route} />
        {hasPoints ? <div className="route-correction-bar">
          <button type="button" disabled={loading} onClick={() => onCorrect('shorten_route')}><Scissors size={16} /> Короче</button>
          <button type="button" disabled={loading} onClick={() => onCorrect('extend_route')}><Plus size={16} /> Добавить место</button>
          <button type="button" disabled={loading} onClick={() => onCorrect('rebuild_from_here')}><RefreshCw size={16} /> Перестроить</button>
        </div> : null}
        <div className="route-correction-bar" aria-label="Оценка маршрута">
          {[1, 2, 3, 4, 5].map((rating) => (
            <button key={rating} type="button" disabled={loading} onClick={() => void rateRoute(rating)}><Star size={16} /> {rating}</button>
          ))}
        </div>
        {ratingStatus ? <p className="route-feedback-status">{ratingStatus}</p> : null}
        <RouteDataNotes route={route} />
      </div>
      <RouteWarnings route={route} />
      {hasPoints ? <div className="route-result-tile"><h2>Карта маршрута</h2><RouteMapPreview points={route.points} /></div> : null}
      <RouteDebugTrace trace={route.debug_trace} />
      {hasPoints ? <div className="route-result-tile"><h2>Точки маршрута</h2><RoutePointList points={route.points} reasons={reasons} /></div> : null}
      {hasPoints ? <div className="route-result-tile route-leg-list"><h2>Переходы между точками</h2>{route.points.slice(0, -1).map((point, index) => (
        <div key={`${point.place_id}-leg`} className="route-leg-row">
          <span>{index + 1} → {index + 2}</span>
          <strong>{nextLegText(point)}</strong>
        </div>
      ))}</div> : null}
      <RouteCandidateOptions disabled={loading} options={route.candidate_options} onAdd={onAddCandidate} />
    </section>
  )
}
