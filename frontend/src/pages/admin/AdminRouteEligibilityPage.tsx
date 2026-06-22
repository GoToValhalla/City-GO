import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminRouteEligibilityDiagnostics } from './AdminRouteEligibilityDiagnostics'
import { AdminRouteEligibilityTable } from './AdminRouteEligibilityTable'
import type { AdminCitiesResponse } from './adminTypes'
import type { EligibilityResponse, RouteReadinessDiagnostics } from './adminRouteTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200]

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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const offset = useMemo(() => (page - 1) * pageSize, [page, pageSize])
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const shownFrom = total === 0 ? 0 : offset + 1
  const shownTo = Math.min(offset + (data?.items.length ?? 0), total)

  const resetListPosition = () => {
    setSelected(new Set())
    setPage(1)
  }

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const sp = new URLSearchParams({ limit: String(pageSize), offset: String(offset) })
    if (citySlug) sp.set('city_slug', citySlug)
    if (eligible) sp.set('eligible', eligible)
    if (readiness) sp.set('readiness', readiness)
    if (quality) sp.set('quality', quality)
    if (minQualityScore) sp.set('min_quality_score', minQualityScore)
    if (issue) sp.set('issue', issue)
    Promise.all([
      adminGet<EligibilityResponse>(`/admin/routes/eligibility?${sp}`),
      citySlug ? adminGet<RouteReadinessDiagnostics>(`/admin/routes/eligibility/${citySlug}`) : Promise.resolve(null),
    ])
      .then(([rows, report]) => {
        setData(rows)
        setDiagnostics(report)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [citySlug, eligible, readiness, quality, minQualityScore, issue, pageSize, offset])

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((r) => setCities(r.items)).catch(() => {})
  }, [])

  useEffect(() => {
    void Promise.resolve().then(load)
  }, [load])

  const bulk = async (action: string, label: string) => {
    const ids = [...selected]
    if (!ids.length || !window.confirm(`${label}: ${ids.length} мест?`)) return
    const params = action === 'disable_route' ? { reason: 'eligibility_dashboard' } : {}
    await adminPost('/admin/places/bulk/apply', { place_ids: ids, action, params, confirm: true })
    setSelected(new Set())
    load()
  }

  const toggleSelected = (placeId: number) => {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(placeId)) {
        next.delete(placeId)
      } else {
        next.add(placeId)
      }
      return next
    })
  }

  const toggleAllVisible = () => {
    const visibleIds = (data?.items ?? []).map((item) => item.place_id)
    setSelected((current) => {
      const next = new Set(current)
      const allSelected = visibleIds.length > 0 && visibleIds.every((placeId) => next.has(placeId))
      if (allSelected) {
        visibleIds.forEach((placeId) => next.delete(placeId))
      } else {
        visibleIds.forEach((placeId) => next.add(placeId))
      }
      return next
    })
  }

  const applyHighQualityPreset = () => {
    setEligible('')
    setReadiness('high_quality')
    setQuality('high')
    setMinQualityScore('75')
    setIssue('')
    resetListPosition()
  }

  const resetFilters = () => {
    setEligible('')
    setReadiness('')
    setQuality('')
    setMinQualityScore('')
    setIssue('')
    resetListPosition()
  }

  if (loading && !data) return <AdminLoading />
  if (error) return <AdminError message={error} />

  return (
    <div>
      <h2 className="admin-page-title">Маршруты → готовность мест</h2>
      <p className="admin-page-subtitle">Отбор мест для каталога и маршрутов по качеству, причинам блокировки и готовности.</p>
      <div className="admin-filters">
        <select value={citySlug} onChange={(e) => { setCitySlug(e.target.value); resetListPosition() }}>
          <option value="">Все города</option>
          {cities.map((city) => <option key={city.slug} value={city.slug}>{city.name}</option>)}
        </select>
        <input placeholder="город" value={citySlug} onChange={(e) => { setCitySlug(e.target.value); resetListPosition() }} />
        <select value={readiness} onChange={(e) => { setReadiness(e.target.value); resetListPosition() }} aria-label="Готовность">
          <option value="">Готовность: все</option>
          <option value="route_ready">готово для маршрутов</option>
          <option value="catalog_ready">готово для каталога</option>
          <option value="high_quality">высокое качество</option>
          <option value="needs_fix">нужно исправить</option>
          <option value="low_quality">низкое качество</option>
          <option value="placeholder">автоназвания OSM</option>
        </select>
        <select value={eligible} onChange={(e) => { setEligible(e.target.value); resetListPosition() }} aria-label="Флаг маршрутов">
          <option value="">Маршруты: все</option>
          <option value="true">подтверждены</option>
          <option value="false">не подтверждены</option>
        </select>
        <select value={quality} onChange={(e) => { setQuality(e.target.value); resetListPosition() }} aria-label="Качество">
          <option value="">Качество: все</option>
          <option value="high">высокое</option>
          <option value="medium">среднее</option>
          <option value="low">низкое</option>
        </select>
        <input
          inputMode="numeric"
          placeholder="мин. качество"
          value={minQualityScore}
          onChange={(e) => { setMinQualityScore(e.target.value.replace(/\D/g, '').slice(0, 3)); resetListPosition() }}
        />
        <select value={issue} onChange={(e) => { setIssue(e.target.value); resetListPosition() }} aria-label="Причина">
          <option value="">Причина: все</option>
          <option value="placeholder_title">автоназвание OSM</option>
          <option value="forbidden_category">запрещенная категория</option>
          <option value="no_coordinates">нет координат</option>
          <option value="no_photo">нет фото</option>
          <option value="no_address">нет адреса</option>
          <option value="no_description">нет описания</option>
          <option value="low_quality">низкое качество</option>
          <option value="unpublished_place">не опубликовано</option>
          <option value="hidden_place">скрыто в каталоге</option>
        </select>
        <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); resetListPosition() }} aria-label="Размер страницы">
          {PAGE_SIZE_OPTIONS.map((value) => <option key={value} value={value}>{value} на странице</option>)}
        </select>
        <button type="button" className="admin-btn admin-btn-sm" onClick={load}>Обновить</button>
        <button type="button" className="admin-btn admin-btn-sm" onClick={applyHighQualityPreset}>Показать высокое качество</button>
        <button type="button" className="admin-btn admin-btn-sm" onClick={resetFilters}>Сбросить фильтры</button>
      </div>
      <section className="admin-bulk-panel">
        <div className="admin-bulk-row">
          <span className="admin-bulk-title">Массовые действия</span>
          <span className="admin-muted">Выбрано: {selected.size}</span>
          <span className="admin-muted">Показано: {shownFrom}-{shownTo} из {total}</span>
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size} onClick={() => void bulk('enable_route', 'Подтвердить для маршрутов')}>Подтвердить для маршрутов</button>
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size} onClick={() => void bulk('disable_route', 'Исключить из маршрутов')}>Исключить из маршрутов</button>
        </div>
        <p className="admin-bulk-hint">Для массовой публикации сначала включите фильтр “высокое качество” или задайте минимум качества. Действие применяется только к выбранным строкам текущей страницы.</p>
        <div className="admin-bulk-row" aria-label="Пагинация готовности мест">
          <button type="button" className="admin-btn admin-btn-sm" disabled={page <= 1 || loading} onClick={() => setPage((value) => Math.max(1, value - 1))}>Назад</button>
          <span className="admin-muted">Страница {page} из {totalPages}</span>
          <button type="button" className="admin-btn admin-btn-sm" disabled={page >= totalPages || loading} onClick={() => setPage((value) => value + 1)}>Вперёд</button>
        </div>
      </section>
      {diagnostics
        ? <AdminRouteEligibilityDiagnostics report={diagnostics} />
        : <AdminEmpty message="Выберите город, чтобы увидеть готовность мест для маршрутов" />}
      {loading ? <AdminLoading /> : null}
      <AdminRouteEligibilityTable items={data?.items ?? []} selected={selected} onToggle={toggleSelected} onToggleAll={toggleAllVisible} />
    </div>
  )
}
