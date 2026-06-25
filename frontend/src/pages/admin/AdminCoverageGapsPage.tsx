import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type CoverageGapItem = {
  id: number
  city_slug: string | null
  city_name: string | null
  slug: string
  name: string
  name_en?: string | null
  name_ru?: string | null
  lat: number
  lng: number
  expected_category: string
  expected_scope: string
  expected_route_policy: string
  significance: string
  source: string
  external_refs: Array<{ type?: string; url?: string }>
  status: string
  gap_reason?: string | null
  review_notes?: string | null
  matched_place_id?: number | null
  matched_place_title?: string | null
  matched_place_slug?: string | null
  matched_place_visible?: boolean | null
  matched_place_route_eligible?: boolean | null
  last_checked_at?: string | null
}

type CoverageSummary = {
  total: number
  matched: number
  unresolved: number
  critical_unresolved: number
  by_status: Record<string, number>
  by_gap_reason: Record<string, number>
  by_expected_category: Record<string, number>
}

type CoverageGapResponse = {
  items: CoverageGapItem[]
  total: number
  offset: number
  limit: number
  summary: CoverageSummary
}

const statusLabels: Record<string, string> = {
  matched: 'Найдено',
  missing: 'Отсутствует',
  needs_review: 'Нужна проверка',
  source_absent: 'Нет в источнике',
  out_of_scope: 'Вне scope',
  tag_unsupported: 'Тег не поддержан',
  rejected_policy: 'Отклонено политикой',
  duplicate: 'Возможный дубль',
}

const gapReasonLabels: Record<string, string> = {
  outside_bbox: 'Вне bbox/scope',
  unsupported_tag: 'Неподдержанный тег',
  source_absent: 'Нет наблюдения источника',
  hidden_by_policy: 'Скрыто политикой',
  missing_name: 'Нет имени',
  duplicate_candidate: 'Кандидат на дубль',
  not_imported_scope: 'Не тот scope',
  not_visible_in_catalog: 'Не видно в каталоге',
  not_route_eligible: 'Не готово к маршрутам',
  none: 'Без проблемы',
}

const categoryLabels: Record<string, string> = {
  culture: 'Культура',
  food: 'Еда',
  walk: 'Прогулка/природа',
  park: 'Парк',
  cafe: 'Кофе',
}

const buildQuery = (params: URLSearchParams, patch: Record<string, string | null>) => {
  const next = new URLSearchParams(params)
  Object.entries(patch).forEach(([key, value]) => {
    if (!value) next.delete(key)
    else next.set(key, value)
  })
  next.delete('offset')
  return next.toString()
}

const apiPath = (params: URLSearchParams) => {
  const apiParams = new URLSearchParams()
  for (const key of ['city_slug', 'status', 'gap_reason', 'expected_category']) {
    const value = params.get(key)
    if (value) apiParams.set(key, value)
  }
  apiParams.set('limit', '300')
  return `/admin/coverage-gaps?${apiParams.toString()}`
}

const filterLink = (params: URLSearchParams, patch: Record<string, string | null>) => `/admin/coverage-gaps?${buildQuery(params, patch)}`

const StatusBadge = ({ value }: { value: string }) => (
  <span className={`admin-badge pub-${value}`}>{statusLabels[value] ?? value}</span>
)

const GapBadge = ({ value }: { value?: string | null }) => (
  <span className="admin-badge">{gapReasonLabels[value || 'none'] ?? value ?? 'Без проблемы'}</span>
)

const MetricCard = ({ label, value, to }: { label: string; value: number; to: string }) => (
  <Link className="admin-metric-card admin-action-card" to={to}>
    <div className="admin-metric-value">{value}</div>
    <div className="admin-metric-label">{label}</div>
  </Link>
)

export const AdminCoverageGapsPage = () => {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<CoverageGapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestPath = useMemo(() => apiPath(params), [params])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    adminGet<CoverageGapResponse>(requestPath)
      .then((response) => { if (active) setData(response) })
      .catch((err: Error) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [requestPath])

  const applyFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('offset')
    setParams(next)
  }

  const refresh = async () => {
    try {
      setRefreshing(true)
      setError(null)
      const city = params.get('city_slug')
      await adminPost(`/admin/coverage-gaps/refresh${city ? `?city_slug=${encodeURIComponent(city)}` : ''}`)
      const response = await adminGet<CoverageGapResponse>(requestPath)
      setData(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return <AdminEmpty message="Нет данных по coverage gaps" />

  const summary = data.summary

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h2 className="admin-page-title">Coverage gaps</h2>
          <p className="admin-page-subtitle">Must-have места, которые City GO обязан найти или объяснить. Каждое число открывает точный набор.</p>
        </div>
        <button className="admin-btn admin-btn-primary" type="button" onClick={() => void refresh()} disabled={refreshing}>
          {refreshing ? 'Обновляем...' : 'Сверить сейчас'}
        </button>
      </div>

      <div className="admin-metrics-grid admin-metrics-small">
        <MetricCard label="Всего must-have" value={summary.total} to="/admin/coverage-gaps" />
        <MetricCard label="Найдено" value={summary.matched} to={filterLink(params, { status: 'matched' })} />
        <MetricCard label="Не закрыто" value={summary.unresolved} to={filterLink(params, { status: null })} />
        <MetricCard label="Критичных gap" value={summary.critical_unresolved} to={filterLink(params, { status: 'needs_review' })} />
      </div>

      <section className="admin-filter-card">
        <div className="admin-filter-header">
          <div>
            <strong>Фильтры</strong>
            <div className="admin-muted">Город, статус, причина и ожидаемая категория сохраняются в URL.</div>
          </div>
          <Link className="admin-btn admin-btn-sm" to="/admin/coverage-gaps">Сбросить</Link>
        </div>
        <div className="admin-filter-grid">
          <label className="admin-field">Город
            <input value={params.get('city_slug') ?? ''} onChange={(event) => applyFilter('city_slug', event.target.value.trim())} placeholder="kutaisi" />
          </label>
          <label className="admin-field">Статус
            <select value={params.get('status') ?? ''} onChange={(event) => applyFilter('status', event.target.value)}>
              <option value="">Все</option>
              {Object.entries(statusLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
            </select>
          </label>
          <label className="admin-field">Причина
            <select value={params.get('gap_reason') ?? ''} onChange={(event) => applyFilter('gap_reason', event.target.value)}>
              <option value="">Все</option>
              {Object.entries(gapReasonLabels).filter(([value]) => value !== 'none').map(([value, label]) => <option value={value} key={value}>{label}</option>)}
            </select>
          </label>
          <label className="admin-field">Категория
            <select value={params.get('expected_category') ?? ''} onChange={(event) => applyFilter('expected_category', event.target.value)}>
              <option value="">Все</option>
              {Object.entries(categoryLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
            </select>
          </label>
        </div>
      </section>

      <div className="admin-status-strip">
        {Object.entries(summary.by_status).map(([status, count]) => (
          <Link className="admin-badge" to={filterLink(params, { status })} key={status}>{statusLabels[status] ?? status}: {count}</Link>
        ))}
        {Object.entries(summary.by_gap_reason).filter(([reason]) => reason !== 'none').map(([reason, count]) => (
          <Link className="admin-badge" to={filterLink(params, { gap_reason: reason })} key={reason}>{gapReasonLabels[reason] ?? reason}: {count}</Link>
        ))}
      </div>

      {!data.items.length ? <AdminEmpty message="По выбранным фильтрам gaps не найдены" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Место</th>
                <th>Город</th>
                <th>Ожидание</th>
                <th>Статус</th>
                <th>Причина</th>
                <th>Матч</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.name}</strong>
                    <div className="admin-muted">{item.slug}</div>
                    <div className="admin-muted">{item.lat.toFixed(5)}, {item.lng.toFixed(5)}</div>
                  </td>
                  <td>
                    {item.city_slug ? <Link to={`/admin/cities/${item.city_slug}`}>{item.city_name ?? item.city_slug}</Link> : '—'}
                    <div className="admin-muted">{item.city_slug}</div>
                  </td>
                  <td>
                    <span className="admin-badge">{categoryLabels[item.expected_category] ?? item.expected_category}</span>
                    <span className="admin-badge">{item.expected_scope}</span>
                    <span className="admin-badge">{item.expected_route_policy}</span>
                    <div className="admin-muted">{item.significance}</div>
                  </td>
                  <td><StatusBadge value={item.status} /></td>
                  <td>
                    <GapBadge value={item.gap_reason} />
                    {item.review_notes ? <div className="admin-muted">{item.review_notes}</div> : null}
                  </td>
                  <td>
                    {item.matched_place_id ? (
                      <>
                        <Link to={`/admin/places/${item.matched_place_id}`}><strong>{item.matched_place_title ?? `#${item.matched_place_id}`}</strong></Link>
                        <div className="admin-muted">Каталог: {item.matched_place_visible ? 'да' : 'нет'} · Маршрут: {item.matched_place_route_eligible ? 'да' : 'нет'}</div>
                      </>
                    ) : <span className="admin-muted">Не сопоставлено</span>}
                  </td>
                  <td className="admin-actions-cell">
                    {item.city_slug ? <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${item.city_slug}&q=${encodeURIComponent(item.name)}`}>Искать место</Link> : null}
                    {item.external_refs?.[0]?.url ? <a className="admin-btn admin-btn-sm" href={item.external_refs[0].url} target="_blank" rel="noreferrer">Источник</a> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
