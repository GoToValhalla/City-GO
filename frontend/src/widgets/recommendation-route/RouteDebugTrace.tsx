import type { RecommendationRouteResponse, RouteDebugTraceEntry } from '../../api/recommendations/recommendationRoute.types'

type Props = {
  route: RecommendationRouteResponse
}

type DebugRow = {
  label: string
  value: unknown
}

type MatrixRow = {
  step: string
  status: string
  signal: string
  action: string
}

const emptyTraceEntry: RouteDebugTraceEntry = { stage: 'empty' }

const STAGE_ORDER = [
  'context_merge',
  'context_normalization',
  'retrieval',
  'candidate_retrieval',
  'quality_annotation',
  'hard_filters',
  'hard_filter',
  'hard_filtering',
  'scoring_raw',
  'scoring',
  'interest_matching',
  'adaptive_plan',
  'assembly_input_debug',
  'assembly',
  'time_ordering',
  'time_aware',
  'budget_fit_first',
  'budget_gap_fill',
  'budget_fit',
  'quality_gates',
  'finalize',
  'final',
  'final_response',
]

const IMPORTANT_TRACE_KEYS = new Set([
  'stage',
  'status',
  'duration_ms',
  'city_id',
  'city_slug',
  'city_db_id',
  'city_launch_status',
  'city_is_active',
  'city_is_blocked_for_routes',
  'start_point',
  'location',
  'radius_meters',
  'requested_radius_meters',
  'expanded_radius_meters',
  'route_time_mode',
  'time_of_day',
  'interests',
  'avoided_categories',
  'interest_removed_due_to_avoidance',
  'warnings',
  'failure_stage',
  'failure_reason',
  'partial_reason',
  'input_count',
  'output_count',
  'count',
  'kept_count',
  'removed_count',
  'selected_count',
  'selected_count_before_budget',
  'input_scored_count',
  'target_points',
  'warning_count',
  'places_total_in_city',
  'places_public_catalog',
  'places_route_visible',
  'places_route_eligible',
  'places_with_coords',
  'geo_query_count',
  'geo_route_eligible_count',
  'candidate_retrieval_expected_count',
  'candidate_retrieval_city_wide_expected_count',
  'raw_candidates_count',
  'after_radius_count',
  'expanded_radius_candidates_count',
  'city_wide_candidates_count',
  'route_visible_candidates_count',
  'final_candidates_count',
  'retrieval_strategy_used',
  'fallback_used',
  'fallback_radius_used',
  'fallback_city_wide_used',
  'fallback_route_visible_used',
  'route_eligible_before_user_exclusions',
  'route_eligible_after_user_exclusions',
  'radius_before_user_exclusions',
  'radius_after_user_exclusions',
  'expanded_radius_before_user_exclusions',
  'expanded_radius_after_user_exclusions',
  'city_wide_after_user_exclusions',
  'route_visible_city_wide_after_user_exclusions',
  'route_visible_radius_after_user_exclusions',
  'retrieval_loss_summary',
  'final_candidate_categories',
  'sample_candidate_ids',
  'top_candidate_distances_meters',
  'strict_kept_count',
  'relaxed_kept_count',
  'reasons',
  'removal_reasons',
  'strict_removal_reasons',
  'relaxed_removal_reasons',
  'exact_count',
  'related_count',
  'neutral_count',
  'expansion_level',
  'expanded_category_count',
  'neutral_added_count',
  'route_minutes',
  'actual_duration_minutes',
  'requested_budget_minutes',
  'requested_time_budget_minutes',
  'target_minutes',
  'target_time_minutes',
  'hard_budget_minutes',
  'hard_time_budget_minutes',
  'budget_kind',
  'budget_unit',
  'before_fill_count',
  'after_fill_count',
  'route_completeness',
  'route_quality_status',
  'fallback_level',
  'failed_gates',
  'final_points_count',
  'final_places_count',
  'final_duration_minutes',
  'final_total_minutes',
  'final_place_ids',
])

const stageTitles: Record<string, string> = {
  context_merge: '1. Context Merge',
  context_normalization: '1.1. Context Conflicts',
  retrieval: '2. Retrieval Summary',
  candidate_retrieval: '2.1. Candidate Retrieval',
  quality_annotation: '2.2. Candidate Quality',
  hard_filters: '3. Hard Filters',
  hard_filter: '3.1. Hard Filter Report',
  hard_filtering: '3.2. Hard Filter Reasons',
  scoring_raw: '4. Raw Scoring',
  scoring: '4.1. Scoring Summary',
  interest_matching: '5. Interest Matching',
  adaptive_plan: '6. Adaptive Plan',
  assembly_input_debug: '7. Assembly Input',
  assembly: '7.1. Assembly',
  time_ordering: '8. Time Ordering',
  time_aware: '8.1. Time Aware',
  budget_fit_first: '9. Time Budget Fit First Pass',
  budget_gap_fill: '9.1. Time Budget Gap Fill',
  budget_fit: '9.2. Time Budget Fit Result',
  quality_gates: '10. Quality Gates',
  finalize: '11. Finalize',
  final: '12. Final',
  final_response: '12.1. Final Response',
}

const DEBUG_LABELS: Record<string, string> = {
  budget_fit_output: 'time_budget_fit_output',
  budget_fit_input: 'time_budget_fit_input',
  budget_output: 'time_budget_output',
  requested_budget_minutes: 'requested_time_budget_minutes',
  target_minutes: 'target_time_minutes',
  hard_budget_minutes: 'hard_time_budget_minutes',
  'pipeline_counts.budget_fit_input': 'pipeline_counts.time_budget_fit_input',
  'pipeline_counts.budget_fit_output': 'pipeline_counts.time_budget_fit_output',
  'important.budget_fit_kept_partial': 'important.time_budget_fit_kept_partial',
}

const displayLabel = (label: string): string => DEBUG_LABELS[label] ?? label

const stageByName = (trace: RouteDebugTraceEntry[], stage: string): RouteDebugTraceEntry | undefined => (
  trace.find((entry) => entry.stage === stage)
)

const rawValue = (entry: RouteDebugTraceEntry, keys: string[]): unknown => (
  keys.map((key) => entry[key]).find((item) => !isEmptyValue(item))
)

const field = (payload: Record<string, unknown> | undefined, key: string): unknown => (
  payload && Object.prototype.hasOwnProperty.call(payload, key) ? payload[key] : null
)

const numberValue = (entry: RouteDebugTraceEntry, keys: string[]): number | null => {
  const raw = rawValue(entry, keys)
  if (typeof raw === 'number') return raw
  if (typeof raw === 'string' && raw.trim() !== '' && !Number.isNaN(Number(raw))) return Number(raw)
  return null
}

const summaryNumber = (route: RecommendationRouteResponse, section: string, key: string): number | null => {
  const sectionPayload = route.route_debug_summary?.[section]
  const value = sectionPayload && typeof sectionPayload === 'object'
    ? (sectionPayload as Record<string, unknown>)[key]
    : null
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value))) return Number(value)
  return null
}

const isEmptyValue = (value: unknown): boolean => {
  if (value === undefined || value === null || value === '') return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length === 0
  return false
}

const compactJson = (value: unknown, maxLength = 220): string => {
  const text = JSON.stringify(value)
  if (!text) return '-'
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

const formatValue = (value: unknown): string => {
  if (isEmptyValue(value)) return '-'
  if (Array.isArray(value)) {
    const shown = value.slice(0, 4).map((item) => (
      typeof item === 'object' && item !== null ? compactJson(item, 120) : formatValue(item)
    ))
    const suffix = value.length > shown.length ? ` +${value.length - shown.length}` : ''
    return `${shown.join(' | ')}${suffix}`
  }
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return compactJson(value)
}

const statusLabel = (isBad: boolean, isWarn = false): string => {
  if (isBad) return 'CRITICAL'
  if (isWarn) return 'WARNING'
  return 'OK'
}

const getOrderedTrace = (trace: RouteDebugTraceEntry[]): RouteDebugTraceEntry[] => {
  const known = STAGE_ORDER
    .map((stage) => stageByName(trace, stage))
    .filter((entry): entry is RouteDebugTraceEntry => Boolean(entry))
  const knownNames = new Set(known.map((entry) => entry.stage))
  const rest = trace.filter((entry) => !knownNames.has(entry.stage))
  return [...known, ...rest]
}

const rowsFromPayload = (payload: Record<string, unknown>, prefix = ''): DebugRow[] => Object.entries(payload).flatMap(([key, value]) => {
  const label = prefix ? `${prefix}.${key}` : key
  if (isEmptyValue(value)) return []
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return rowsFromPayload(value as Record<string, unknown>, label)
  }
  return [{ label, value }]
})

const compactStageRows = (entry: RouteDebugTraceEntry): DebugRow[] => Object.entries(entry).flatMap(([key, value]) => {
  if (!IMPORTANT_TRACE_KEYS.has(key) || isEmptyValue(value)) return []
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return rowsFromPayload(value as Record<string, unknown>, key)
  }
  return [{ label: key, value }]
})

const renderRows = (rows: DebugRow[]) => {
  const visibleRows = rows.filter((row) => !isEmptyValue(row.value))
  if (!visibleRows.length) return <p className="route-debug-empty">Нет значимых данных.</p>
  return (
    <div className="route-debug-summary-grid">
      {visibleRows.map((row) => (
        <div key={row.label}>
          <span>{displayLabel(row.label)}</span>
          <strong>{formatValue(row.value)}</strong>
        </div>
      ))}
    </div>
  )
}

const buildPipelineMatrix = (
  route: RecommendationRouteResponse,
  retrieval: RouteDebugTraceEntry,
  candidateRetrieval: RouteDebugTraceEntry,
  hardFilter: RouteDebugTraceEntry,
  scoring: RouteDebugTraceEntry,
  assembly: RouteDebugTraceEntry,
  budgetFit: RouteDebugTraceEntry,
  final: RouteDebugTraceEntry,
): MatrixRow[] => {
  const cityTotal = numberValue(candidateRetrieval, ['places_total_in_city']) ?? summaryNumber(route, 'city', 'places_total_in_city')
  const routeEligible = numberValue(candidateRetrieval, ['places_route_eligible']) ?? summaryNumber(route, 'city', 'places_route_eligible')
  const retrievalOut = numberValue(retrieval, ['final_candidates_count', 'count'])
    ?? numberValue(candidateRetrieval, ['count'])
    ?? summaryNumber(route, 'retrieval', 'final_candidates_count')
  const hardInput = numberValue(hardFilter, ['input_count']) ?? summaryNumber(route, 'pipeline_counts', 'hard_filter_input')
  const hardOut = numberValue(hardFilter, ['output_count', 'kept_count']) ?? summaryNumber(route, 'pipeline_counts', 'hard_filter_output')
  const scoringOut = numberValue(scoring, ['output_count', 'count']) ?? summaryNumber(route, 'pipeline_counts', 'scoring_output')
  const assemblyInput = numberValue(assembly, ['input_scored_count', 'input_count']) ?? summaryNumber(route, 'pipeline_counts', 'assembly_input')
  const assemblyOut = numberValue(assembly, ['output_count', 'selected_count']) ?? summaryNumber(route, 'pipeline_counts', 'assembly_output')
  const budgetInput = numberValue(budgetFit, ['input_count'])
    ?? summaryNumber(route, 'pipeline_counts', 'time_budget_fit_input')
    ?? summaryNumber(route, 'pipeline_counts', 'budget_fit_input')
  const budgetOut = numberValue(budgetFit, ['output_count', 'kept_count'])
    ?? summaryNumber(route, 'pipeline_counts', 'time_budget_fit_output')
    ?? summaryNumber(route, 'pipeline_counts', 'budget_fit_output')
  const finalPoints = numberValue(final, ['final_points_count']) ?? route.total_places

  return [
    {
      step: 'Candidate Retrieval',
      status: statusLabel(Boolean(cityTotal && cityTotal > 0 && retrievalOut === 0)),
      signal: `city_total=${formatValue(cityTotal)}, route_eligible=${formatValue(routeEligible)}, output=${formatValue(retrievalOut)}`,
      action: retrievalOut === 0 ? 'Проверить retrieval query, radius, city-wide fallback, route-visible fallback.' : 'Кандидаты дошли дальше.',
    },
    {
      step: 'Hard Filters',
      status: statusLabel(Boolean(hardInput && hardInput > 0 && hardOut === 0)),
      signal: `input=${formatValue(hardInput)}, output=${formatValue(hardOut)}`,
      action: hardOut === 0 ? 'Проверить opening_hours/timezone/avoided/price_budget/no_coordinates.' : 'Hard filters не выглядят точкой смерти.',
    },
    {
      step: 'Scoring',
      status: statusLabel(Boolean(hardOut && hardOut > 0 && scoringOut === 0)),
      signal: `hard_output=${formatValue(hardOut)}, scoring_output=${formatValue(scoringOut)}`,
      action: scoringOut === 0 ? 'Проверить interest matching и scoring exceptions.' : 'Scoring пропустил кандидатов.',
    },
    {
      step: 'Assembly',
      status: statusLabel(Boolean(assemblyInput && assemblyInput > 20 && (assemblyOut ?? 0) <= 1), Boolean(assemblyInput && assemblyOut !== null && assemblyOut < Math.min(3, assemblyInput))),
      signal: `input_scored=${formatValue(assemblyInput)}, output=${formatValue(assemblyOut)}, target=${formatValue(rawValue(assembly, ['target_points']))}`,
      action: assemblyInput && assemblyInput > 20 && (assemblyOut ?? 0) <= 1
        ? 'Смотреть walk cap, first point, diversity, fallback.'
        : 'Assembly не выглядит главным убийцей маршрута.',
    },
    {
      step: 'Time Budget Fit (minutes)',
      status: statusLabel(Boolean(budgetInput && budgetInput > 0 && budgetOut === 0)),
      signal: `input=${formatValue(budgetInput)}, output=${formatValue(budgetOut)}, time_budget_minutes=${formatValue(rawValue(budgetFit, ['requested_time_budget_minutes', 'requested_budget_minutes']))}, route_minutes=${formatValue(rawValue(budgetFit, ['route_minutes', 'actual_duration_minutes']))}`,
      action: budgetInput && budgetInput > 0 && budgetOut === 0 ? 'Запрещать silent zero: сохранять partial route с warning.' : 'Time budget fit не обнулил маршрут.',
    },
    {
      step: 'Finalize',
      status: statusLabel(Boolean(budgetOut && budgetOut > 0 && finalPoints === 0)),
      signal: `time_budget_output=${formatValue(budgetOut)}, final_points=${formatValue(finalPoints)}, status=${formatValue(route.status)}`,
      action: budgetOut && budgetOut > 0 && finalPoints === 0 ? 'Проверить status mapping/finalize: partial не должен стать no_route.' : 'Finalize не скрыл валидный partial route.',
    },
  ]
}

const buildKeyRows = (
  route: RecommendationRouteResponse,
  retrieval: RouteDebugTraceEntry,
  candidateRetrieval: RouteDebugTraceEntry,
  hardFilter: RouteDebugTraceEntry,
  scoring: RouteDebugTraceEntry,
  assembly: RouteDebugTraceEntry,
  budgetFit: RouteDebugTraceEntry,
  final: RouteDebugTraceEntry,
): DebugRow[] => ([
  { label: 'status', value: route.status },
  { label: 'partial_reason', value: route.partial_reason },
  { label: 'death_point', value: field(route.route_debug_summary, 'death_point') ?? field(route.route_debug_summary, 'failure_stage') },
  { label: 'city_total', value: numberValue(candidateRetrieval, ['places_total_in_city']) ?? summaryNumber(route, 'city', 'places_total_in_city') },
  { label: 'route_visible', value: numberValue(candidateRetrieval, ['places_route_visible']) ?? summaryNumber(route, 'city', 'places_route_visible') },
  { label: 'route_eligible', value: numberValue(candidateRetrieval, ['places_route_eligible']) ?? summaryNumber(route, 'city', 'places_route_eligible') },
  { label: 'geo_query_count', value: numberValue(candidateRetrieval, ['geo_query_count']) },
  { label: 'retrieval_output', value: numberValue(retrieval, ['final_candidates_count', 'count']) ?? summaryNumber(route, 'retrieval', 'final_candidates_count') },
  { label: 'retrieval_strategy', value: rawValue(retrieval, ['retrieval_strategy_used']) },
  { label: 'route_visible_fallback', value: rawValue(retrieval, ['fallback_route_visible_used']) },
  { label: 'hard_filters_output', value: numberValue(hardFilter, ['output_count', 'kept_count']) ?? summaryNumber(route, 'pipeline_counts', 'hard_filter_output') },
  { label: 'scoring_output', value: numberValue(scoring, ['output_count', 'count']) ?? summaryNumber(route, 'pipeline_counts', 'scoring_output') },
  { label: 'assembly_output', value: numberValue(assembly, ['output_count', 'selected_count']) ?? summaryNumber(route, 'pipeline_counts', 'assembly_output') },
  {
    label: 'time_budget_fit_output',
    value: numberValue(budgetFit, ['output_count', 'kept_count'])
      ?? summaryNumber(route, 'pipeline_counts', 'time_budget_fit_output')
      ?? summaryNumber(route, 'pipeline_counts', 'budget_fit_output'),
  },
  { label: 'final_points', value: numberValue(final, ['final_points_count']) ?? route.total_places },
])

const renderMatrix = (rows: MatrixRow[]) => (
  <div className="route-debug-matrix">
    {rows.map((row) => (
      <div className="route-debug-matrix-row" key={row.step} data-status={row.status.toLowerCase()}>
        <span>{row.status}</span>
        <strong>{row.step}</strong>
        <p>{row.signal}</p>
        <p>{row.action}</p>
      </div>
    ))}
  </div>
)

export const RouteDebugTrace = ({ route }: Props) => {
  const trace = getOrderedTrace(route.debug_trace ?? [])
  const retrieval = stageByName(trace, 'retrieval') ?? stageByName(trace, 'candidate_retrieval') ?? emptyTraceEntry
  const candidateRetrieval = stageByName(trace, 'candidate_retrieval') ?? emptyTraceEntry
  const hardFilter = stageByName(trace, 'hard_filters') ?? stageByName(trace, 'hard_filter') ?? emptyTraceEntry
  const scoring = stageByName(trace, 'scoring') ?? stageByName(trace, 'scoring_raw') ?? emptyTraceEntry
  const assembly = stageByName(trace, 'assembly') ?? emptyTraceEntry
  const budgetFit = stageByName(trace, 'budget_fit') ?? emptyTraceEntry
  const final = stageByName(trace, 'final') ?? emptyTraceEntry
  const meaningfulTrace = trace.filter((entry) => compactStageRows(entry).length > 1)

  return (
    <section className="route-result-tile route-debug-trace route-debug-page">
      <h3>Debug маршрута</h3>

      <div className="route-debug-section route-debug-section-primary">
        <strong>Главный вывод</strong>
        {renderRows(buildKeyRows(route, retrieval, candidateRetrieval, hardFilter, scoring, assembly, budgetFit, final))}
      </div>

      <div className="route-debug-section">
        <strong>Диагностическая матрица</strong>
        {renderMatrix(buildPipelineMatrix(route, retrieval, candidateRetrieval, hardFilter, scoring, assembly, budgetFit, final))}
      </div>

      <div className="route-debug-stage-list">
        <strong>Debug trace по шагам</strong>
        {meaningfulTrace.map((entry, index) => (
          <div className="route-debug-stage" key={`${entry.stage}-${index}`}>
            <h4>{stageTitles[entry.stage] ?? entry.stage}</h4>
            {renderRows(compactStageRows(entry).filter((row) => row.label !== 'stage'))}
          </div>
        ))}
      </div>
    </section>
  )
}
