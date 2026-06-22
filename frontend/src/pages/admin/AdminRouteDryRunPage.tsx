import { useEffect, useMemo, useState } from 'react'
import { adminGet, adminPost } from './adminApi'
import type { AdminCitiesResponse } from './adminTypes'
import type { DryRunCandidate, DryRunResponse, RouteDraft, RouteDraftGenerationResponse, RoutePublishResponse } from './adminRouteTypes'
import { AdminError } from './shared/AdminStates'

const qualityLabel = (status?: string) => {
  switch (status) {
    case 'good': return 'Хороший'
    case 'acceptable': return 'Можно проверить'
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
    route_incomplete: 'Маршрут не собран до конца.',
    route_short_due_to_time_budget: 'Маршрут короткий из-за малого бюджета времени.',
    route_short_due_to_low_place_density: 'Маршрут короткий: мало подходящих мест.',
    route_built_without_selected_interests: 'Маршрут собран без выбранных интересов.',
    some_places_have_no_address: 'У части точек нет адреса.',
    some_places_have_no_photo: 'У части точек нет фото.',
    some_places_have_weak_description: 'У части точек слабое описание.',
    route_has_long_walk_segments: 'Есть длинные пешие переходы.',
    category_diversity_limited: 'Ограничено разнообразие категорий.',
  }
  return map[code] ?? humanizeCode(code)
}

const reasonText = (code: string) => {
  if (code.startsWith('forbidden_category:')) {
    return `Категория не подходит для маршрутов: ${code.split(':')[1] || 'неизвестно'}.`
  }
  if (code.startsWith('quality_tier_not_route_allowed:')) {
    return `Низкий уровень качества места: ${code.split(':')[1] || 'неизвестно'}.`
  }
  const map: Record<string, string> = {
    selected: 'Выбрано в маршрут.',
    score: 'Высокая оценка для маршрута.',
    close_to_start: 'Рядом со стартом маршрута.',
    category_match: 'Подходит под выбранные интересы.',
    city_not_published: 'Город не опубликован. Сначала переведите город в опубликованное состояние.',
    city_inactive: 'Город выключен. Включите город перед сборкой маршрутов.',
    missing_city_id: 'У места не указан город.',
    place_not_published: 'Место не опубликовано. Опубликуйте место или уберите его из кандидатов.',
    unpublished_place: 'Место не опубликовано. Опубликуйте место или уберите его из кандидатов.',
    place_not_visible_in_catalog: 'Место скрыто в каталоге. Сделайте его видимым.',
    hidden_place: 'Место скрыто в каталоге. Сделайте его видимым.',
    route_eligible_false: 'Место вручную исключено из маршрутов.',
    place_inactive: 'Место выключено.',
    inactive_place: 'Место выключено.',
    place_status_not_active: 'Статус места не active.',
    lifecycle_not_active: 'Место не в активном жизненном цикле.',
    missing_coordinates: 'Нет координат. Добавьте широту и долготу.',
    no_coordinates: 'Нет координат. Добавьте широту и долготу.',
    invalid_coordinates: 'Координаты выглядят неверными.',
    missing_canonical_category: 'Не определена категория места.',
    spam_poi: 'Место похоже на служебную или мусорную точку.',
    duplicate_suspected: 'Место похоже на дубль.',
    critical_field_expired: 'Ключевые данные устарели, нужна проверка.',
    place_archived: 'Место в архиве.',
    no_photo: 'Нет фото.',
    no_address: 'Нет адреса.',
    no_description: 'Нет описания.',
    low_quality: 'Низкое качество карточки места.',
  }
  return map[code] ?? `Техническая причина: ${humanizeCode(code)}.`
}

const routeStatusText = (status?: string) => {
  const map: Record<string, string> = {
    complete: 'полный маршрут',
    partial: 'неполный маршрут',
    failed: 'не собран',
    active: 'активен',
    published: 'опубликован',
  }
  return status ? map[status] ?? humanizeCode(status) : '—'
}

const humanizeCode = (code: string) => code.replace(/[_-]+/g, ' ')

const formatScore = (score: number | null) => {
  if (score === null || score === undefined) return '—'
  return score <= 1 ? `${Math.round(score * 100)}%` : String(score)
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

const ReasonList = ({ reasons, empty }: { reasons: string[]; empty: string }) => {
  if (!reasons.length) return <span className="admin-muted">{empty}</span>
  return (
    <ul className="admin-muted" style={{ margin: 0, paddingLeft: 18 }}>
      {reasons.map((reason) => <li key={reason}>{reasonText(reason)}</li>)}
    </ul>
  )
}

const DryRunMiniMap = ({ points }: { points: DryRunCandidate[] }) => {
  const mapped = useMemo(() => mapPoints(points), [points])
  if (!mapped.length) return <div className="admin-muted">Для мини-карты нет координат выбранных точек.</div>
  return (
    <section className="admin-metric-card" style={{ marginBottom: 16 }}>
      <h3>Мини-карта маршрута</h3>
      <svg viewBox="0 0 100 100" style={{ width: '100%', minHeight: 260, background: '#202124', borderRadius: 8 }} role="img" aria-label="Предварительная карта маршрута">
        <path d="M0 20 H100 M0 40 H100 M0 60 H100 M0 80 H100 M20 0 V100 M40 0 V100 M60 0 V100 M80 0 V100" stroke="rgba(255,255,255,.12)" strokeWidth="0.5" />
        {mapped.length > 1 ? <path d={pathFrom(mapped)} fill="none" stroke="#7cc7ff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /> : null}
        {mapped.map((point, index) => (
          <g key={point.place_id} transform={`translate(${point.x} ${point.y})`}>
            <circle r="4.8" fill="#fff" stroke="#0066cc" strokeWidth="1.5" />
            <text textAnchor="middle" dominantBaseline="central" fill="#0066cc" fontSize="4" fontWeight="800">{index + 1}</text>
          </g>
        ))}
      </svg>
      <p className="admin-muted">Номера показывают порядок точек в будущем маршруте.</p>
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
  const [draft, setDraft] = useState<RouteDraft | null>(null)
  const [published, setPublished] = useState<RoutePublishResponse | null>(null)
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

  const dryRunBody = (): Record<string, unknown> => {
    const body: Record<string, unknown> = {
      city_slug: citySlug, duration_min: duration, route_mode: 'walk',
      interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
    }
    if (budget !== '') body.budget_level = Number(budget)
    if (startLat && startLng) { body.start_lat = Number(startLat); body.start_lng = Number(startLng) }
    return body
  }

  const run = async () => {
    if (!citySlug) {
      setError('Выберите город для проверки.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      setDraft(null)
      setPublished(null)
      setResult(await adminPost<DryRunResponse>('/admin/routes/dry-run', dryRunBody()))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(false) }
  }

  const createDraft = async () => {
    setBusy(true)
    setError(null)
    try {
      const response = await adminPost<RouteDraftGenerationResponse>('/admin/routes/drafts/generate', dryRunBody())
      setDraft(response.draft)
      setResult(response.dry_run)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(false) }
  }

  const publishDraft = async () => {
    if (!draft || published) return
    setBusy(true)
    setError(null)
    try {
      setPublished(await adminPost<RoutePublishResponse>(`/admin/routes/drafts/${draft.draft_id}/publish`, {}))
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

  const canSaveDraft = Boolean(result && result.counts.selected_places > 0)

  return (
    <div>
      <h2 className="admin-page-title">Маршруты → проверка сборки</h2>
      <div className="admin-filters">
        <select value={citySlug} onChange={(e) => setCitySlug(e.target.value)} aria-label="Город dry-run">
          <option value="">Город</option>
          {cities.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
        <input type="number" value={duration} onChange={(e) => setDuration(Number(e.target.value))} placeholder="минуты" />
        <input value={budget} onChange={(e) => setBudget(e.target.value === '' ? '' : Number(e.target.value))} placeholder="бюджет 1-4" />
        <input value={startLat} onChange={(e) => setStartLat(e.target.value)} placeholder="широта старта" />
        <input value={startLng} onChange={(e) => setStartLng(e.target.value)} placeholder="долгота старта" />
        <input value={interests} onChange={(e) => setInterests(e.target.value)} placeholder="интересы через запятую" />
        <button type="button" className="admin-btn" disabled={busy || !citySlug} onClick={run}>{busy ? '…' : 'Проверить сборку'}</button>
        {result && <button type="button" className="admin-btn admin-btn-sm" onClick={downloadJson}>Скачать тех. отчет</button>}
      </div>
      {error && <AdminError message={error} />}
      {result && (
        <div>
          <section className="admin-metric-card" style={{ marginBottom: 16 }}>
            <h3>Проверка #{result.generation_run_id}</h3>
            <div className="admin-metrics-grid admin-metrics-small">
              <div className="admin-metric-card"><div className="admin-metric-value">{result.counts.total_candidates}</div><div className="admin-metric-label">найдено мест</div></div>
              <div className="admin-metric-card"><div className="admin-metric-value">{result.counts.eligible_candidates}</div><div className="admin-metric-label">подходит</div></div>
              <div className="admin-metric-card"><div className="admin-metric-value">{result.counts.selected_places}</div><div className="admin-metric-label">выбрано</div></div>
            </div>
            <p>{canSaveDraft ? 'Можно сохранить черновик маршрута и затем опубликовать его.' : 'Сохранять пока нечего: система не выбрала ни одной точки.'}</p>
          </section>
          <div className="admin-filters">
            <button type="button" className="admin-btn admin-btn-sm" disabled={busy || !canSaveDraft} onClick={createDraft}>Сохранить черновик</button>
            <button type="button" className="admin-btn admin-btn-sm" disabled={busy || !draft || Boolean(published)} onClick={publishDraft}>Опубликовать маршрут</button>
            {draft ? <span className="admin-muted">Черновик #{draft.draft_id}: {draft.points.length} точек, {routeStatusText(draft.route_status)}</span> : null}
            {published ? <span className="admin-muted">Маршрут опубликован: #{published.route.id}, {published.route.slug}</span> : null}
          </div>
          <DryRunMiniMap points={result.selected_places} />
          {result.quality ? (
            <section className="admin-metric-card" style={{ marginBottom: 16 }}>
              <div className="admin-metric-value">{result.quality.score_percent}%</div>
              <div className="admin-metric-label">Качество маршрута</div>
              <p><span className={qualityClass(result.quality.status)}>{qualityLabel(result.quality.status)}</span></p>
              {result.quality.partial_reason ? <p className="admin-muted">Причина: {warningText(result.quality.partial_reason)}</p> : null}
              {result.quality.warnings.length > 0 ? (
                <ul className="admin-muted">
                  {result.quality.warnings.map((warning) => <li key={warning}>{warningText(warning)}</li>)}
                </ul>
              ) : <p className="admin-muted">Критичных предупреждений нет.</p>}
              {Object.keys(result.quality.breakdown).length > 0 ? (
                <details className="admin-muted">
                  <summary>Технические показатели</summary>
                  <pre style={{ fontSize: 11 }}>{JSON.stringify(result.quality.breakdown, null, 2)}</pre>
                </details>
              ) : null}
            </section>
          ) : null}
          <h3>Выбрано в маршрут</h3>
          <table className="admin-table"><thead><tr><th>Место</th><th>Кат.</th><th>Оценка</th><th>Почему выбрано</th></tr></thead><tbody>
            {result.selected_places.map((p) => <tr key={p.place_id}><td>{p.title}</td><td>{p.category}</td><td>{formatScore(p.score)}</td><td><ReasonList reasons={p.selection_reasons} empty="Подходит" /></td></tr>)}
          </tbody></table>
          <h3>Не вошли в маршрут</h3>
          <p className="admin-muted">Здесь показано, что нужно исправить, чтобы место могло попасть в маршрут.</p>
          <table className="admin-table"><thead><tr><th>Место</th><th>Кат.</th><th>Что мешает</th></tr></thead><tbody>
            {result.rejected_candidates.slice(0, 50).map((p) => <tr key={p.place_id}><td>{p.title}</td><td>{p.category}</td><td><ReasonList reasons={p.rejection_reasons} empty="Нет явной причины" /></td></tr>)}
          </tbody></table>
          {result.rejected_candidates.length > 50 ? <p className="admin-muted">Показаны первые 50 отклоненных мест из {result.rejected_candidates.length}.</p> : null}
        </div>
      )}
    </div>
  )
}
