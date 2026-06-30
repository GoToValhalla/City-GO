import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPatch, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'
import './AdminCoverageGaps.css'

type CoverageGapRow = {
  id: number
  city_slug: string | null
  name: string
  expected_category: string
  expected_scope: string
  expected_route_policy: string
  status: string
  gap_reason?: string | null
  review_notes?: string | null
  matched_place_id?: number | null
  matched_place_title?: string | null
}

type CoverageGapPayload = {
  items: CoverageGapRow[]
  total: number
  summary: { total: number; matched: number; unresolved: number; critical_unresolved: number }
}

type OperationStatus = {
  freshness: 'fresh' | 'stale' | 'running' | 'failed_stale' | string
  is_stale: boolean
  last_snapshot_at?: string | null
  latest_operation?: { operation_id: number; status: string; error?: string | null; updated_at?: string | null } | null
}

const freshnessLabel: Record<string, string> = {
  fresh: 'Актуально',
  stale: 'Устарело',
  running: 'Обновляется',
  failed_stale: 'Ошибка обновления',
}

const statusLabel: Record<string, string> = {
  matched: 'Найдено',
  missing: 'Не найдено',
  needs_review: 'Нужна проверка',
  source_absent: 'Нет в источнике',
  out_of_scope: 'Вне области',
  tag_unsupported: 'Тег не поддержан',
  rejected_policy: 'Скрыто политикой',
  duplicate: 'Дубликат',
}

const reasonLabel: Record<string, string> = {
  outside_bbox: 'Вне bbox',
  unsupported_tag: 'Тег не поддержан',
  source_absent: 'Нет в источнике',
  hidden_by_policy: 'Скрыто политикой',
  missing_name: 'Нет названия',
  missing_coordinates: 'Нет координат',
  duplicate_candidate: 'Возможный дубль',
  not_imported_scope: 'Не импортируется scope',
  not_visible_in_catalog: 'Не видно в каталоге',
  not_route_eligible: 'Не подходит для маршрутов',
}

const badgeClass = (freshness?: string) => {
  if (freshness === 'fresh') return 'admin-badge pub-published'
  if (freshness === 'running') return 'admin-badge pub-needs_review'
  if (freshness === 'failed_stale') return 'admin-badge pub-hidden'
  return 'admin-badge pub-draft'
}

const valueOrEmpty = (params: URLSearchParams, key: string) => params.get(key) ?? ''

export const AdminCoverageGapsSnapshotPage = () => {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<CoverageGapPayload | null>(null)
  const [status, setStatus] = useState<OperationStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const citySlug = valueOrEmpty(params, 'city_slug')

  const query = useMemo(() => {
    const api = new URLSearchParams()
    for (const key of ['city_slug', 'status', 'gap_reason', 'expected_category']) {
      const value = params.get(key)
      if (value) api.set(key, value)
    }
    api.set('limit', '100')
    api.set('refresh', 'false')
    return api.toString()
  }, [params])

  const loadStatus = useCallback(async () => {
    const api = new URLSearchParams()
    if (citySlug) api.set('city_slug', citySlug)
    setStatus(await adminGet<OperationStatus>(`/admin/background-operations/coverage-gaps/status?${api.toString()}`))
  }, [citySlug])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [payload] = await Promise.all([
        adminGet<CoverageGapPayload>(`/admin/coverage-gaps?${query}`),
        loadStatus(),
      ])
      setData(payload)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить coverage snapshot')
    } finally {
      setLoading(false)
    }
  }, [query, loadStatus])

  useEffect(() => { void load() }, [load])
  useEffect(() => {
    if (status?.freshness !== 'running') return
    const timer = window.setInterval(() => { void loadStatus() }, 3000)
    return () => window.clearInterval(timer)
  }, [status?.freshness, loadStatus])

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    next.set('tab', 'gaps')
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const api = new URLSearchParams()
      if (citySlug) api.set('city_slug', citySlug)
      const operation = await adminPost<{ operation_id: number; status: string }>(`/admin/background-operations/coverage-gaps/refresh?${api.toString()}`, citySlug ? { city_slug: citySlug } : {})
      setStatus({ freshness: operation.status === 'completed' ? 'fresh' : 'running', is_stale: true, latest_operation: { operation_id: operation.operation_id, status: operation.status } })
      await loadStatus()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось поставить refresh в очередь')
    } finally {
      setRefreshing(false)
    }
  }

  const mark = async (row: CoverageGapRow, nextStatus: string, gapReason?: string | null) => {
    setUpdatingId(row.id)
    setError(null)
    try {
      await adminPatch(`/admin/coverage-gaps/${row.id}`, { status: nextStatus, gap_reason: gapReason ?? null, review_notes: `Admin coverage action: ${nextStatus}` })
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось обновить строку')
    } finally {
      setUpdatingId(null)
    }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return <AdminEmpty message="Нет данных" />

  return <div>
    <div className="admin-page-header admin-gap-header">
      <div>
        <div className="admin-kicker">Data Coverage Assurance</div>
        <h2 className="admin-page-title">Пропущенные must-have места</h2>
        <p className="admin-page-subtitle">Экран читает сохранённый snapshot. Кнопка обновления ставит тяжёлую сверку в background job.</p>
      </div>
      <div className="admin-action-toolbar admin-gap-header-actions">
        <span className={badgeClass(status?.freshness)}>{freshnessLabel[status?.freshness ?? ''] ?? status?.freshness ?? 'Нет snapshot'}</span>
        <button className="admin-btn admin-btn-primary" type="button" disabled={refreshing || status?.freshness === 'running'} onClick={() => void refresh()}>{status?.freshness === 'running' ? 'Обновляется...' : 'Обновить snapshot'}</button>
      </div>
    </div>

    <section className="admin-help-panel admin-gap-help">
      <div className="admin-help-title">Snapshot</div>
      <p>Последний snapshot: <strong>{status?.last_snapshot_at ? new Date(status.last_snapshot_at).toLocaleString('ru-RU') : 'ещё не создан'}</strong></p>
      {status?.latest_operation ? <p>Операция #{status.latest_operation.operation_id}: <strong>{status.latest_operation.status}</strong>{status.latest_operation.error ? ` · ${status.latest_operation.error}` : ''}</p> : <p className="admin-muted">Операций обновления ещё не было.</p>}
    </section>

    <div className="admin-metrics-grid">
      <div className="admin-metric-card"><div className="admin-metric-value">{data.summary.total}</div><div className="admin-metric-label">Всего ожидается</div></div>
      <div className="admin-metric-card"><div className="admin-metric-value">{data.summary.matched}</div><div className="admin-metric-label">Найдено</div></div>
      <div className="admin-metric-card"><div className="admin-metric-value">{data.summary.unresolved}</div><div className="admin-metric-label">Не закрыто</div></div>
      <div className="admin-metric-card"><div className="admin-metric-value">{data.summary.critical_unresolved}</div><div className="admin-metric-label">Критично</div></div>
    </div>

    <div className="admin-toolbar admin-gap-filters">
      <input placeholder="city_slug" value={citySlug} onChange={(e) => setFilter('city_slug', e.target.value)} />
      <input placeholder="status" value={valueOrEmpty(params, 'status')} onChange={(e) => setFilter('status', e.target.value)} />
      <input placeholder="gap_reason" value={valueOrEmpty(params, 'gap_reason')} onChange={(e) => setFilter('gap_reason', e.target.value)} />
      <input placeholder="category" value={valueOrEmpty(params, 'expected_category')} onChange={(e) => setFilter('expected_category', e.target.value)} />
    </div>

    {!data.items.length ? <AdminEmpty message="По текущим фильтрам пропусков нет" /> : <div className="admin-gap-list">
      {data.items.map((row) => <article className="admin-gap-card" key={row.id}>
        <div className="admin-gap-card-head"><div><h3>{row.name}</h3><p>{row.city_slug ?? 'город не указан'} · {row.expected_category} · {row.expected_scope}</p></div><span className="admin-badge pub-draft">{statusLabel[row.status] ?? row.status}</span></div>
        <div className="admin-gap-details">
          <p><strong>Политика:</strong> {row.expected_route_policy}</p>
          <p><strong>Причина:</strong> {row.gap_reason ? reasonLabel[row.gap_reason] ?? row.gap_reason : '—'}</p>
          {row.review_notes ? <p><strong>Заметка:</strong> {row.review_notes}</p> : null}
          {row.matched_place_id ? <p><strong>Связано с:</strong> <Link to={`/admin/places/${row.matched_place_id}`}>{row.matched_place_title ?? `место #${row.matched_place_id}`}</Link></p> : null}
        </div>
        <div className="admin-actions-cell">
          <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} onClick={() => void mark(row, 'needs_review', row.gap_reason ?? 'manual_review')}>На проверку</button>
          <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} onClick={() => void mark(row, 'out_of_scope', 'outside_bbox')}>Вне области</button>
          <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} onClick={() => void mark(row, 'source_absent', 'source_absent')}>Нет в источнике</button>
          <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} onClick={() => void mark(row, 'matched', null)}>Закрыть</button>
        </div>
      </article>)}
    </div>}
  </div>
}
