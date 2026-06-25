import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPatch, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'
import './AdminCoverageGaps.css'

type Row = {
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

type Payload = {
  items: Row[]
  total: number
  summary: {
    total: number
    matched: number
    unresolved: number
    critical_unresolved: number
    by_status?: Record<string, number>
    by_gap_reason?: Record<string, number>
    by_expected_category?: Record<string, number>
  }
  filters?: Record<string, string | null>
}

type Option = { value: string; label: string }

const statusOptions: Option[] = [
  { value: '', label: 'Все статусы' },
  { value: 'unresolved', label: 'Не закрыто' },
  { value: 'critical', label: 'Критично' },
  { value: 'missing', label: 'Не найдено' },
  { value: 'matched', label: 'Найдено' },
  { value: 'needs_review', label: 'Нужна проверка' },
  { value: 'source_absent', label: 'Нет в источнике' },
  { value: 'out_of_scope', label: 'Вне области импорта' },
  { value: 'tag_unsupported', label: 'Неподдерживаемый тег' },
  { value: 'rejected_policy', label: 'Скрыто политикой' },
  { value: 'duplicate', label: 'Дубликат' },
]

const reasonOptions: Option[] = [
  { value: '', label: 'Все причины' },
  { value: 'outside_bbox', label: 'Вне bbox города' },
  { value: 'unsupported_tag', label: 'Тег не поддержан' },
  { value: 'source_absent', label: 'Нет в источнике' },
  { value: 'hidden_by_policy', label: 'Скрыто политикой каталога' },
  { value: 'missing_name', label: 'Нет названия' },
  { value: 'missing_coordinates', label: 'Нет координат' },
  { value: 'duplicate_candidate', label: 'Возможный дубль' },
  { value: 'not_imported_scope', label: 'Не импортируется этим scope' },
  { value: 'not_visible_in_catalog', label: 'Не видно в каталоге' },
  { value: 'not_route_eligible', label: 'Не подходит для маршрутов' },
]

const categoryOptions: Option[] = [
  { value: '', label: 'Все категории' },
  { value: 'culture', label: 'Культура' },
  { value: 'food', label: 'Еда' },
  { value: 'walk', label: 'Прогулка/природа' },
  { value: 'park', label: 'Парк' },
  { value: 'museum', label: 'Музей' },
  { value: 'viewpoint', label: 'Смотровая' },
  { value: 'cafe', label: 'Кафе' },
]

const categoryLabels: Record<string, string> = {
  culture: 'Культура',
  food: 'Еда',
  walk: 'Прогулка/природа',
  park: 'Парк',
  museum: 'Музей',
  viewpoint: 'Смотровая',
  cafe: 'Кафе',
}

const scopeLabels: Record<string, string> = {
  urban_core: 'Центр города',
  food_core: 'Еда и кофе',
  food_wider_center: 'Еда · широкий центр',
  heritage_ring: 'Наследие рядом',
  nature_daytrip: 'Природа / day-trip',
  regional_attractions: 'Региональные точки',
  useful_services: 'Полезные сервисы',
}

const routePolicyLabels: Record<string, string> = {
  must_have: 'Обязательное',
  day_trip: 'Day-trip',
  optional: 'Опционально',
}

const statusLabels = Object.fromEntries(statusOptions.filter((o) => o.value).map((o) => [o.value, o.label])) as Record<string, string>
const reasonLabels = Object.fromEntries(reasonOptions.filter((o) => o.value).map((o) => [o.value, o.label])) as Record<string, string>

const statusHint: Record<string, string> = {
  missing: 'Место ожидается, но пока не найдено в каталоге и источниках.',
  matched: 'Место сопоставлено с каталогом.',
  needs_review: 'Нужна ручная проверка редактора.',
  source_absent: 'Источник не содержит подходящего объекта.',
  out_of_scope: 'Точка лежит вне настроенной области импорта.',
  tag_unsupported: 'Источник вернул объект, но его теги не покрыты таксономией.',
  rejected_policy: 'Кандидат найден, но скрыт текущей политикой видимости.',
  duplicate: 'Есть риск дубля в каталоге.',
}

const reasonAction: Record<string, string> = {
  outside_bbox: 'Расширить bbox/scope или зафиксировать исключение.',
  unsupported_tag: 'Добавить mapping в OSM taxonomy/import profile.',
  source_absent: 'Проверить другой легальный источник или оставить редакторское объяснение.',
  hidden_by_policy: 'Проверить статус места, видимость и route eligibility.',
  missing_name: 'Дополнить название из источника или руками.',
  missing_coordinates: 'Дозаполнить координаты.',
  duplicate_candidate: 'Открыть дубль и выбрать canonical place.',
  not_imported_scope: 'Добавить объект в нужный import scope/profile.',
  not_visible_in_catalog: 'Проверить публикацию/скрытие в каталоге.',
  not_route_eligible: 'Проверить категорию и eligibility для маршрутов.',
}

const metricLink = (label: string, value: number, params: URLSearchParams, patch: Record<string, string>, hint?: string) => {
  const next = new URLSearchParams(params)
  next.set('tab', 'gaps')
  Object.entries(patch).forEach(([key, val]) => val ? next.set(key, val) : next.delete(key))
  return <Link className="admin-metric-card admin-metric-link admin-gap-metric" to={`/admin/coverage?${next.toString()}`} title={hint ?? label}>
    <div className="admin-metric-value">{value}</div>
    <div className="admin-metric-label">{label}</div>
    {hint ? <div className="admin-gap-metric-hint">{hint}</div> : null}
  </Link>
}

const valueOrEmpty = (params: URLSearchParams, key: string) => params.get(key) ?? ''
const labelFor = (map: Record<string, string>, value?: string | null) => value ? (map[value] ?? value) : '—'
const formatRawNote = (note: string) => note
  .replaceAll('Matched but requires review:', 'Найден кандидат, нужна проверка:')
  .replaceAll('No matching place or source observation found inside configured import scopes.', 'Нет совпадения в местах или source observations внутри настроенных import scopes.')
  .replaceAll('reason=hidden_by_policy', 'причина: скрыто политикой')
  .replaceAll('reason=source_absent', 'причина: нет в источнике')
  .replaceAll('distance=', 'расстояние=')
  .replaceAll('name_score=', 'сходство имени=')

const statusClass = (status: string) => {
  if (status === 'matched') return 'pub-published'
  if (status === 'needs_review') return 'pub-needs_review'
  if (status === 'rejected_policy' || status === 'missing' || status === 'source_absent' || status === 'out_of_scope' || status === 'tag_unsupported') return 'pub-hidden'
  if (status === 'duplicate') return 'pub-draft'
  return `pub-${status}`
}

export const AdminCoverageGapsPage = () => {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)

  const query = useMemo(() => {
    const api = new URLSearchParams()
    for (const key of ['city_slug', 'status', 'gap_reason', 'expected_category']) {
      const value = params.get(key)
      if (value) api.set(key, value)
    }
    api.set('limit', '300')
    return api.toString()
  }, [params])

  const load = useCallback((refresh = true) => {
    const api = new URLSearchParams(query)
    api.set('refresh', refresh ? 'true' : 'false')
    setLoading(true)
    setError(null)
    adminGet<Payload>(`/admin/coverage-gaps?${api.toString()}`)
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [query])

  useEffect(() => { load(true) }, [load])

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    next.set('tab', 'gaps')
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }

  const resetFilters = () => {
    const next = new URLSearchParams()
    next.set('tab', 'gaps')
    setParams(next)
  }

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const city = params.get('city_slug')
      await adminPost(`/admin/coverage-gaps/refresh${city ? `?city_slug=${encodeURIComponent(city)}` : ''}`)
      load(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRefreshing(false)
    }
  }

  const mark = async (row: Row, status: string, gap_reason?: string | null) => {
    setUpdatingId(row.id)
    setError(null)
    try {
      await adminPatch(`/admin/coverage-gaps/${row.id}`, {
        status,
        gap_reason: gap_reason ?? null,
        review_notes: `Admin action from Coverage Gaps UI: ${status}${gap_reason ? ` / ${gap_reason}` : ''}`,
      })
      // После ручного действия не запускаем повторную авто-сверку, иначе только что выставленный
      // редакторский статус может быть сразу перезаписан источниками.
      load(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setUpdatingId(null)
    }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return <AdminEmpty message="Нет данных" />

  const citySlug = valueOrEmpty(params, 'city_slug')
  const activeFilters = ['city_slug', 'status', 'gap_reason', 'expected_category'].filter((key) => valueOrEmpty(params, key)).length

  return <div>
    <div className="admin-page-header admin-gap-header">
      <div>
        <div className="admin-kicker">Data Coverage Assurance</div>
        <h2 className="admin-page-title">Пропущенные must-have места</h2>
        <p className="admin-page-subtitle">Сверка важных точек с каталогом, import scopes и source observations. Цель — понять не только что пропало, но и почему.</p>
      </div>
      <div className="admin-action-toolbar admin-gap-header-actions">
        <button className="admin-btn admin-btn-muted" type="button" onClick={resetFilters} disabled={!activeFilters}>Сбросить фильтры</button>
        <button className="admin-btn admin-btn-primary" type="button" disabled={refreshing} onClick={() => void refresh()}>{refreshing ? 'Сверяем...' : 'Сверить сейчас'}</button>
      </div>
    </div>

    <div className="admin-help-panel admin-gap-help">
      <div className="admin-help-title">Как читать экран</div>
      <ul className="admin-help-list">
        <li><strong>Найдено</strong> — место сопоставлено с каталогом и не требует объяснения.</li>
        <li><strong>Не закрыто</strong> — must-have POI ещё требует решения или объяснения.</li>
        <li><strong>Критично</strong> — влияет на readiness города и качество маршрутов.</li>
      </ul>
    </div>

    <div className="admin-metrics-grid admin-metrics-small">
      {metricLink('Всего', data.summary.total, params, { status: '', gap_reason: '', expected_category: '' }, 'Все must-have записи')}
      {metricLink('Найдено', data.summary.matched, params, { status: 'matched' }, 'Сопоставлено с каталогом')}
      {metricLink('Не закрыто', data.summary.unresolved, params, { status: 'unresolved', gap_reason: '' }, 'Требует решения или объяснения')}
      {metricLink('Критично', data.summary.critical_unresolved, params, { status: 'critical', gap_reason: '' }, 'Блокирует уверенность в готовности города')}
    </div>

    <div className="admin-filter-card">
      <div className="admin-filter-header">
        <div>
          <div className="admin-help-title">Фильтры</div>
          <p className="admin-bulk-hint">Выбранные фильтры сохраняются в URL. Активно: {activeFilters || 0}</p>
        </div>
        {citySlug ? <Link className="admin-btn admin-btn-sm" to={`/admin/coverage?tab=gaps&city_slug=${encodeURIComponent(citySlug)}`}>Только {citySlug}</Link> : null}
      </div>
      <div className="admin-filter-grid">
        <label className="admin-field">Город
          <input value={citySlug} onChange={(e) => setFilter('city_slug', e.target.value.trim())} placeholder="Например: kutaisi" />
        </label>
        <label className="admin-field">Статус
          <select value={valueOrEmpty(params, 'status')} onChange={(e) => setFilter('status', e.target.value)}>{statusOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        </label>
        <label className="admin-field">Причина
          <select value={valueOrEmpty(params, 'gap_reason')} onChange={(e) => setFilter('gap_reason', e.target.value)}>{reasonOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        </label>
        <label className="admin-field">Категория
          <select value={valueOrEmpty(params, 'expected_category')} onChange={(e) => setFilter('expected_category', e.target.value)}>{categoryOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        </label>
      </div>
    </div>

    {!data.items.length ? <AdminEmpty message="Список пуст" /> : <div className="admin-table-wrap"><table className="admin-table admin-table-compact admin-gap-table">
      <thead><tr><th>Место</th><th>Ожидание</th><th>Состояние</th><th>Что делать</th><th>Кандидат</th><th>Действия</th></tr></thead>
      <tbody>{data.items.map((row) => {
        const statusLabel = labelFor(statusLabels, row.status)
        const reasonLabel = labelFor(reasonLabels, row.gap_reason)
        const actionText = row.gap_reason ? reasonAction[row.gap_reason] : statusHint[row.status]
        return <tr key={row.id} className={row.expected_route_policy === 'must_have' ? 'admin-row-warning' : ''}>
          <td>
            <strong>{row.name}</strong>
            <div className="admin-muted">{row.city_slug ?? 'город не задан'} · #{row.id}</div>
            {row.review_notes ? <div className="admin-gap-note">{formatRawNote(row.review_notes)}</div> : null}
          </td>
          <td>
            <span className="admin-badge">{labelFor(categoryLabels, row.expected_category)}</span>
            <span className="admin-badge">{labelFor(scopeLabels, row.expected_scope)}</span>
            <span className="admin-badge">{labelFor(routePolicyLabels, row.expected_route_policy)}</span>
          </td>
          <td>
            <Link to={`/admin/coverage?tab=gaps&status=${row.status}`} className={`admin-badge ${statusClass(row.status)}`} title={statusHint[row.status] ?? row.status}>{statusLabel}</Link>
            {row.gap_reason ? <Link className="admin-gap-reason" to={`/admin/coverage?tab=gaps&gap_reason=${row.gap_reason}`}>{reasonLabel}</Link> : null}
          </td>
          <td><div className="admin-gap-action-text">{actionText ?? 'Проверить вручную и зафиксировать решение.'}</div></td>
          <td>{row.matched_place_id ? <Link to={`/admin/places/${row.matched_place_id}`}><strong>{row.matched_place_title ?? `#${row.matched_place_id}`}</strong></Link> : <span className="admin-muted">Нет кандидата</span>}</td>
          <td className="admin-actions-cell">
            {row.city_slug ? <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${row.city_slug}&q=${encodeURIComponent(row.name)}`}>Найти в каталоге</Link> : null}
            <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} type="button" onClick={() => void mark(row, 'needs_review', row.gap_reason ?? 'not_visible_in_catalog')}>На проверку</button>
            <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} type="button" onClick={() => void mark(row, 'source_absent', 'source_absent')}>Нет в источнике</button>
            <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} type="button" onClick={() => void mark(row, 'duplicate', 'duplicate_candidate')}>Дубль</button>
          </td>
        </tr>
      })}</tbody>
    </table></div>}
  </div>
}
