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
  budget_fit_first: '9. Budget Fit First Pass',
  budget_gap_fill: '9.1. Budget Gap Fill',
  budget_fit: '9.2. Budget Fit Result',
  quality_gates: '10. Quality Gates',
  finalize: '11. Finalize',
  final: '12. Final',
  final_response: '12.1. Final Response',
}

const stageByName = (trace: RouteDebugTraceEntry[], stage: string): RouteDebugTraceEntry | undefined => (
  trace.find((entry) => entry.stage === stage)
)

const rawValue = (entry: RouteDebugTraceEntry, keys: string[]): unknown => (
  keys.map((key) => entry[key]).find((item) => item !== undefined && item !== null)
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

const formatValue = (value: unknown): string => {
  if (value === undefined || value === null || value === '') return '-'
  if (Array.isArray(value)) return value.length ? value.map(formatValue).join(', ') : '-'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

const statusLabel = (isBad: boolean, isWarn = false): string => {
  if (isBad) return 'CRITICAL'
  if (isWarn) return 'WARNING'
  return 'OK'
}

const stageOutput = (entry: RouteDebugTraceEntry): number | null => (
  numberValue(entry, ['output_count', 'kept_count', 'selected_count', 'count'])
)

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
  const budgetInput = numberValue(budgetFit, ['input_count']) ?? summaryNumber(route, 'pipeline_counts', 'budget_fit_input')
  const budgetOut = numberValue(budgetFit, ['output_count', 'kept_count']) ?? summaryNumber(route, 'pipeline_counts', 'budget_fit_output')
  const finalPoints = numberValue(final, ['final_points_count']) ?? route.total_places

  return [
    {
      step: 'Candidate Retrieval',
      status: statusLabel(Boolean(cityTotal && cityTotal > 0 && retrievalOut === 0)),
      signal: `city_total=${formatValue(cityTotal)}, route_eligible=${formatValue(routeEligible)}, output=${formatValue(retrievalOut)}`,
      action: retrievalOut === 0 ? 'Проверить city slug, radius, fallback city-wide, category balance.' : 'Кандидаты дошли дальше.',
    },
    {
      step: 'Hard Filters',
      status: statusLabel(Boolean(hardInput && hardInput > 0 && hardOut === 0)),
      signal: `input=${formatValue(hardInput)}, output=${formatValue(hardOut)}`,
      action: hardOut === 0 ? 'Проверить opening_hours/timezone/avoided/budget/no_coordinates.' : 'Hard filters не выглядят точкой смерти.',
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
        ? 'Гипотеза Gemini подтверждается: смотреть walk cap, first point, diversity, fallback.'
        : 'Assembly не выглядит главным убийцей маршрута.',
    },
    {
      step: 'Budget Fit',
      status: statusLabel(Boolean(budgetInput && budgetInput > 0 && budgetOut === 0)),
      signal: `input=${formatValue(budgetInput)}, output=${formatValue(budgetOut)}, budget=${formatValue(rawValue(budgetFit, ['requested_budget_minutes']))}, route_minutes=${formatValue(rawValue(budgetFit, ['route_minutes', 'actual_duration_minutes']))}`,
      action: budgetInput && budgetInput > 0 && budgetOut === 0 ? 'Запрещать silent zero: сохранять partial route с warning.' : 'Budget fit не обнулил маршрут.',
    },
    {
      step: 'Finalize',
      status: statusLabel(Boolean(budgetOut && budgetOut > 0 && finalPoints === 0)),
      signal: `budget_output=${formatValue(budgetOut)}, final_points=${formatValue(finalPoints)}, status=${formatValue(route.status)}`,
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
  { label: 'route_id', value: route.route_id },
  { label: 'status', value: route.status },
  { label: 'partial_reason', value: route.partial_reason },
  { label: 'death_point', value: field(route.route_debug_summary, 'death_point') ?? field(route.route_debug_summary, 'failure_stage') },
  { label: 'city_total', value: numberValue(candidateRetrieval, ['places_total_in_city']) ?? summaryNumber(route, 'city', 'places_total_in_city') },
  { label: 'route_eligible_total', value: numberValue(candidateRetrieval, ['places_route_eligible']) ?? summaryNumber(route, 'city', 'places_route_eligible') },
  { label: 'retrieval_output', value: numberValue(retrieval, ['final_candidates_count', 'count']) ?? summaryNumber(route, 'retrieval', 'final_candidates_count') },
  { label: 'hard_filters_output', value: numberValue(hardFilter, ['output_count', 'kept_count']) ?? summaryNumber(route, 'pipeline_counts', 'hard_filter_output') },
  { label: 'scoring_output', value: numberValue(scoring, ['output_count', 'count']) ?? summaryNumber(route, 'pipeline_counts', 'scoring_output') },
  { label: 'assembly_input', value: numberValue(assembly, ['input_scored_count', 'input_count']) ?? summaryNumber(route, 'pipeline_counts', 'assembly_input') },
  { label: 'assembly_output', value: numberValue(assembly, ['output_count', 'selected_count']) ?? summaryNumber(route, 'pipeline_counts', 'assembly_output') },
  { label: 'budget_fit_output', value: numberValue(budgetFit, ['output_count', 'kept_count']) ?? summaryNumber(route, 'pipeline_counts', 'budget_fit_output') },
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
  const adaptivePlan = stageByName(trace, 'adaptive_plan') ?? emptyTraceEntry
  const assembly = stageByName(trace, 'assembly') ?? emptyTraceEntry
  const budgetFit = stageByName(trace, 'budget_fit') ?? emptyTraceEntry
  const qualityGates = stageByName(trace, 'quality_gates') ?? emptyTraceEntry
  const final = stageByName(trace, 'final') ?? emptyTraceEntry

  return (
    <section className="route-result-tile route-debug-trace route-debug-page">
      <h3>Debug маршрута</h3>
      <p>Полная диагностика пайплайна на странице. Без вложенных блоков, скролла и JSON-портянок.</p>

      <div className="route-debug-section">
        <strong>Главный вывод</strong>
        {renderRows(buildKeyRows(route, retrieval, candidateRetrieval, hardFilter, scoring, assembly, budgetFit, final))}
      </div>

      <div className="route-debug-section">
        <strong>Диагностическая матрица Gemini + Route Engine</strong>
        {renderMatrix(buildPipelineMatrix(route, retrieval, candidateRetrieval, hardFilter, scoring, assembly, budgetFit, final))}
      </div>

      <div className="route-debug-section">
        <strong>Context / Interests / Avoided</strong>
        {renderRows([
          { label: 'interests', value: rawValue(stageByName(trace, 'context_merge') ?? emptyTraceEntry, ['interests']) },
          { label: 'avoided_categories', value: rawValue(stageByName(trace, 'context_merge') ?? emptyTraceEntry, ['avoided_categories']) },
          { label: 'resolved_conflicts', value: rawValue(stageByName(trace, 'context_merge') ?? emptyTraceEntry, ['interest_removed_due_to_avoidance']) },
          { label: 'context_warnings', value: rawValue(stageByName(trace, 'context_normalization') ?? emptyTraceEntry, ['warnings']) },
        ])}
      </div>

      <div className="route-debug-section">
        <strong>Assembly / Budget / Quality</strong>
        {renderRows([
          { label: 'assembly.failure_reason', value: rawValue(assembly, ['failure_reason']) },
          { label: 'assembly.rejection_reasons', value: rawValue(assembly, ['rejection_reasons']) },
          { label: 'assembly.first_point_rejection_reasons', value: rawValue(assembly, ['first_point_rejection_reasons']) },
          { label: 'assembly.fallback_used', value: rawValue(assembly, ['fallback_used']) },
          { label: 'assembly.fallback_triggers', value: rawValue(assembly, ['fallback_triggers']) },
          { label: 'budget_fit.failure_reason', value: rawValue(budgetFit, ['failure_reason']) },
          { label: 'budget_fit.warnings', value: rawValue(budgetFit, ['warnings']) },
          { label: 'quality_gates.status', value: rawValue(qualityGates, ['route_quality_status', 'status']) },
          { label: 'quality_gates.failed_gates', value: rawValue(qualityGates, ['failed_gates']) },
        ])}
      </div>

      {route.route_debug_summary ? (
        <div className="route-debug-section">
          <strong>Backend route_debug_summary</strong>
          {renderRows(rowsFromPayload(route.route_debug_summary))}
        </div>
      ) : null}

      <div className="route-debug-stage-list">
        <strong>Полный debug_trace по шагам</strong>
        {trace.map((entry) => (
          <div className="route-debug-stage" key={`${entry.stage}-${stageOutput(entry) ?? 'none'}`}>
            <h4>{stageTitles[entry.stage] ?? entry.stage}</h4>
            {renderRows(rowsFromPayload(entry as Record<string, unknown>))}
          </div>
        ))}
      </div>
    </section>
  )
}
