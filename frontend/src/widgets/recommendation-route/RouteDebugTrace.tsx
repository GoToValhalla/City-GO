import type { RecommendationRouteResponse, RouteDebugTraceEntry } from '../../api/recommendations/recommendationRoute.types'

type Props = {
  route: RecommendationRouteResponse
}

const stageTitle: Record<string, string> = {
  assembly: 'Сборка маршрута',
  budget_fit: 'Подгонка под бюджет',
  candidate_retrieval: 'Поиск кандидатов',
  context_merge: 'Контекст запроса',
  hard_filter: 'Жёсткие фильтры',
  quality_annotation: 'Качество данных',
  route_quality_gate: 'Quality gate маршрута',
  scoring: 'Скоринг',
  time_aware: 'Проверка времени',
}

const diagnosticKeys = [
  'city_slug',
  'city_db_id',
  'start_point',
  'radius_meters',
  'places_total_in_city',
  'places_public_catalog',
  'places_route_visible',
  'places_route_eligible',
  'places_active_legacy_safe',
  'places_active_geocoded',
  'places_with_coords',
  'geo_query_count',
  'requested_budget_minutes',
  'effective_budget_minutes',
  'candidate_count',
  'filtered_count',
  'scored_count',
  'initial_route_count',
  'after_budget_fit_count',
  'final_route_count',
  'target_points',
  'min_points',
  'route_minutes',
  'budget_utilization_pct',
  'warnings',
]

const value = (entry: RouteDebugTraceEntry, keys: string[]): string => {
  const found = keys.map((key) => entry[key]).find((item) => item !== undefined && item !== null)
  if (found === undefined || found === null) return '—'
  if (typeof found === 'object') return JSON.stringify(found)
  return String(found)
}

const reasons = (entry: RouteDebugTraceEntry): string => {
  const raw = entry.reasons
  if (!raw || Object.keys(raw).length === 0) return '—'
  return Object.entries(raw).map(([key, count]) => `${key}: ${count}`).join(', ')
}

const diagnostics = (entry: RouteDebugTraceEntry): string => {
  const direct = diagnosticKeys
    .filter((key) => entry[key] !== undefined && entry[key] !== null)
    .reduce<Record<string, unknown>>((acc, key) => ({ ...acc, [key]: entry[key] }), {})

  const nested = typeof entry.diagnostics === 'object' && entry.diagnostics !== null ? entry.diagnostics : {}
  const payload = { ...nested, ...direct }

  return Object.keys(payload).length > 0 ? JSON.stringify(payload, null, 2) : ''
}

const stageByName = (trace: RouteDebugTraceEntry[], stage: string): RouteDebugTraceEntry | undefined => (
  trace.find((entry) => entry.stage === stage)
)

const shortJson = (payload: unknown): string => JSON.stringify(payload, null, 2)

const fullDebugPayload = (route: RecommendationRouteResponse): Record<string, unknown> => ({
  route_id: route.route_id,
  status: route.status,
  partial_reason: route.partial_reason,
  total_places: route.total_places,
  total_minutes: route.total_minutes,
  total_estimated_minutes: route.total_estimated_minutes,
  estimated_distance: route.estimated_distance,
  total_walk_distance_meters: route.total_walk_distance_meters,
  quality_score: route.quality_score,
  quality_status: route.quality_status,
  quality_breakdown: route.quality_breakdown,
  time_breakdown: route.time_breakdown,
  category_distribution: route.category_distribution,
  warnings: route.warnings,
  user_warnings: route.user_warnings,
  context: route.context,
  points: route.points.map((point) => ({
    place_id: point.place_id,
    title: point.title,
    category: point.category,
    lat: point.lat,
    lng: point.lng,
    visit_minutes: point.visit_minutes,
    estimated_walk_minutes: point.estimated_walk_minutes,
    estimated_distance_meters: point.estimated_distance_meters,
    scoring_breakdown: point.scoring_breakdown,
  })),
  candidate_options_count: route.candidate_options?.length ?? 0,
  candidate_options: route.candidate_options?.slice(0, 20).map((point) => ({
    place_id: point.place_id,
    title: point.title,
    category: point.category,
    lat: point.lat,
    lng: point.lng,
    visit_minutes: point.visit_minutes,
    estimated_walk_minutes: point.estimated_walk_minutes,
  })),
  debug_trace: route.debug_trace,
})

export const RouteDebugTrace = ({ route }: Props) => {
  const trace = route.debug_trace ?? []
  const retrieval = stageByName(trace, 'candidate_retrieval')
  const hardFilter = stageByName(trace, 'hard_filter')
  const scoring = stageByName(trace, 'scoring')
  const assembly = stageByName(trace, 'assembly')
  const budgetFit = stageByName(trace, 'budget_fit')
  const qualityGate = stageByName(trace, 'route_quality_gate')
  const rawPayload = fullDebugPayload(route)

  return (
    <details className="route-result-tile route-debug-trace" open>
      <summary>Debug маршрута — полный разбор</summary>

      <div className="route-debug-summary-grid">
        <div><span>Статус</span><strong>{route.status ?? '—'}</strong></div>
        <div><span>Точек</span><strong>{route.total_places}</strong></div>
        <div><span>Минут</span><strong>{route.total_estimated_minutes}</strong></div>
        <div><span>Кандидатов</span><strong>{value(retrieval ?? {}, ['count', 'candidate_count'])}</strong></div>
        <div><span>После фильтров</span><strong>{value(hardFilter ?? {}, ['kept_count'])}</strong></div>
        <div><span>Скоринг</span><strong>{value(scoring ?? {}, ['count', 'scored_count'])}</strong></div>
        <div><span>Assembly</span><strong>{value(assembly ?? {}, ['selected_count', 'initial_route_count'])}</strong></div>
        <div><span>Budget fit</span><strong>{value(budgetFit ?? {}, ['kept_count', 'after_budget_fit_count'])}</strong></div>
        <div><span>Итог</span><strong>{value(qualityGate ?? {}, ['final_route_count'])}</strong></div>
        <div><span>Budget %</span><strong>{value(qualityGate ?? {}, ['budget_utilization_pct'])}</strong></div>
      </div>

      {route.warnings?.length ? (
        <div className="route-debug-warning-box">
          <strong>Warnings из backend</strong>
          <pre>{shortJson(route.warnings)}</pre>
        </div>
      ) : null}

      <div className="route-debug-list">
        {trace.map((entry, index) => {
          const details = diagnostics(entry)
          return (
            <div className="route-debug-item" key={`${entry.stage}-${index}`}>
              <strong>{stageTitle[entry.stage] ?? entry.stage}</strong>
              <span>duration_ms: {value(entry, ['duration_ms'])}</span>
              <span>count: {value(entry, ['count', 'input_count', 'candidate_count'])}</span>
              <span>kept: {value(entry, ['kept_count', 'selected_count', 'final_route_count'])}</span>
              <span>removed: {value(entry, ['removed_count'])}</span>
              <span>warnings: {value(entry, ['warning_count'])}</span>
              <span>fallback: {value(entry, ['fallback_used'])}</span>
              <span>reasons: {reasons(entry)}</span>
              {details ? <pre>{details}</pre> : null}
            </div>
          )
        })}
      </div>

      <details className="route-debug-raw" open>
        <summary>Полный JSON ответа маршрута</summary>
        <pre>{shortJson(rawPayload)}</pre>
      </details>
    </details>
  )
}
