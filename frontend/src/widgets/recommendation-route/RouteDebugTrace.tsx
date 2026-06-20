import type { RecommendationRouteResponse, RouteDebugTraceEntry } from '../../api/recommendations/recommendationRoute.types'

type Props = {
  route: RecommendationRouteResponse
}

const emptyTraceEntry: RouteDebugTraceEntry = { stage: 'empty' }

const stageTitle: Record<string, string> = {
  assembly: 'Сборка маршрута',
  budget_fit: 'Подгонка под бюджет',
  candidate_retrieval: 'Поиск кандидатов',
  context_merge: 'Контекст запроса',
  hard_filter: 'Жёсткие фильтры',
  hard_filtering: 'Жёсткие фильтры',
  interest_matching: 'Совпадения интересов',
  pool_expansion: 'Расширение пула',
  quality_annotation: 'Качество данных',
  quality_gates: 'Quality gates маршрута',
  adaptive_plan: 'Адаптивный план',
  finalize: 'Финализация',
  final_response: 'Финальный ответ',
  context_normalization: 'Нормализация контекста',
  route_quality_gate: 'Quality gate маршрута',
  retrieval: 'Retrieval',
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
  'geo_route_eligible_count',
  'candidate_retrieval_expected_count',
  'candidate_retrieval_city_wide_expected_count',
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

const debugBlocks = [
  ['context', 'Контекст'],
  ['city_stats', 'Статистика города'],
  ['retrieval', 'Retrieval'],
  ['candidate_retrieval', 'Candidate retrieval raw'],
  ['quality_annotation', 'Quality annotation'],
  ['hard_filters', 'Hard filters'],
  ['interest_matching', 'Interest matching'],
  ['adaptive_plan', 'Adaptive plan'],
  ['pool_expansion', 'Pool expansion'],
  ['scoring', 'Scoring'],
  ['assembly', 'Assembly'],
  ['time_ordering', 'Time ordering'],
  ['time_aware', 'Time aware'],
  ['budget_fit', 'Budget fit'],
  ['quality_gates', 'Quality gates'],
  ['finalize', 'Finalize'],
  ['final', 'Final'],
] as const

const blockFields: Record<string, string[]> = {
  context: ['city_id', 'start_lat', 'start_lng', 'radius_meters', 'time_budget_minutes', 'route_time_mode', 'time_of_day', 'interests', 'interest_removed_due_to_avoidance', 'avoided_categories', 'excluded_place_ids', 'budget_level', 'pace_mode'],
  city_stats: ['places_total_in_city', 'places_public_catalog', 'places_route_eligible', 'places_active_legacy_safe', 'places_with_coords'],
  retrieval: ['input_city_id', 'requested_radius_meters', 'query_limit', 'healthy_min_candidates', 'raw_candidates_count', 'after_radius_count', 'expanded_radius_candidates_count', 'city_wide_candidates_count', 'retrieval_strategy_used', 'retrieval_coverage_pct', 'low_coverage_threshold_pct', 'after_city_filter_count', 'after_route_eligible_count', 'after_public_catalog_count', 'after_coordinates_count', 'after_excluded_place_ids_count', 'after_avoided_categories_count', 'final_candidates_count', 'fallback_city_wide_used', 'fallback_radius_used', 'center_used', 'places_within_500m', 'places_within_1km', 'places_within_2km', 'places_within_5km', 'places_within_10km', 'city_wide_eligible', 'spatial_density', 'top_candidate_distances_meters', 'sample_candidate_ids'],
  candidate_retrieval: ['count', 'city_slug', 'city_db_id', 'city_launch_status', 'city_is_active', 'city_is_blocked_for_routes', 'start_point', 'radius_meters', 'places_total_in_city', 'places_public_catalog', 'places_route_visible', 'places_route_eligible', 'places_active_legacy_safe', 'places_with_coords', 'geo_query_count', 'geo_route_eligible_count', 'candidate_retrieval_expected_count', 'candidate_retrieval_city_wide_expected_count', 'categories', 'sample_candidates'],
  quality_annotation: ['input_count', 'output_count', 'warning_count', 'validation_issue_counts', 'sample_candidates', 'warnings'],
  hard_filters: ['input_count', 'strict_kept', 'relaxed_kept', 'fallback_used', 'output_count', 'removed_count', 'removal_reasons', 'strict_removal_reasons', 'relaxed_removal_reasons', 'sample_removed'],
  interest_matching: ['input_count', 'requested_interests', 'interest_removed_due_to_avoidance', 'exact_count', 'exact_matches_count', 'related_matches_count', 'neutral_candidates_count', 'expansion_level', 'expanded_category_count', 'neutral_added_count', 'target_points', 'output_count', 'sample_exact_ids', 'sample_related_ids', 'sample_neutral_ids'],
  adaptive_plan: ['input_count', 'output_count', 'target_points', 'expansion_level', 'exact_count', 'related_count', 'neutral_count', 'expanded_category_count', 'neutral_added_count', 'user_explanation', 'warnings'],
  pool_expansion: ['input_count', 'output_count', 'expansion_level', 'expanded_category_count', 'neutral_added_count', 'target_points', 'warnings'],
  scoring: ['input_count', 'output_count', 'min_score', 'max_score', 'avg_score', 'top_scored_candidates'],
  assembly: ['input_count', 'input_scored_count', 'target_points', 'selected_count', 'selected_count_before_budget', 'rejected_count', 'rejection_reasons', 'selected_ids', 'fallback_used', 'fallback_triggers', 'rejected_sample', 'first_point_candidates_checked', 'first_point_rejection_reasons', 'failure_reason'],
  time_ordering: ['input_count', 'output_count', 'input_route', 'output_route'],
  time_aware: ['input_count', 'output_count', 'removed_count', 'route_minutes', 'input_route', 'output_route'],
  budget_fit: ['input_count', 'output_count', 'requested_budget_minutes', 'actual_duration_minutes', 'route_completeness', 'removed_by_budget_count', 'removed_by_budget_sample', 'failure_reason'],
  quality_gates: ['status', 'warnings', 'failed_gates', 'user_explanation'],
  finalize: ['input_count', 'final_places_count', 'final_total_minutes', 'final_total_km', 'partial_reason', 'warning_count', 'warnings', 'final_points'],
  final: ['final_points_count', 'final_duration_minutes', 'final_distance_km', 'final_place_ids', 'failure_stage'],
}

const value = (entry: RouteDebugTraceEntry, keys: string[]): string => {
  const found = keys.map((key) => entry[key]).find((item) => item !== undefined && item !== null)
  if (found === undefined || found === null) return '—'
  if (typeof found === 'object') return JSON.stringify(found)
  return String(found)
}

const rawValue = (entry: RouteDebugTraceEntry, keys: string[]): unknown => (
  keys.map((key) => entry[key]).find((item) => item !== undefined && item !== null)
)

const numberValue = (entry: RouteDebugTraceEntry, keys: string[]): number | null => {
  const raw = rawValue(entry, keys)
  return typeof raw === 'number' ? raw : null
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

const blockPayload = (entry: RouteDebugTraceEntry, fields: string[]): Record<string, unknown> => (
  fields.reduce<Record<string, unknown>>((acc, key) => ({ ...acc, [key]: entry[key] ?? null }), {})
)

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
  route_quality_status: route.route_quality_status,
  route_completeness: route.route_completeness,
  matched_interest_count: route.matched_interest_count,
  total_requested_interests: route.total_requested_interests,
  expansion_level: route.expansion_level,
  neutral_added_count: route.neutral_added_count,
  fallback_level: route.fallback_level,
  user_explanation: route.user_explanation,
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

const retrievalDiagnosis = (retrieval: RouteDebugTraceEntry, candidateRetrieval: RouteDebugTraceEntry): Record<string, unknown> => {
  const finalCandidates = numberValue(retrieval, ['final_candidates_count', 'count']) ?? numberValue(candidateRetrieval, ['count'])
  const cityWideExpected = numberValue(candidateRetrieval, ['candidate_retrieval_city_wide_expected_count', 'places_route_eligible'])
  const radiusExpected = numberValue(candidateRetrieval, ['candidate_retrieval_expected_count', 'geo_route_eligible_count', 'geo_query_count'])
  const routeVisible = numberValue(candidateRetrieval, ['places_route_visible'])
  const status = finalCandidates === 0 && (cityWideExpected ?? 0) > 0
    ? 'CRITICAL: city-wide candidates exist, but retrieval returned 0'
    : finalCandidates === 0 && (routeVisible ?? 0) > 0
      ? 'CRITICAL: route-visible places exist, but retrieval returned 0'
      : finalCandidates !== null && finalCandidates < 40
        ? 'LOW: retrieval returned less than healthy threshold'
        : 'OK'

  return {
    status,
    final_candidates: finalCandidates,
    radius_expected: radiusExpected,
    city_wide_expected: cityWideExpected,
    route_visible: routeVisible,
    radius_meters: value(candidateRetrieval, ['radius_meters']),
    start_point: rawValue(candidateRetrieval, ['start_point']),
    retrieval_stage: value(retrieval, ['retrieval_strategy_used']),
    fallback_radius_used: rawValue(retrieval, ['fallback_radius_used']),
    fallback_city_wide_used: rawValue(retrieval, ['fallback_city_wide_used']),
    sample_candidate_ids: rawValue(retrieval, ['sample_candidate_ids']),
  }
}

export const RouteDebugTrace = ({ route }: Props) => {
  const trace = route.debug_trace ?? []
  const retrieval = stageByName(trace, 'retrieval') ?? stageByName(trace, 'candidate_retrieval') ?? emptyTraceEntry
  const candidateRetrieval = stageByName(trace, 'candidate_retrieval') ?? emptyTraceEntry
  const hardFilter = stageByName(trace, 'hard_filters') ?? stageByName(trace, 'hard_filter') ?? emptyTraceEntry
  const scoring = stageByName(trace, 'scoring') ?? emptyTraceEntry
  const assembly = stageByName(trace, 'assembly') ?? emptyTraceEntry
  const budgetFit = stageByName(trace, 'budget_fit') ?? emptyTraceEntry
  const qualityGate = stageByName(trace, 'quality_gates') ?? stageByName(trace, 'route_quality_gate') ?? emptyTraceEntry
  const rawPayload = fullDebugPayload(route)
  const retrievalDeathCheck = retrievalDiagnosis(retrieval, candidateRetrieval)

  return (
    <details className="route-result-tile route-debug-trace" open>
      <summary>Debug маршрута — полный разбор</summary>

      <div className="route-debug-warning-box">
        <strong>Retrieval death check</strong>
        <pre>{shortJson(retrievalDeathCheck)}</pre>
      </div>

      <div className="route-debug-summary-grid">
        <div><span>Статус</span><strong>{route.status ?? '—'}</strong></div>
        <div><span>Точек</span><strong>{route.total_places}</strong></div>
        <div><span>Минут</span><strong>{route.total_estimated_minutes}</strong></div>
        <div><span>Кандидатов</span><strong>{value(retrieval, ['final_candidates_count', 'count', 'candidate_count'])}</strong></div>
        <div><span>City-wide expected</span><strong>{value(candidateRetrieval, ['candidate_retrieval_city_wide_expected_count'])}</strong></div>
        <div><span>Radius expected</span><strong>{value(candidateRetrieval, ['candidate_retrieval_expected_count', 'geo_route_eligible_count'])}</strong></div>
        <div><span>После фильтров</span><strong>{value(hardFilter, ['output_count', 'kept_count'])}</strong></div>
        <div><span>Скоринг</span><strong>{value(scoring, ['count', 'scored_count'])}</strong></div>
        <div><span>Assembly</span><strong>{value(assembly, ['selected_count', 'initial_route_count'])}</strong></div>
        <div><span>Budget fit</span><strong>{value(budgetFit, ['kept_count', 'after_budget_fit_count'])}</strong></div>
        <div><span>Итог</span><strong>{value(qualityGate, ['final_route_count'])}</strong></div>
        <div><span>Budget %</span><strong>{value(qualityGate, ['budget_utilization_pct'])}</strong></div>
        <div><span>Route quality</span><strong>{route.route_quality_status ?? '—'}</strong></div>
        <div><span>Expansion</span><strong>{route.expansion_level ?? '—'}</strong></div>
      </div>

      {route.warnings?.length ? (
        <div className="route-debug-warning-box">
          <strong>Warnings из backend</strong>
          <pre>{shortJson(route.warnings)}</pre>
        </div>
      ) : null}

      <div className="route-debug-list">
        {debugBlocks.map(([stage, title]) => {
          const entry = stageByName(trace, stage) ?? { stage }
          return (
            <div className="route-debug-item" key={`canonical-${stage}`}>
              <strong>{title}</strong>
              <pre>{shortJson(blockPayload(entry, blockFields[stage] ?? []))}</pre>
            </div>
          )
        })}
      </div>

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
