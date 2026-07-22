import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type ChangeValue = { before: unknown; after: unknown }
type Review = {
  id: number; place_id: number; place_title: string; city_slug: string; city_name: string
  changes: Record<string, ChangeValue>; source: string | null; source_url: string | null
  reason: string | null; review_reasons: string[]
}
type SortKey = 'title' | 'city' | 'changes'

const valueText = (value: unknown) => value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value)

export const AdminPlaceChangeReviewsPage = () => {
  const [params, setParams] = useSearchParams()
  const citySlug = params.get('city') ?? ''
  const sortRaw = params.get('sort')
  const sort: SortKey = sortRaw === 'title' || sortRaw === 'city' || sortRaw === 'changes' ? sortRaw : 'title'
  const dir = params.get('dir') === 'desc' ? 'desc' : 'asc'
  const [items, setItems] = useState<Review[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | 'bulk' | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    const query = new URLSearchParams({ status: 'open', limit: '100' })
    if (citySlug) query.set('city_slug', citySlug)
    try {
      const response = await adminGet<{ items: Review[]; total: number }>(`/admin/place-change-reviews?${query}`)
      setItems(response.items); setTotal(response.total); setSelected(new Set())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось загрузить изменения мест')
    } finally { setLoading(false) }
  }, [citySlug])
  useEffect(() => { void load() }, [load])

  const sorted = useMemo(() => {
    const factor = dir === 'asc' ? 1 : -1
    return [...items].sort((a, b) => {
      if (sort === 'city') return a.city_name.localeCompare(b.city_name, 'ru') * factor
      if (sort === 'changes') return (Object.keys(a.changes).length - Object.keys(b.changes).length) * factor
      return a.place_title.localeCompare(b.place_title, 'ru') * factor
    })
  }, [items, sort, dir])

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value); else next.delete(key)
    setParams(next, { replace: true })
  }
  const toggleSort = (key: SortKey) => {
    const next = new URLSearchParams(params)
    if (sort === key) next.set('dir', dir === 'asc' ? 'desc' : 'asc')
    else { next.set('sort', key); next.set('dir', 'asc') }
    setParams(next, { replace: true })
  }
  const toggle = (id: number) => setSelected((current) => {
    const next = new Set(current)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  })
  const invert = () => setSelected((current) => {
    const next = new Set<number>()
    sorted.forEach((item) => { if (!current.has(item.id)) next.add(item.id) })
    return next
  })

  const resolveBulk = async (action: 'approve' | 'reject') => {
    const reviewIds = [...selected]
    if (!reviewIds.length) return
    if (!window.confirm(`${action === 'approve' ? 'Принять' : 'Отклонить'} ${reviewIds.length} мест?`)) return
    setBusy('bulk'); setError(null)
    try {
      await adminPost(`/admin/place-change-reviews/bulk/${action}`, { review_ids: reviewIds })
      setItems((current) => current.filter((item) => !selected.has(item.id)))
      setTotal((current) => Math.max(0, current - reviewIds.length))
      setSelected(new Set())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось обработать изменения')
    } finally { setBusy(null) }
  }
  const resolve = async (review: Review, action: 'approve' | 'reject') => {
    if (!window.confirm(`${action === 'approve' ? 'Принять' : 'Отклонить'} «${review.place_title}»?`)) return
    setBusy(review.id); setError(null)
    try {
      await adminPost(`/admin/place-change-reviews/${review.id}/${action}`, {})
      setItems((current) => current.filter((item) => item.id !== review.id))
      setTotal((current) => Math.max(0, current - 1))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось обработать изменение')
    } finally { setBusy(null) }
  }

  return <div>
    <h2 className="admin-page-title">Изменения мест ({total})</h2>
    <p className="admin-page-subtitle">Изменённые места временно скрыты из публичного каталога.</p>
    <section className="admin-filter-card admin-filter-grid admin-filters-sticky">
      <label className="admin-field"><span>Город</span><input value={citySlug} onChange={(e) => setFilter('city', e.target.value)} placeholder="slug города" /></label>
      <button type="button" className="admin-btn" onClick={() => setParams({}, { replace: true })}>Сбросить</button>
      <button type="button" className="admin-btn" disabled={!sorted.length} onClick={invert}>Инвертировать выбор</button>
      <button type="button" className="admin-btn admin-btn-ok" disabled={selected.size === 0 || busy !== null} onClick={() => void resolveBulk('approve')}>Принять ({selected.size})</button>
      <button type="button" className="admin-btn admin-btn-danger" disabled={selected.size === 0 || busy !== null} onClick={() => void resolveBulk('reject')}>Отклонить ({selected.size})</button>
    </section>
    {error && <AdminError message={error} />}
    {loading ? <AdminLoading /> : sorted.length === 0 ? <AdminEmpty message="Новых изменений мест нет" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr>
      <th><input aria-label="Выбрать все" type="checkbox" checked={sorted.length > 0 && selected.size === sorted.length} onChange={() => setSelected(selected.size === sorted.length ? new Set() : new Set(sorted.map((item) => item.id)))} /></th>
      <th className="admin-sortable-th" aria-sort={sort === 'title' ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'} onClick={() => toggleSort('title')}>Место</th>
      <th className="admin-sortable-th" aria-sort={sort === 'city' ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'} onClick={() => toggleSort('city')}>Город</th>
      <th className="admin-sortable-th" aria-sort={sort === 'changes' ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'} onClick={() => toggleSort('changes')}>Что изменилось</th>
      <th>Источник</th><th>Действия</th></tr></thead><tbody>
      {sorted.map((review) => <tr key={review.id}>
        <td><input aria-label={`Выбрать ${review.place_title}`} type="checkbox" checked={selected.has(review.id)} onChange={() => toggle(review.id)} /></td>
        <td><Link to={`/admin/places/${review.place_id}`}>{review.place_title}</Link></td>
        <td><Link to={`/admin/cities/${review.city_slug}`}>{review.city_name}</Link></td>
        <td>{Object.entries(review.changes).map(([field, change]) => <div key={field}><strong>{field}:</strong> {valueText(change.before)} → {valueText(change.after)}</div>)}</td>
        <td>{review.source_url ? <a href={review.source_url} target="_blank" rel="noreferrer">{review.source ?? 'Источник'}</a> : review.source ?? 'Источник'}<br />{review.reason}<br /><span className="admin-muted">{review.review_reasons.join(', ') || 'Источник обновил данные'}</span></td>
        <td><div className="admin-actions-cell"><button type="button" className="admin-btn admin-btn-ok admin-btn-sm" disabled={busy !== null} onClick={() => void resolve(review, 'approve')}>Принять</button><button type="button" className="admin-btn admin-btn-danger admin-btn-sm" disabled={busy !== null} onClick={() => void resolve(review, 'reject')}>Отклонить</button></div></td>
      </tr>)}
    </tbody></table></div>}
  </div>
}
