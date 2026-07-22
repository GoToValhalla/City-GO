import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCategorySelect } from './AdminCategorySelect'
import { verificationStatusText } from './adminHumanText'
import { VERIFY_STATUS_OPTIONS } from './adminPlacesPresets'
import { categoryText } from './adminRouteCopy'
import type { AdminCitiesResponse, AdminVerificationQueue, AdminVerificationTask } from './adminTypes'
import { AdminEmpty, AdminLoading, AdminSectionError } from './shared/AdminStates'

type AdminVerificationSummary = {
  needs_recheck: number
  verified_today: number
  unverified: number
  low_confidence: number
}

const PAGE_SIZES = [20, 50, 100]
const DEFAULT_PAGE_SIZE = 50
const DEFAULT_QUEUE_STATUS = 'needs_recheck'
const pageSizeFromQuery = (value: string | null) => PAGE_SIZES.includes(Number(value)) ? Number(value) : DEFAULT_PAGE_SIZE
const offsetFromQuery = (value: string | null) => Number.isInteger(Number(value)) && Number(value) >= 0 ? Number(value) : 0
const confidenceText = (value: number) => value <= 1 ? `${Math.round(value * 100)}%` : `${Math.round(value)}%`
const errorText = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

export const AdminPlaceVerificationsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const citySlug = searchParams.get('city') ?? ''
  const status = searchParams.get('status') ?? DEFAULT_QUEUE_STATUS
  const category = searchParams.get('category') ?? ''
  const limit = pageSizeFromQuery(searchParams.get('limit'))
  const offset = offsetFromQuery(searchParams.get('offset'))
  const [tasks, setTasks] = useState<AdminVerificationTask[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<AdminVerificationSummary | null>(null)
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [queueLoading, setQueueLoading] = useState(true)
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [citiesLoading, setCitiesLoading] = useState(true)
  const [queueError, setQueueError] = useState<string | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [filtersError, setFiltersError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const requestSequence = useRef(0)

  const updateFilters = useCallback((changes: Record<string, string | number | null>) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => {
      const normalized = value === null ? '' : String(value)
      const isDefault = (key === 'limit' && normalized === String(DEFAULT_PAGE_SIZE)) || (key === 'offset' && normalized === '0')
      if (!normalized || isDefault) next.delete(key); else next.set(key, normalized)
    })
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const loadQueue = useCallback(async (requestId: number) => {
    setQueueLoading(true); setQueueError(null)
    const query = new URLSearchParams({ limit: String(limit), offset: String(offset), status })
    if (citySlug) query.set('city_slug', citySlug)
    if (category) query.set('category', category)
    try {
      const queue = await adminGet<AdminVerificationQueue>(`/admin/place-verifications/queue?${query}`, { cache: false, timeoutMs: 8_000 })
      if (requestId !== requestSequence.current) return
      setTasks(Array.isArray(queue.items) ? queue.items : [])
      setTotal(typeof queue.total === 'number' ? queue.total : 0)
    } catch (error) {
      if (requestId === requestSequence.current) {
        setTasks([])
        setTotal(0)
        setQueueError(errorText(error, 'Не удалось загрузить очередь проверки мест'))
      }
    } finally {
      if (requestId === requestSequence.current) setQueueLoading(false)
    }
  }, [citySlug, status, category, limit, offset])

  const loadSummary = useCallback(async (requestId: number) => {
    setSummaryLoading(true); setSummaryError(null)
    try {
      const summary = await adminGet<AdminVerificationSummary>('/admin/place-verifications/summary', { cache: false, timeoutMs: 8_000 })
      if (requestId === requestSequence.current) setStats(summary)
    } catch (error) {
      if (requestId === requestSequence.current) {
        setStats(null)
        setSummaryError(errorText(error, 'Не удалось загрузить сводку проверки мест'))
      }
    } finally {
      if (requestId === requestSequence.current) setSummaryLoading(false)
    }
  }, [])

  const loadCities = useCallback(async (requestId: number) => {
    setCitiesLoading(true); setFiltersError(null)
    try {
      const response = await adminGet<AdminCitiesResponse>('/admin/cities?limit=100', { cache: false, timeoutMs: 8_000 })
      if (requestId === requestSequence.current) setCities(Array.isArray(response.items) ? response.items : [])
    } catch (error) {
      if (requestId === requestSequence.current) setFiltersError(errorText(error, 'Не удалось загрузить список городов'))
    } finally {
      if (requestId === requestSequence.current) setCitiesLoading(false)
    }
  }, [])

  const load = useCallback(() => {
    const requestId = ++requestSequence.current
    setActionError(null)
    void loadQueue(requestId)
    void loadSummary(requestId)
    void loadCities(requestId)
  }, [loadQueue, loadSummary, loadCities])

  useEffect(() => { load(); return () => { requestSequence.current += 1 } }, [load])

  const verify = async (placeId: number, action: string) => {
    if (!window.confirm(`${action === 'exists' ? 'Подтвердить место' : 'Исключить как не найденное'} для места #${placeId}?`)) return
    setBusy(placeId); setActionError(null)
    try {
      await adminPost(`/admin/place-verifications/places/${placeId}/verify`, { action })
      setTasks((current) => current.filter((task) => task.place_id !== placeId))
      setTotal((current) => Math.max(0, current - 1))
      const requestId = ++requestSequence.current
      void loadQueue(requestId)
      void loadSummary(requestSequence.current)
    } catch (error) {
      setActionError(errorText(error, 'Не удалось сохранить результат проверки'))
    } finally {
      setBusy(null)
    }
  }

  const metric = (value: number, label: string, filter: Record<string, string>, muted?: string) => (
    <button type="button" className="admin-metric-card" onClick={() => updateFilters({ ...filter, offset: 0 })}>
      <div className="admin-metric-value">{value}</div><div className="admin-metric-label">{label}</div>
      <span className="admin-muted">{muted ?? 'Открыть выборку →'}</span>
    </button>
  )
  const page = Math.floor(offset / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))
  const sortKeyRaw = searchParams.get('sort') ?? 'title'
  const sortKey = sortKeyRaw === 'confidence' || sortKeyRaw === 'city' || sortKeyRaw === 'title' ? sortKeyRaw : 'title'
  const sortedTasks = useMemo(() => {
    const rows = [...tasks]
    if (sortKey === 'confidence') return rows.sort((a, b) => a.existence_confidence_score - b.existence_confidence_score)
    if (sortKey === 'city') return rows.sort((a, b) => (a.city_slug ?? '').localeCompare(b.city_slug ?? '', 'ru'))
    return rows.sort((a, b) => a.title.localeCompare(b.title, 'ru'))
  }, [tasks, sortKey])
  return <div>
    <h2 className="admin-page-title">Проверка мест ({total})</h2>
    <p className="admin-page-subtitle">По умолчанию показана только ручная очередь перепроверки. Массовая низкая уверенность должна закрываться автоматикой и quality policy, а не руками.</p>
    <section className="admin-section">
      {summaryLoading && !stats && !summaryError && <AdminLoading message="Загрузка сводки проверки…" />}
      {summaryError && <AdminSectionError title="Не удалось загрузить сводку проверки мест" message={summaryError} onRetry={() => void loadSummary(++requestSequence.current)} />}
      {stats && <div className="admin-metrics-grid admin-metrics-small">{metric(stats.needs_recheck, 'В очереди', { status: 'needs_recheck' })}{metric(stats.verified_today, 'Проверено сегодня', { status: 'verified' })}{metric(stats.unverified, 'Не проверено авто', { status: 'unverified' }, 'Автоматизировать →')}{metric(stats.low_confidence, 'Низкая уверенность', { status: 'unverified' }, 'Не разбирать руками')}</div>}
    </section>
    <section className="admin-filter-card admin-filters-sticky">
      <div className="admin-help-title">Фильтры проверки</div>
      {filtersError && <AdminSectionError title="Не удалось загрузить фильтры" message={filtersError} onRetry={() => void loadCities(++requestSequence.current)} />}
      <div className="admin-filters"><select aria-label="Город" value={citySlug} disabled={citiesLoading && cities.length === 0} onChange={(e) => updateFilters({ city: e.target.value, offset: 0 })}><option value="">Все города</option>{cities.map((city) => <option key={city.id} value={city.slug}>{city.name}</option>)}</select><select aria-label="Статус проверки" value={status} onChange={(e) => updateFilters({ status: e.target.value || DEFAULT_QUEUE_STATUS, offset: 0 })}>{VERIFY_STATUS_OPTIONS.filter((option) => option.value).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><AdminCategorySelect value={category} citySlug={citySlug || undefined} onChange={(value) => updateFilters({ category: value, offset: 0 })} includeAll /><select aria-label="Размер страницы" value={limit} onChange={(e) => updateFilters({ limit: Number(e.target.value), offset: 0 })}>{PAGE_SIZES.map((size) => <option key={size} value={size}>{size} на страницу</option>)}</select><select aria-label="Сортировка" value={searchParams.get('sort') ?? 'title'} onChange={(e) => updateFilters({ sort: e.target.value, offset: 0 })}><option value="title">По названию</option><option value="confidence">По уверенности</option><option value="city">По городу</option></select></div>
    </section>
    {actionError && <AdminSectionError title="Не удалось сохранить результат проверки" message={actionError} />}
    <section className="admin-section">
      {queueError && <AdminSectionError title="Не удалось загрузить очередь проверки мест" message={queueError} onRetry={() => void loadQueue(++requestSequence.current)} />}
      {queueLoading && tasks.length === 0 && !queueError ? <AdminLoading message="Загрузка очереди проверки…" /> : null}
      {!queueLoading && tasks.length === 0 && !queueError ? <AdminEmpty message="Ручная очередь пуста по выбранным фильтрам" /> : null}
      {tasks.length > 0 && <><div className="admin-table-wrap"><table className="admin-table admin-table-stackable"><thead><tr><th>Место</th><th>Город</th><th>Категория</th><th>Адрес</th><th>Статус</th><th>Уверенность</th><th>Действия</th></tr></thead><tbody>{sortedTasks.map((task) => <tr key={task.place_id}><td data-label="Место"><Link to={`/admin/places/${task.place_id}`}>{task.title}</Link></td><td data-label="Город">{task.city_slug ? <Link to={`/admin/cities/${task.city_slug}?tab=verification`}>{task.city_slug}</Link> : '—'}</td><td data-label="Категория">{categoryText(task.category)}</td><td data-label="Адрес">{task.address ?? '—'}</td><td data-label="Статус">{verificationStatusText(task.verification_status)}</td><td data-label="Уверенность">{confidenceText(task.existence_confidence_score)}</td><td data-label="Действия"><button type="button" disabled={busy === task.place_id} onClick={() => void verify(task.place_id, 'exists')} className="admin-btn admin-btn-ok admin-btn-sm">Подтвердить место</button><button type="button" disabled={busy === task.place_id} onClick={() => void verify(task.place_id, 'not_found')} className="admin-btn admin-btn-danger admin-btn-sm">Исключить</button></td></tr>)}</tbody></table></div><div className="admin-actions-cell"><button type="button" className="admin-btn admin-btn-sm" disabled={offset === 0} onClick={() => updateFilters({ offset: Math.max(0, offset - limit) })}>Назад</button><span className="admin-muted">Стр. {page} / {pages} · всего {total}</span><button type="button" className="admin-btn admin-btn-sm" disabled={offset + limit >= total} onClick={() => updateFilters({ offset: offset + limit })}>Вперёд</button></div></>}
    </section>
  </div>
}
