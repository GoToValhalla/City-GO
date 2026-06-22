import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCategorySelect } from './AdminCategorySelect'
import { AdminPlacesFilters } from './AdminPlacesFilters'
import { AdminPlacesLoadSentinel } from './AdminPlacesLoadSentinel'
import { AdminPlacesTable } from './AdminPlacesTable'
import type { AdminCitiesResponse } from './adminTypes'
import { bulkActionHint, bulkActionText } from './adminHumanText'
import { useAdminPlacesList } from './useAdminPlacesList'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

export const AdminPlacesPage = () => {
  const [params] = useSearchParams()
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [citySlug, setCitySlug] = useState(params.get('city') ?? '')
  const [preset, setPreset] = useState(params.get('preset') ?? '')
  const [pubStatus, setPubStatus] = useState('')
  const [verifyStatus, setVerifyStatus] = useState('')
  const [category, setCategory] = useState('')
  const [routeEligible, setRouteEligible] = useState('')
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkCategory, setBulkCategory] = useState('')
  const [preview, setPreview] = useState<{ affected_count?: number; warnings?: string[] } | null>(null)
  const filters = useMemo(
    () => ({ citySlug, preset, pubStatus, verifyStatus, category, routeEligible, q }),
    [citySlug, preset, pubStatus, verifyStatus, category, routeEligible, q],
  )
  const { items, total, loading, loadingMore, error, hasMore, reload, loadMore, setError } = useAdminPlacesList(filters)

  useEffect(() => { adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((r) => setCities(r.items)).catch(() => {}) }, [])
  useEffect(() => { reload(); setSelected(new Set()); setPreview(null) }, [reload])

  const toggleSel = (id: number) => setSelected((s) => {
    const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n
  })

  const toggleVisible = () => {
    const visibleIds = items.map((item) => item.id)
    setSelected((current) => {
      const next = new Set(current)
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => next.has(id))
      if (allSelected) {
        visibleIds.forEach((id) => next.delete(id))
      } else {
        visibleIds.forEach((id) => next.add(id))
      }
      return next
    })
  }

  const resetFilters = () => {
    setCitySlug('')
    setPreset('')
    setPubStatus('')
    setVerifyStatus('')
    setCategory('')
    setRouteEligible('')
    setQ('')
  }

  const bulk = async (action: string, paramsBody: object = {}) => {
    const ids = [...selected]
    if (!ids.length) return
    const label = bulkActionText(action)
    const prev = await adminPost<{ affected_count?: number; warnings?: string[] }>('/admin/places/bulk/preview', { place_ids: ids, action, params: paramsBody })
    setPreview(prev)
    if (!window.confirm(`${label}: ${ids.length} мест?`)) return
    await adminPost('/admin/places/bulk/apply', { place_ids: ids, action, params: paramsBody, confirm: true })
    setSelected(new Set()); setPreview(null); reload()
  }

  const refreshSelectedAddresses = async () => {
    const ids = [...selected]
    if (!ids.length || !window.confirm(`Обновить адреса: ${ids.length} мест?`)) return
    await adminPost('/admin/places/address-refresh', { place_ids: ids })
    reload()
  }

  const changeSelectedCategory = () => {
    if (!bulkCategory) return
    void bulk('set_category', { category: bulkCategory })
  }

  const action = async (placeId: number, endpoint: string, body?: object) => {
    setBusy(placeId)
    try { await adminPost(`/admin/places/${placeId}/${endpoint}`, body ?? {}); reload() }
    catch (e) { setError(e instanceof Error ? e.message : 'Ошибка действия') }
    finally { setBusy(null) }
  }

  const unpublish = (id: number) => {
    const reason = window.prompt('Причина скрытия места с сайта (обязательно):')
    if (!reason?.trim()) return
    void action(id, 'unpublish', { reason: reason.trim() })
  }

  return (
    <div>
      <h2 className="admin-page-title">Места ({total})</h2>
      <p className="admin-page-subtitle">Управление качеством данных и публикацией · <Link to="/admin/places/new">Создать место</Link></p>
      <AdminPlacesFilters cities={cities} citySlug={citySlug} preset={preset} pubStatus={pubStatus}
        verifyStatus={verifyStatus} category={category} routeEligible={routeEligible} q={q}
        onCityChange={setCitySlug} onPresetChange={setPreset} onPubStatusChange={setPubStatus}
        onVerifyStatusChange={setVerifyStatus} onCategoryChange={setCategory} onRouteEligibleChange={setRouteEligible}
        onQChange={setQ} onSearch={reload} onReset={resetFilters} />
      <section className="admin-bulk-panel">
        <div className="admin-bulk-row">
          <span className="admin-bulk-title">Массовые действия</span>
          <span className="admin-muted">Выбрано: {selected.size}</span>
          <button type="button" className="admin-btn admin-btn-sm" disabled={!items.length} onClick={toggleVisible}>Выбрать все видимые</button>
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size} onClick={() => setSelected(new Set())}>Снять выбор</button>
        </div>
        <p className="admin-bulk-hint">Массовое действие применяется только к выбранным строкам. Если нужно обработать больше мест, сначала загрузите следующую страницу или сузьте фильтр.</p>
        <div className="admin-bulk-row">
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size} title={bulkActionHint('send_review')} onClick={() => bulk('send_review')}>{bulkActionText('send_review')}</button>
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size} title={bulkActionHint('enable_route')} onClick={() => bulk('enable_route')}>{bulkActionText('enable_route')}</button>
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size} title={bulkActionHint('disable_route')} onClick={() => bulk('disable_route', { reason: 'bulk' })}>{bulkActionText('disable_route')}</button>
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size} title={bulkActionHint('refresh_addresses')} onClick={() => void refreshSelectedAddresses()}>{bulkActionText('refresh_addresses')}</button>
        </div>
        <div className="admin-bulk-row">
          <AdminCategorySelect value={bulkCategory} onChange={setBulkCategory} includeAll ariaLabel="Новая категория" citySlug={citySlug} />
          <button type="button" className="admin-btn admin-btn-sm" disabled={!selected.size || !bulkCategory} title={bulkActionHint('set_category')} onClick={changeSelectedCategory}>{bulkActionText('set_category')}</button>
        </div>
        <ul className="admin-help-list">
          <li>{bulkActionHint('enable_route')}</li>
          <li>{bulkActionHint('disable_route')}</li>
          <li>{bulkActionHint('set_category')}</li>
        </ul>
        {preview && (
          <p className="admin-muted">
            Предпросмотр: будет затронуто {preview.affected_count ?? selected.size} мест{preview.warnings?.length ? `. Предупреждения: ${preview.warnings.join(', ')}` : '.'}
          </p>
        )}
      </section>
      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="Места не найдены по выбранным фильтрам" /> : (
        <>
          <AdminPlacesTable items={items} busy={busy} selected={selected} onToggle={toggleSel} onToggleAll={toggleVisible}
            onPublish={(id) => action(id, 'publish')} onUnpublish={unpublish} onVerify={(id) => action(id, 'verify')} />
          <AdminPlacesLoadSentinel enabled={hasMore} loading={loadingMore} onLoadMore={loadMore} shown={items.length} total={total} />
        </>
      )}
    </div>
  )
}
