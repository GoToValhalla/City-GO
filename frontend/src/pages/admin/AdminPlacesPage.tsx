import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCategorySelect } from './AdminCategorySelect'
import { AdminPlacesFilters } from './AdminPlacesFilters'
import { AdminPlacesLoadSentinel } from './AdminPlacesLoadSentinel'
import { AdminPlacesTable } from './AdminPlacesTable'
import type { AdminCitiesResponse } from './adminTypes'
import { bulkActionHint, bulkActionText } from './adminHumanText'
import { useAdminPlacesList, type PlacesListFilters } from './useAdminPlacesList'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const DEFAULT_FILTERS: PlacesListFilters = {
  citySlug: '', destinationSlug: '', preset: '', pubStatus: '', verifyStatus: '', category: '', routeEligible: '', active: '', searchable: '',
  hasPhoto: '', hasAddress: '', hasDescription: '', hasPhone: '', hasWebsite: '', hasHours: '', lowConfidence: '',
  qualityTier: '', source: '', sort: 'updated', direction: 'desc', limit: 50, q: '',
}

const PARAM_KEYS: Record<keyof PlacesListFilters, string> = {
  citySlug: 'city', destinationSlug: 'destination', preset: 'preset', pubStatus: 'publication', verifyStatus: 'verification', category: 'category',
  routeEligible: 'routes', active: 'active', searchable: 'searchable', hasPhoto: 'photo', hasAddress: 'address',
  hasDescription: 'description', hasPhone: 'phone', hasWebsite: 'website', hasHours: 'hours', lowConfidence: 'confidence',
  qualityTier: 'quality', source: 'source', sort: 'sort', direction: 'direction', limit: 'limit', q: 'q',
}

const filtersFromParams = (params: URLSearchParams): PlacesListFilters => {
  const values = { ...DEFAULT_FILTERS }
  Object.entries(PARAM_KEYS).forEach(([field, key]) => {
    const raw = params.get(key)
    if (raw !== null) {
      if (field === 'limit') values.limit = [20, 50, 100, 200].includes(Number(raw)) ? Number(raw) : 50
      else (values as unknown as Record<string, string>)[field] = raw
    }
  })
  return values
}

export const AdminPlacesPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [busy, setBusy] = useState<number | null>(null)
  const [bulkBusy, setBulkBusy] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkCategory, setBulkCategory] = useState('')
  const [preview, setPreview] = useState<{ affected_count?: number; warnings?: string[] } | null>(null)
  const [filtersExpanded, setFiltersExpanded] = useState(false)
  const filters = useMemo(() => filtersFromParams(searchParams), [searchParams])
  const { items, total, loading, loadingMore, error, hasMore, reload, loadMore, setError } = useAdminPlacesList(filters)

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((response) => setCities(response.items)).catch(() => {})
  }, [])
  useEffect(() => { void reload(); setSelected(new Set()); setPreview(null) }, [reload])

  const updateFilters = useCallback((changes: Partial<PlacesListFilters>) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([field, value]) => {
      const key = PARAM_KEYS[field as keyof PlacesListFilters]
      const defaultValue = DEFAULT_FILTERS[field as keyof PlacesListFilters]
      if (value === '' || value === defaultValue) next.delete(key)
      else next.set(key, String(value))
    })
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const toggleSelected = (id: number) => setSelected((current) => {
    const next = new Set(current)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  })

  const toggleVisible = () => setSelected((current) => {
    const next = new Set(current)
    const allSelected = items.length > 0 && items.every((item) => next.has(item.id))
    items.forEach((item) => { if (allSelected) next.delete(item.id); else next.add(item.id) })
    return next
  })

  const bulk = async (action: string, params: object = {}) => {
    const ids = [...selected]
    if (!ids.length) return
    setBulkBusy(true)
    setError(null)
    try {
      const result = await adminPost<{ affected_count?: number; warnings?: string[] }>('/admin/places/bulk/preview', { place_ids: ids, action, params })
      setPreview(result)
      if (!window.confirm(`${bulkActionText(action)}: ${result.affected_count ?? ids.length} мест?`)) return
      await adminPost('/admin/places/bulk/apply', { place_ids: ids, action, params, confirm: true })
      setSelected(new Set())
      setPreview(null)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось выполнить массовое действие')
    } finally {
      setBulkBusy(false)
    }
  }

  const refreshSelectedAddresses = async () => {
    const ids = [...selected]
    if (!ids.length || !window.confirm(`Поставить обновление адресов для ${ids.length} мест?`)) return
    setBulkBusy(true)
    try {
      await adminPost('/admin/places/address-refresh', { place_ids: ids })
      setSelected(new Set())
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось запустить обновление адресов')
    } finally {
      setBulkBusy(false)
    }
  }

  const action = async (placeId: number, endpoint: string, body: object = {}) => {
    setBusy(placeId)
    setError(null)
    try {
      await adminPost(`/admin/places/${placeId}/${endpoint}`, body)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось выполнить действие')
    } finally {
      setBusy(null)
    }
  }

  const unpublish = (id: number) => {
    const reason = window.prompt('Причина скрытия места с сайта:')
    if (reason?.trim()) void action(id, 'unpublish', { reason: reason.trim() })
  }

  return (
    <div>
      <div className="admin-page-header">
        <div><h2 className="admin-page-title">Каталог мест</h2><p className="admin-page-subtitle">Найдено: {total}. Фильтрация, проверка, публикация и массовое управление.</p></div>
        <Link className="admin-btn admin-btn-primary" to={`/admin/places/new${filters.citySlug ? `?city=${filters.citySlug}` : ''}`}>Добавить место</Link>
      </div>
      <AdminPlacesFilters cities={cities} value={filters} expanded={filtersExpanded} onChange={updateFilters} onToggleExpanded={() => setFiltersExpanded((current) => !current)} onReset={() => setSearchParams({}, { replace: true })} />

      <section className="admin-bulk-panel">
        <div className="admin-bulk-row"><span className="admin-bulk-title">Массовые действия</span><span className="admin-selection-count">Выбрано: {selected.size}</span><button type="button" className="admin-btn" disabled={!items.length || bulkBusy} onClick={toggleVisible}>Выбрать загруженные</button><button type="button" className="admin-btn admin-btn-muted" disabled={!selected.size || bulkBusy} onClick={() => setSelected(new Set())}>Снять выбор</button></div>
        <p className="admin-bulk-hint">Действия применяются к отмеченным местам. Перед изменением система покажет количество затронутых записей.</p>
        <div className="admin-bulk-row">
          <button type="button" className="admin-btn" disabled={!selected.size || bulkBusy} title={bulkActionHint('send_review')} onClick={() => void bulk('send_review')}>{bulkActionText('send_review')}</button>
          <button type="button" className="admin-btn admin-btn-ok" disabled={!selected.size || bulkBusy} title={bulkActionHint('enable_route')} onClick={() => void bulk('enable_route')}>{bulkActionText('enable_route')}</button>
          <button type="button" className="admin-btn admin-btn-danger" disabled={!selected.size || bulkBusy} title={bulkActionHint('disable_route')} onClick={() => void bulk('disable_route', { reason: 'Массовое исключение' })}>{bulkActionText('disable_route')}</button>
          <button type="button" className="admin-btn" disabled={!selected.size || bulkBusy} title={bulkActionHint('refresh_addresses')} onClick={() => void refreshSelectedAddresses()}>{bulkActionText('refresh_addresses')}</button>
        </div>
        <div className="admin-bulk-row"><AdminCategorySelect value={bulkCategory} onChange={setBulkCategory} includeAll ariaLabel="Новая категория" citySlug={filters.citySlug} /><button type="button" className="admin-btn" disabled={!selected.size || !bulkCategory || bulkBusy} onClick={() => void bulk('set_category', { category: bulkCategory })}>{bulkActionText('set_category')}</button></div>
        {preview && <p className="admin-muted">Будет изменено: {preview.affected_count ?? selected.size}.{preview.warnings?.length ? ` Предупреждения: ${preview.warnings.join(', ')}` : ''}</p>}
      </section>

      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="По выбранным фильтрам места не найдены" /> : <><AdminPlacesTable items={items} busy={busy} selected={selected} onToggle={toggleSelected} onToggleAll={toggleVisible} onPublish={(id) => void action(id, 'publish')} onUnpublish={unpublish} onVerify={(id) => void action(id, 'verify')} /><AdminPlacesLoadSentinel enabled={hasMore} loading={loadingMore} onLoadMore={loadMore} shown={items.length} total={total} /></>}
    </div>
  )
}
