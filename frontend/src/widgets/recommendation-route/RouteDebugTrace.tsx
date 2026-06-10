import type { RouteDebugTraceEntry } from '../../api/recommendations/recommendationRoute.types'

type Props = {
  trace?: RouteDebugTraceEntry[]
}

const stageTitle: Record<string, string> = {
  assembly: 'Сборка маршрута',
  budget_fit: 'Подгонка под бюджет',
  candidate_retrieval: 'Поиск кандидатов',
  context_merge: 'Контекст запроса',
  hard_filter: 'Жёсткие фильтры',
  quality_annotation: 'Качество данных',
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
  'places_active_legacy_safe',
  'places_with_coords',
  'geo_query_count',
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

export const RouteDebugTrace = ({ trace = [] }: Props) => {
  if (trace.length === 0) return null

  return (
    <details className="route-result-tile route-debug-trace" open>
      <summary>Debug маршрута</summary>
      <div className="route-debug-list">
        {trace.map((entry, index) => {
          const details = diagnostics(entry)
          return (
            <div className="route-debug-item" key={`${entry.stage}-${index}`}>
              <strong>{stageTitle[entry.stage] ?? entry.stage}</strong>
              <span>duration_ms: {value(entry, ['duration_ms'])}</span>
              <span>count: {value(entry, ['count', 'input_count'])}</span>
              <span>kept: {value(entry, ['kept_count', 'selected_count'])}</span>
              <span>removed: {value(entry, ['removed_count'])}</span>
              <span>warnings: {value(entry, ['warning_count'])}</span>
              <span>fallback: {value(entry, ['fallback_used'])}</span>
              <span>reasons: {reasons(entry)}</span>
              {details ? <pre>{details}</pre> : null}
            </div>
          )
        })}
      </div>
    </details>
  )
}
