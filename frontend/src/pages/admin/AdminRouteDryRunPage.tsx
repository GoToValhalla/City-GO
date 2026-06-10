import { useEffect, useMemo, useState } from 'react'
import { adminGet, adminPost } from './adminApi'
import type { AdminCitiesResponse } from './adminTypes'
import type { DryRunCandidate, DryRunResponse } from './adminRouteTypes'
import { AdminError } from './shared/AdminStates'

const qualityLabel = (status?: string) => {
  switch (status) {
    case 'good': return 'Хороший'
    case 'acceptable': return 'Допустимый'
    case 'weak': return 'Слабый'
    case 'failed': return 'Не собран'
    default: return status || '—'
  }
}

const qualityClass = (status?: string) => {
  if (status === 'good' || status === 'acceptable') return 'admin-badge pub-published'
  if (status === 'failed') return 'admin-badge pub-hidden'
  return 'admin-badge pub-draft'
}

const warningText = (code: string) => {
  const map: Record<string, string> = {
    route_failed_no_places: 'Не удалось собрать маршрут: нет подходящих точек.',
    route_short_due_to_time_budget: 'Маршрут короткий из-за малого бюджета времени.',
    route_short_due_to_low_place_density: 'Маршрут короткий: мало подходящих мест.',
    some_places_have_no_address: 'У части точек нет адреса.',
    some_places_have_no_photo: 'У части точек нет фото.',
    some_places_have_weak_description: 'У части точек слабое описание.',
    route_has_long_walk_segments: 'Есть длинные пешие переходы.',
    category_diversity_limited: 'Ограничено разнообразие категорий.',
  }
  return map[code] ?? code
}

type MapCandidate = DryRunCandidate & { x: number; y: number }

const mapPoints = (points: DryRunCandidate[]): MapCandidate[] => {
  const valid = points.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
  if (!valid.length) return []
  const minLat = Math.min(...valid.map((p) => Number(p.lat)))
  const maxLat = Math.max(...valid.map((p) => Number(p.lat)))
  const minLng = Math.min(...valid.map((p) => Number(p.lng)))
  const maxLng = Math.max(...valid.map((p) => Number(p.lng)))
  const latSpan = Math.max(maxLat - minLat, 0.00001)
  const lngSpan = Math.max(maxLng - minLng, 0.00001)
  return valid.map((point) => ({
    ...point,
    x: 8 + ((Number(point.lng) - minLng) / lngSpan) * 84,
    y: 92 - ((Number(point.lat) - minLat) / latSpan) * 84,
  }))
}

const pathFrom = (points: MapCandidate[]) => points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ')

const DryRunMiniMap = ({ points }: { points: DryRunCandidate[] }) => {
  const mapped = useMemo(() => mapPoints(points), [points])
  if (!mapped.length) return <div className="admin-muted">Для мини-карты нет координат selected-точек.</div>
  return (
    <section className="admin-metric-card" style={{ marginBottom: 16 }}>
      <h3>Мини-карта selected</h3>
      <svg viewBox="0 0 100 100" style={{ width: '100%', minHeight: 260, background: '#202124', borderRadius: 8 }} role="img" aria-label="Dry run route map">
        <path d="M0 20 H100 M0 40 H100 M0 60 H100 M0 80 H100 M20 0 V100 M40 0 V100 M60 0 V100 M80 0 V100" stroke="rgba(255,255,255,.12)" strokeWidth="0.5" />
        {mapped.length > 1 ? <path d={pathFrom(mapped)} fill="none" stroke="#7cc7ff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /> : null}
        {mapped.map((point, index) => (
          <g key={point.place_id} transform={`translate(${point.x} ${point.y})`}>
            <circle r="4.8" fill="#fff" stroke="#0066cc" strokeWidth="1.5" />
            <text textAnchor="middle" dominantBaseline="central" fill="#0066cc" fontSize="4" fontWeight="800">{index + 1}</text>
          </g>
        ))}
      </svg>
      <p className="admin-muted">Порядок маркеров соответствует порядку selected-точек в dry-run.</p>
    </section>
  )
}

export const AdminRouteDryRunPage = () => {
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [citySlug, setCitySlug] = useState('')
  const [duration, setDuration] = useState(180)
  const [budget, setBudget] = useState<number | ''>('')
  const [startLat, setStartLat] = useState('')
  const [startLng, setStartLng] = useState('')
  const [interests, setInterests] = useState('')
  const [result, setResult] = useState<DryRunResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100')
      .then((response) => {
        setCities(response.items)
        setCitySlug((current) => current || response.items[0]?.slug || '')
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  const run = async () => {
    if (!citySlug) {
      setError('Выберите город для dry-run.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const body: Record<string, unknown> = {
        city_slug: citySlug, duration_min: duration, route_mode: 'walk',
        interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
      }
      if (budget !== '') body.budget_level = Number(budget)
      if (startLat && startLng) { body.start_lat = Number(startLat); body.start_lng = Number(startLng) }
      setResult(await adminPost<DryRunResponse>('/admin/routes/dry-run', body))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(false) }
  }

  const downloadJson = () => {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `dry-run-${citySlug}-${result.generation_run_id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <h2 className="admin-page-title">Маршруты → Dry Run</h2>
      <div className="admin-filters">
        <select value={citySlug} onChange={(e) => setCitySlug(e.target.value)} aria-label="Город dry-run">
          <option value="">Город</option>
          {cities.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
        <input type="number" value={duration} onChange={(e) => setDuration(Number(e.target.value))} placeholder="минуты" />
        <input value={budget} onChange={(e) => setBudget(e.target.value === '' ? '' : Number(e.target.value))} placeholder="бюджет" />
        <input value={startLat} onChange={(e) => setStartLat(e.target.value)} placeholder="lat" />
        <input value={startLng} onChange={(e) => setStartLng(e.target.value)} placeholder="lng" />
        <input value={interests} onChange={(e) => setInterests(e.target.value)} placeholder="интересы (через запятую)" />
        <button type="button" className="admin-btn" disabled={busy || !citySlug} onClick={run}>{busy ? '…' : 'Запустить'}</button>
        {result && <button type="button" className="admin-btn admin-btn-sm" onClick={downloadJson}>JSON</button>}
      </div>
      {error && <AdminError message={error} />}
      {result && (
        <div>
          <p>Run #{result.generation_run_id}: total {result.counts.total_candidates}, eligible {result.counts.eligible_candidates}, selected {result.counts.selected_places}</p>
          <DryRunMiniMap points={result.selected_places} />
          {result.quality ? (
            <section className="admin-metric-card" style={{ marginBottom: 16 }}>
              <div className="admin-metric-value">{result.quality.score_percent}%</div>
              <div className="admin-metric-label">Качество маршрута</div>
              <p><span className={qualityClass(result.quality.status)}>{qualityLabel(result.quality.status)}</span></p>
              {result.quality.partial_reason ? <p className="admin-muted">Причина: {result.quality.partial_reason}</p> : null}
              {result.quality.warnings.length > 0 ? (
                <ul className="admin-muted">
                  {result.quality.warnings.map((warning) => <li key={warning}>{warningText(warning)}</li>)}
                </ul>
              ) : <p className="admin-muted">Критичных предупреждений нет.</p>}
              {Object.keys(result.quality.breakdown).length > 0 ? (
                <pre className="admin-muted" style={{ fontSize: 11 }}>{JSON.stringify(result.quality.breakdown, null, 2)}</pre>
              ) : null}
            </section>
          ) : null}
          <h3>Selected</h3>
          <table className="admin-table"><thead><tr><th>Место</th><th>Кат.</th><th>Score</th><th>Reasons</th></tr></thead><tbody>
            {result.selected_places.map((p) => <tr key={p.place_id}><td>{p.title}</td><td>{p.category}</td><td>{p.score ?? '—'}</td><td>{p.selection_reasons.join(', ')}</td></tr>)}
          </tbody></table>
          <h3>Rejected</h3>
          <table className="admin-table"><thead><tr><th>Место</th><th>Кат.</th><th>Reasons</th></tr></thead><tbody>
            {result.rejected_candidates.slice(0, 50).map((p) => <tr key={p.place_id}><td>{p.title}</td><td>{p.category}</td><td>{p.rejection_reasons.join(', ')}</td></tr>)}
          </tbody></table>
        </div>
      )}
    </div>
  )
}
