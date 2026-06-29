import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminRouteEligibilityDiagnostics } from './AdminRouteEligibilityDiagnostics'
import { AdminRouteEligibilityTable } from './AdminRouteEligibilityTable'
import type { AdminCitiesResponse } from './adminTypes'
import type { EligibilityResponse, RouteReadinessDiagnostics } from './adminRouteTypes'
import { AdminEmpty, AdminLoading, AdminSectionError } from './shared/AdminStates'

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200]
const errorText = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

export const AdminRouteEligibilityPage = () => {
  const [urlParams] = useSearchParams()
  const [data, setData] = useState<EligibilityResponse | null>(null)
  const [diagnostics, setDiagnostics] = useState<RouteReadinessDiagnostics | null>(null)
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [citySlug, setCitySlug] = useState(urlParams.get('city_slug') ?? urlParams.get('city') ?? '')
  const [eligible, setEligible] = useState('')
  const [readiness, setReadiness] = useState(urlParams.get('readiness') ?? '')
  const [quality, setQuality] = useState(urlParams.get('quality') ?? '')
  const [minQualityScore, setMinQualityScore] = useState(urlParams.get('min_quality_score') ?? '')
  const [issue, setIssue] = useState(urlParams.get('issue') ?? '')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [pageSize, setPageSize] = useState(50)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState({ list: true, diagnostics: false, cities: true })
  const [errors, setErrors] = useState({ list: null as string | null, diagnostics: null as string | null, cities: null as string | null })
  const [bulkAction, setBulkAction] = useState<string | null>(null)
  const [bulkError, setBulkError] = useState<string | null>(null)

  const offset = useMemo(() => (page - 1) * pageSize, [page, pageSize])
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const shownFrom = total === 0 ? 0 : offset + 1
  const shownTo = Math.min(offset + (data?.items.length ?? 0), total)
  const setLoadingKey = useCallback((key: keyof typeof loading, value: boolean) => setLoading((current) => ({ ...current, [key]: value })), [])
  const setErrorKey = useCallback((key: keyof typeof errors, value: string | null) => setErrors((current) => ({ ...current, [key]: value })), [])

  const resetListPosition = () => { setSelected(new Set()); setPage(1) }

  const listPath = useCallback(() => {
    const sp = new URLSearchParams({ limit: String(pageSize), offset: String(offset) })
    if (citySlug) sp.set('city_slug', citySlug)
    if (eligible) sp.set('eligible', eligible)
    if (readiness) sp.set('readiness', readiness)
    if (quality) sp.set('quality', quality)
    if (minQualityScore) sp.set('min_quality_score', minQualityScore)
    if (issue) sp.set('issue', issue)
    return `/admin/routes/eligibility?${sp}`
  }, [citySlug, eligible, readiness, quality, minQualityScore, issue, pageSize, offset])

  const loadList = useCallback(async () => {
    setLoadingKey('list', true); setErrorKey('list', null)
    try { setData(await adminGet<EligibilityResponse>(listPath(), { cache: false })) }
    catch (error) { setErrorKey('list', errorText(error, 'Не удалось загрузить готовность мест')) }
    finally { setLoadingKey('list', false) }
  }, [listPath, setErrorKey, setLoadingKey])

  const loadDiagnostics = useCallback(async () => {
    if (!citySlug) { setDiagnostics(null); setErrorKey('diagnostics', null); return }
    setLoadingKey('diagnostics', true); setErrorKey('diagnostics', null)
    try { setDiagnostics(await adminGet<RouteReadinessDiagnostics>(`/admin/routes/eligibility/${citySlug}`, { cache: false })) }
    catch (error) { setErrorKey('diagnostics', errorText(error, 'Не удалось загрузить диагностику города')) }
    finally { setLoadingKey('diagnostics', false) }
  }, [citySlug, setErrorKey, setLoadingKey])

  const loadCities = useCallback(async () => {
    setLoadingKey('cities', true); setErrorKey('cities', null)
    try { setCities((await adminGet<AdminCitiesResponse>('/admin/cities?limit=100')).items) }
    catch (error) { setErrorKey('cities', errorText(error, 'Не удалось загрузить список городов')) }
    finally { setLoadingKey('cities', false) }
  }, [setErrorKey, setLoadingKey])

  useEffect(() => { void loadCities() }, [loadCities])
  useEffect(() => { void loadList(); void loadDiagnostics() }, [loadList, loadDiagnostics])

  const reloadAll = () => { void loadList(); void loadDiagnostics(); void loadCities() }

  const bulk = async (action: string, label: string) => {
    const ids = [...selected]
    if (!ids.length || bulkAction || !window.confirm(`${label}: ${ids.length} мест?`)) return
    const params = action === 'disable_route' ? { reason: 'eligibility_dashboard' } : {}
    setBulkAction(action); setBulkError(null)
    try {
      await adminPost('/admin/places/bulk/apply', { place_ids: ids, action, params, confirm: true })
      setSelected(new Set())
      await loadList()
    } catch (error) {
      setBulkError(errorText(error, 'Не удалось выполнить массовое действие'))
    } finally { setBulkAction(null) }
  }

  const toggleSelected = (placeId: number) => setSelected((current) => {
    const next = new Set(current)
    if (next.has(placeId)) next.delete(placeId)
    else next.add(placeId)
    return next
  })
  const toggleAllVisible = () => setSelected((current) => {
    const next = new Set(current)
    const visibleIds = (data?.items ?? []).map((item) => item.place_id)
    const allSelected = visibleIds.length > 0 && visibleIds.every((placeId) => next.has(placeId))
    visibleIds.forEach((placeId) => allSelected ? next.delete(placeId) : next.add(placeId))
    return next
  })
  const applyHighQualityPreset = () => { setEligible(''); setReadiness('high_quality'); setQuality('high'); setMinQualityScore('75'); setIssue(''); resetListPosition() }
  const resetFilters = () => { setEligible(''); setReadiness(''); setQuality(''); setMinQualityScore(''); setIssue(''); resetListPosition() }

  return <div>
    <h2 className="admin-page-title">Маршруты → готовность мест</h2>
    <p className="admin-page-subtitle">Отбор мест для каталога и маршрутов по качеству, причинам блокировки и готовности.</p>
    <div className="admin-filters">
      <select value={citySlug} disabled={loading.cities && !cities.length} onChange={(e) => { setCitySlug(e.target.value); resetListPosition() }}><option value="">Все города</option>{cities.map((city) => <option key={city.slug} value={city.slug}>{city.name}</option>)}</select>
      <input placeholder="город" value={citySlug} onChange={(e) => { setCitySlug(e.target.value); resetListPosition() }} />
      <select value={readiness} onChange={(e) => { setReadiness(e.target.value); resetListPosition() }} aria-label="Готовность"><option value="">Готовность: все</option><option value="route_ready">готово для маршрутов</option><option value="catalog_ready">готово для каталога</option><option value="high_quality">высокое качество</option><option value="needs_fix">нужно исправить</option><option value="low_quality">низкое качество</option><option value="placeholder">автоназвания OSM</option></select>
      <select value={eligible} onChange={(e) => { setEligible(e.target.value); resetListPosition() }} aria-label="Флаг маршрутов"><option value="">Маршруты: все</option><option value="true">подтверждены</option><option value="false">не подтверждены</option></select>
      <select value={quality} onChange={(e) => { setQuality(e.target.value); resetListPosition() }} aria-label="Качество"><option value="">Качество: все</option><option value="high">высокое</option><option value="medium">среднее</option><option value="low">низкое</option></select>
      <input inputMode="numeric" placeholder="мин. качество" value={minQualityScore} onChange={(e) => { setMinQualityScore(e.target.value.replace(/\D/g, '').slice(0, 3)); resetListPosition() }} />
      <select value={issue} onChange={(e) => { setIssue(e.target.value); resetListPosition() }} aria-label="Причина"><option value="">Причина: все</option><option value="placeholder_title">автоназвание OSM</option><option value="forbidden_category">запрещенная категория</option><option value="no_coordinates">нет координат</option><option value="no_photo">нет фото</option><option value="no_address">нет адреса</option><option value="no_description">нет описания</option><option value="low_quality">низкое качество</option><option value="unpublished_place">не опубликовано</option><option value="hidden_place">скрыто в каталоге</option></select>
      <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); resetListPosition() }} aria-label="Размер страницы">{PAGE_SIZE_OPTIONS.map((value) => <option key={value} value={value}>{value} на странице</option>)}</select>
      <button type="button" className="admin-btn admin-btn-sm" onClick={reloadAll}>Обновить</button>
      <button type="button" className="admin-btn admin-btn-sm" onClick={applyHighQualityPreset}>Показать высокое качество</button>
      <button type="button" className="admin-btn admin-btn-sm" onClick={resetFilters}>Сбросить фильтры</button>
    </div>
    {errors.cities && <AdminSectionError title="Не удалось загрузить города" message={errors.cities} onRetry={() => void loadCities()} />}
    <section className="admin-bulk-panel">
      <div className="admin-bulk-row"><span className="admin-bulk-title">Массовые действия</span><span className="admin-muted">Выбрано: {selected.size}</span><span className="admin-muted">Показано: {shownFrom}-{shownTo} из {total}</span><button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size || Boolean(bulkAction)} onClick={() => void bulk('enable_route', 'Подтвердить для маршрутов')}>{bulkAction === 'enable_route' ? 'Подтверждаем...' : 'Подтвердить для маршрутов'}</button><button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size || Boolean(bulkAction)} onClick={() => void bulk('disable_route', 'Исключить из маршрутов')}>{bulkAction === 'disable_route' ? 'Исключаем...' : 'Исключить из маршрутов'}</button></div>
      {bulkError ? <AdminSectionError title="Не удалось выполнить массовое действие" message={bulkError} /> : null}
      <p className="admin-bulk-hint">Для массовой публикации сначала включите фильтр “высокое качество” или задайте минимум качества. Действие применяется только к выбранным строкам текущей страницы.</p>
      <div className="admin-bulk-row" aria-label="Пагинация готовности мест"><button type="button" className="admin-btn admin-btn-sm" disabled={page <= 1 || loading.list} onClick={() => setPage((value) => Math.max(1, value - 1))}>Назад</button><span className="admin-muted">Страница {page} из {totalPages}</span><button type="button" className="admin-btn admin-btn-sm" disabled={page >= totalPages || loading.list} onClick={() => setPage((value) => value + 1)}>Вперёд</button></div>
    </section>
    {errors.diagnostics ? <AdminSectionError title="Не удалось загрузить диагностику города" message={errors.diagnostics} onRetry={() => void loadDiagnostics()} /> : diagnostics ? <AdminRouteEligibilityDiagnostics report={diagnostics} /> : loading.diagnostics ? <AdminLoading message="Загрузка диагностики города…" /> : <AdminEmpty message="Выберите город, чтобы увидеть готовность мест для маршрутов" />}
    <section className="admin-section">
      <h3 className="admin-section-title">Места</h3>
      {errors.list ? <AdminSectionError title="Не удалось загрузить готовность мест" message={errors.list} onRetry={() => void loadList()} /> : null}
      {loading.list && !data ? <AdminLoading message="Загрузка готовности мест…" /> : null}
      {loading.list && data ? <AdminLoading message="Обновляем список…" /> : null}
      {!errors.list && data ? <div className="admin-table-wrap"><AdminRouteEligibilityTable items={data.items} selected={selected} onToggle={toggleSelected} onToggleAll={toggleAllVisible} /></div> : null}
    </section>
  </div>
}
