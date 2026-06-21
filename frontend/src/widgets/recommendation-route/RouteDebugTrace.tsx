import type { RecommendationRouteResponse, RouteDebugTraceEntry } from '../../api/recommendations/recommendationRoute.types'

type Props = {
  route: RecommendationRouteResponse
}

type DebugRow = {
  label: string
  value: unknown
}

const emptyTraceEntry: RouteDebugTraceEntry = { stage: 'empty' }

const stageByName = (trace: RouteDebugTraceEntry[], stage: string): RouteDebugTraceEntry | undefined => (
  trace.find((entry) => entry.stage === stage)
)

const rawValue = (entry: RouteDebugTraceEntry, keys: string[]): unknown => (
  keys.map((key) => entry[key]).find((item) => item !== undefined && item !== null)
)

const numberValue = (entry: RouteDebugTraceEntry, keys: string[]): number | null => {
  const raw = rawValue(entry, keys)
  if (typeof raw === 'number') return raw
  if (typeof raw === 'string' && raw.trim() !== '' && !Number.isNaN(Number(raw))) return Number(raw)
  return null
}

const json = (payload: unknown): string => JSON.stringify(payload, null, 2)

const formatValue = (value: unknown): string => {
  if (value === undefined || value === null || value === '') return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

const field = (payload: Record<string, unknown> | undefined, key: string): unknown => (
  payload && Object.prototype.hasOwnProperty.call(payload, key) ? payload[key] : null
)

const retrievalDiagnosis = (
  retrieval: RouteDebugTraceEntry,
  candidateRetrieval: RouteDebugTraceEntry,
  hardFilter: RouteDebugTraceEntry,
  scoring: RouteDebugTraceEntry,
): Record<string, unknown> => {
  const finalCandidates = numberValue(retrieval, ['final_candidates_count', 'count']) ?? numberValue(candidateRetrieval, ['count'])
  const cityWideExpected = numberValue(candidateRetrieval, ['candidate_retrieval_city_wide_expected_count', 'places_route_eligible'])
  const radiusExpected = numberValue(candidateRetrieval, ['candidate_retrieval_expected_count', 'geo_route_eligible_count', 'geo_query_count'])
  const routeVisible = numberValue(candidateRetrieval, ['places_route_visible'])
  const hardFilterInput = numberValue(hardFilter, ['input_count'])
  const hardFilterOutput = numberValue(hardFilter, ['output_count', 'kept_count'])
  const scoringOutput = numberValue(scoring, ['output_count', 'count'])
  const status = finalCandidates === 0 && (cityWideExpected ?? 0) > 0
    ? 'CRITICAL: city-wide candidates exist, but retrieval returned 0'
    : finalCandidates === 0 && (routeVisible ?? 0) > 0
      ? 'CRITICAL: route-visible places exist, but retrieval returned 0'
      : (hardFilterInput ?? 0) > 0 && hardFilterOutput === 0
        ? 'CRITICAL: retrieval returned candidates, but hard filters removed all of them'
        : (hardFilterOutput ?? 0) > 0 && scoringOutput === 0
          ? 'CRITICAL: hard filters kept candidates, but scoring returned 0'
          : finalCandidates !== null && finalCandidates < 40
            ? 'LOW: retrieval returned less than healthy threshold'
            : 'OK'

  return {
    status,
    final_candidates: finalCandidates,
    hard_filter_input: hardFilterInput,
    hard_filter_output: hardFilterOutput,
    scoring_output: scoringOutput,
    radius_expected: radiusExpected,
    city_wide_expected: cityWideExpected,
    route_visible: routeVisible,
    radius_meters: rawValue(candidateRetrieval, ['radius_meters']),
    start_point: rawValue(candidateRetrieval, ['start_point']),
    retrieval_stage: rawValue(retrieval, ['retrieval_strategy_used']),
    fallback_radius_used: rawValue(retrieval, ['fallback_radius_used']),
    fallback_city_wide_used: rawValue(retrieval, ['fallback_city_wide_used']),
    fallback_route_visible_used: rawValue(retrieval, ['fallback_route_visible_used']),
    sample_candidate_ids: rawValue(retrieval, ['sample_candidate_ids']),
  }
}

const buildCopyPayload = (
  route: RecommendationRouteResponse,
  retrieval: RouteDebugTraceEntry,
  candidateRetrieval: RouteDebugTraceEntry,
  hardFilter: RouteDebugTraceEntry,
  scoring: RouteDebugTraceEntry,
  assembly: RouteDebugTraceEntry,
  budgetFit: RouteDebugTraceEntry,
): Record<string, unknown> => ({
  route_id: route.route_id,
  status: route.status,
  partial_reason: route.partial_reason,
  total_places: route.total_places,
  warnings: route.warnings,
  route_debug_summary: route.route_debug_summary ?? null,
  route_debug_summary_exists: Boolean(route.route_debug_summary),
  retrieval_diagnosis: retrievalDiagnosis(retrieval, candidateRetrieval, hardFilter, scoring),
  route: {
    route_quality_status: route.route_quality_status,
    route_completeness: route.route_completeness,
    expansion_level: route.expansion_level,
    fallback_level: route.fallback_level,
    matched_interest_count: route.matched_interest_count,
    total_requested_interests: route.total_requested_interests,
  },
  city: {
    places_total_in_city: rawValue(candidateRetrieval, ['places_total_in_city']) ?? field(route.route_debug_summary?.city, 'places_total_in_city'),
    places_public_catalog: rawValue(candidateRetrieval, ['places_public_catalog']) ?? field(route.route_debug_summary?.city, 'places_public_catalog'),
    places_route_visible: rawValue(candidateRetrieval, ['places_route_visible']) ?? field(route.route_debug_summary?.city, 'places_route_visible'),
    places_route_eligible: rawValue(candidateRetrieval, ['places_route_eligible']) ?? field(route.route_debug_summary?.city, 'places_route_eligible'),
    geo_query_count: rawValue(candidateRetrieval, ['geo_query_count']) ?? field(route.route_debug_summary?.city, 'geo_query_count'),
  },
  retrieval: {
    final_candidates_count: rawValue(retrieval, ['final_candidates_count', 'count']) ?? field(route.route_debug_summary?.retrieval, 'final_candidates_count'),
    raw_candidates_count: rawValue(retrieval, ['raw_candidates_count']) ?? field(route.route_debug_summary?.retrieval, 'raw_candidates_count'),
    after_radius_count: rawValue(retrieval, ['after_radius_count']) ?? field(route.route_debug_summary?.retrieval, 'after_radius_count'),
    expanded_radius_candidates_count: rawValue(retrieval, ['expanded_radius_candidates_count']) ?? field(route.route_debug_summary?.retrieval, 'expanded_radius_candidates_count'),
    city_wide_candidates_count: rawValue(retrieval, ['city_wide_candidates_count']) ?? field(route.route_debug_summary?.retrieval, 'city_wide_candidates_count'),
    route_visible_candidates_count: rawValue(retrieval, ['route_visible_candidates_count']) ?? field(route.route_debug_summary?.retrieval, 'route_visible_candidates_count'),
    retrieval_strategy_used: rawValue(retrieval, ['retrieval_strategy_used']) ?? field(route.route_debug_summary?.retrieval, 'strategy'),
    fallback_radius_used: rawValue(retrieval, ['fallback_radius_used']),
    fallback_city_wide_used: rawValue(retrieval, ['fallback_city_wide_used']),
    fallback_route_visible_used: rawValue(retrieval, ['fallback_route_visible_used']),
    retrieval_loss_summary: rawValue(retrieval, ['retrieval_loss_summary']) ?? field(route.route_debug_summary?.important, 'retrieval_loss_summary'),
    sample_candidate_ids: rawValue(retrieval, ['sample_candidate_ids']) ?? field(route.route_debug_summary?.important, 'sample_candidate_ids'),
  },
  pipeline_counts: {
    hard_filter_input: rawValue(hardFilter, ['input_count']) ?? field(route.route_debug_summary?.pipeline_counts, 'hard_filter_input'),
    hard_filter_output: rawValue(hardFilter, ['output_count', 'kept_count']) ?? field(route.route_debug_summary?.pipeline_counts, 'hard_filter_output'),
    scoring_output: rawValue(scoring, ['output_count', 'count']) ?? field(route.route_debug_summary?.pipeline_counts, 'scoring_output'),
    assembly_output: rawValue(assembly, ['selected_count']) ?? field(route.route_debug_summary?.pipeline_counts, 'assembly_output'),
    budget_fit_output: rawValue(budgetFit, ['output_count', 'kept_count']) ?? field(route.route_debug_summary?.pipeline_counts, 'budget_fit_output'),
  },
})

const rowsFromPayload = (payload: Record<string, unknown>, prefix = ''): DebugRow[] => Object.entries(payload).flatMap(([key, value]) => {
  const label = prefix ? `${prefix}.${key}` : key
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return rowsFromPayload(value as Record<string, unknown>, label)
  }
  return [{ label, value }]
})

const renderRows = (rows: DebugRow[]) => (
  <div className="route-debug-summary-grid">
    {rows.map((row) => (
      <div key={row.label}>
        <span>{row.label}</span>
        <strong>{formatValue(row.value)}</strong>
      </div>
    ))}
  </div>
)

const renderCopyLines = (payload: Record<string, unknown>) => (
  <div className="route-debug-copy-lines">
    {json(payload).split('\n').map((line, index) => (
      <div key={`${index}-${line}`}>{line || ' '}</div>
    ))}
  </div>
)

export const RouteDebugTrace = ({ route }: Props) => {
  const trace = route.debug_trace ?? []
  const retrieval = stageByName(trace, 'retrieval') ?? stageByName(trace, 'candidate_retrieval') ?? emptyTraceEntry
  const candidateRetrieval = stageByName(trace, 'candidate_retrieval') ?? emptyTraceEntry
  const hardFilter = stageByName(trace, 'hard_filters') ?? stageByName(trace, 'hard_filter') ?? emptyTraceEntry
  const scoring = stageByName(trace, 'scoring') ?? stageByName(trace, 'scoring_raw') ?? emptyTraceEntry
  const assembly = stageByName(trace, 'assembly') ?? emptyTraceEntry
  const budgetFit = stageByName(trace, 'budget_fit') ?? emptyTraceEntry
  const copyPayload = buildCopyPayload(route, retrieval, candidateRetrieval, hardFilter, scoring, assembly, budgetFit)

  return (
    <section className="route-result-tile route-debug-trace route-debug-page">
      <h3>Debug маршрута</h3>
      <p>Короткая диагностика без вложенных скроллов. Просто листай страницу вниз.</p>

      <div className="route-debug-warning-box">
        <strong>Главный диагноз</strong>
        {renderRows(rowsFromPayload(retrievalDiagnosis(retrieval, candidateRetrieval, hardFilter, scoring)))}
      </div>

      <div className="route-debug-warning-box">
        <strong>Короткий JSON для копирования</strong>
        {renderCopyLines(copyPayload)}
      </div>

      <div className="route-debug-warning-box">
        <strong>Сводка ответа</strong>
        {renderRows([
          { label: 'route_id', value: route.route_id },
          { label: 'status', value: route.status },
          { label: 'partial_reason', value: route.partial_reason },
          { label: 'total_places', value: route.total_places },
          { label: 'route_quality_status', value: route.route_quality_status },
          { label: 'route_completeness', value: route.route_completeness },
          { label: 'route_debug_summary_exists', value: Boolean(route.route_debug_summary) },
          { label: 'debug_trace_entries', value: trace.length },
        ])}
      </div>

      {route.route_debug_summary ? (
        <div className="route-debug-warning-box">
          <strong>Backend route_debug_summary</strong>
          {renderRows(rowsFromPayload(route.route_debug_summary))}
        </div>
      ) : null}

      <div className="route-debug-warning-box">
        <strong>Warnings</strong>
        {renderRows([
          { label: 'warnings', value: route.warnings },
          { label: 'user_warnings', value: route.user_warnings?.map((item) => item.type) ?? [] },
        ])}
      </div>
    </section>
  )
}
