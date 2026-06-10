import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminPlacesFilters } from './AdminPlacesFilters'
import { AdminPlacesLoadSentinel } from './AdminPlacesLoadSentinel'
import { AdminPlacesTable } from './AdminPlacesTable'
import type { AdminCitiesResponse } from './adminTypes'
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
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [preview, setPreview] = useState<object | null>(null)
  const filters = useMemo(
    () => ({ citySlug, preset, pubStatus, verifyStatus, category, q }),
    [citySlug, preset, pubStatus, verifyStatus, category, q],
  )
  const { items, total, loading, loadingMore, error, hasMore, reload, loadMore, setError } = useAdminPlacesList(filters)

  useEffect(() => { adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((r) => setCities(r.items)).catch(() => {}) }, [])
  useEffect(() => { reload() }, [reload])

  const toggleSel = (id: number) => setSelected((s) => {
    const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n
  })

  const bulk = async (action: string, paramsBody: object = {}) => {
    const ids = [...selected]
    if (!ids.length) return
    const prev = await adminPost<object>('/admin/places/bulk/preview', { place_ids: ids, action, params: paramsBody })
    setPreview(prev)
    if (!window.confirm(`Применить «${action}» к ${ids.length} местам?`)) return
    await adminPost('/admin/places/bulk/apply', { place_ids: ids, action, params: paramsBody, confirm: true })
    setSelected(new Set()); setPreview(null); reload()
  }

  const action = async (placeId: number, endpoint: string, body?: object) => {
    setBusy(placeId)
    try { await adminPost(`/admin/places/${placeId}/${endpoint}`, body ?? {}); reload() }
    catch (e) { setError(e instanceof Error ? e.message : 'Ошибка действия') }
    finally { setBusy(null) }
  }

  const unpublish = (id: number) => {
    const reason = window.prompt('Причина скрытия места (обязательно):')
    if (!reason?.trim()) return
    void action(id, 'unpublish', { reason: reason.trim() })
  }

  return (
    <div>
      <h2 className="admin-page-title">Места ({total})</h2>
      <p className="admin-page-subtitle">Управление качеством данных и публикацией · <Link to="/admin/places/new">Создать место</Link></p>
      {selected.size > 0 && (
        <div className="admin-filters admin-filters-stack">
          <span>Выбрано: {selected.size}</span>
          <button type="button" className="admin-btn admin-btn-sm" onClick={() => bulk('send_review')}>На проверку</button>
          <button type="button" className="admin-btn admin-btn-sm" onClick={() => bulk('enable_route')}>Включить в маршруты</button>
          <button type="button" className="admin-btn admin-btn-sm" onClick={() => bulk('disable_route', { reason: 'bulk' })}>Исключить из маршрутов</button>
          <button type="button" className="admin-btn admin-btn-sm" onClick={() => adminPost('/admin/places/address-refresh', { place_ids: [...selected] }).then(reload)}>Обновить адреса</button>
        </div>
      )}
      {preview && <pre className="admin-muted" style={{ fontSize: 11 }}>{JSON.stringify(preview, null, 2)}</pre>}
      <AdminPlacesFilters cities={cities} citySlug={citySlug} preset={preset} pubStatus={pubStatus}
        verifyStatus={verifyStatus} category={category} q={q}
        onCityChange={setCitySlug} onPresetChange={setPreset} onPubStatusChange={setPubStatus}
        onVerifyStatusChange={setVerifyStatus} onCategoryChange={setCategory} onQChange={setQ} onSearch={reload} />
      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="Места не найдены по выбранным фильтрам" /> : (
        <>
          <AdminPlacesTable items={items} busy={busy} selected={selected} onToggle={toggleSel}
            onPublish={(id) => action(id, 'publish')} onUnpublish={unpublish} onVerify={(id) => action(id, 'verify')} />
          <AdminPlacesLoadSentinel enabled={hasMore} loading={loadingMore} onLoadMore={loadMore} shown={items.length} total={total} />
        </>
      )}
    </div>
  )
}
