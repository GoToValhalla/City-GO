import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type { AdminPlaceChangeReview, AdminPlaceChangeReviewsResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const valueText = (value: unknown) => value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value)

export const AdminPlaceChangeReviewsPage = () => {
  const [params, setParams] = useSearchParams()
  const citySlug = params.get('city') ?? ''
  const [items, setItems] = useState<AdminPlaceChangeReview[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | 'bulk' | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    const query = new URLSearchParams({ status: 'open', limit: '100' })
    if (citySlug) query.set('city_slug', citySlug)
    try {
      const response = await adminGet<AdminPlaceChangeReviewsResponse>(`/admin/place-change-reviews?${query}`)
      setItems(response.items)
      setTotal(response.total)
      setSelected(new Set())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось загрузить изменения мест')
    } finally {
      setLoading(false)
    }
  }, [citySlug])

  useEffect(() => { void load() }, [load])

  const updateCity = (value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set('city', value)
    else next.delete('city')
    setParams(next, { replace: true })
  }

  const toggle = (reviewId: number) => setSelected((current) => {
    const next = new Set(current)
    if (next.has(reviewId)) next.delete(reviewId)
    else next.add(reviewId)
    return next
  })

  const resolveBulk = async (action: 'approve' | 'reject') => {
    const reviewIds = [...selected]
    if (reviewIds.length === 0) return
    const label = action === 'approve' ? 'Принять новые данные' : 'Отклонить и восстановить прежние данные'
    if (!window.confirm(`${label} для ${reviewIds.length} мест?`)) return
    setBusy('bulk')
    setError(null)
    try {
      await adminPost(`/admin/place-change-reviews/bulk/${action}`, { review_ids: reviewIds })
      setItems((current) => current.filter((item) => !selected.has(item.id)))
      setTotal((current) => Math.max(0, current - reviewIds.length))
      setSelected(new Set())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось обработать изменения')
    } finally {
      setBusy(null)
    }
  }

  const resolve = async (review: AdminPlaceChangeReview, action: 'approve' | 'reject') => {
    const label = action === 'approve' ? 'Принять новые данные' : 'Отклонить и восстановить прежние данные'
    if (!window.confirm(`${label} для «${review.place_title}»?`)) return
    setBusy(review.id)
    setError(null)
    try {
      await adminPost(`/admin/place-change-reviews/${review.id}/${action}`, {})
      setItems((current) => current.filter((item) => item.id !== review.id))
      setTotal((current) => Math.max(0, current - 1))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось обработать изменение')
    } finally {
      setBusy(null)
    }
  }

  return <div>
    <h2 className="admin-page-title">Изменения мест ({total})</h2>
    <p className="admin-page-subtitle">Изменённые места временно скрыты из публичного каталога. Здесь можно принять новые данные или восстановить прежнюю версию.</p>
    <section className="admin-filter-card admin-filter-grid">
      <label className="admin-field"><span>Город</span><input value={citySlug} onChange={(event) => updateCity(event.target.value)} placeholder="slug города" /></label>
      <button type="button" className="admin-btn" onClick={() => setParams({})}>Сбросить</button>
      <button type="button" className="admin-btn admin-btn-ok" disabled={selected.size === 0 || busy !== null} onClick={() => void resolveBulk('approve')}>Принять выбранные ({selected.size})</button>
      <button type="button" className="admin-btn admin-btn-danger" disabled={selected.size === 0 || busy !== null} onClick={() => void resolveBulk('reject')}>Отклонить выбранные ({selected.size})</button>
    </section>
    {error && <AdminError message={error} />}
    {loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="Новых изменений мест нет" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th><input aria-label="Выбрать все изменения" type="checkbox" checked={items.length > 0 && selected.size === items.length} onChange={() => setSelected(selected.size === items.length ? new Set() : new Set(items.map((item) => item.id)))} /></th><th>Место</th><th>Город</th><th>Что изменилось</th><th>Источник и причина</th><th>Действия</th></tr></thead><tbody>
      {items.map((review) => <tr key={review.id}>
        <td><input aria-label={`Выбрать ${review.place_title}`} type="checkbox" checked={selected.has(review.id)} onChange={() => toggle(review.id)} /></td>
        <td><Link to={`/admin/places/${review.place_id}`}>{review.place_title}</Link></td>
        <td><Link to={`/admin/cities/${review.city_slug}`}>{review.city_name}</Link></td>
        <td>{Object.entries(review.changes).map(([field, change]) => <div key={field}><strong>{field}:</strong> {valueText(change.before)} → {valueText(change.after)}</div>)}</td>
        <td>{review.source_url ? <a href={review.source_url} target="_blank" rel="noreferrer">{review.source ?? "Источник"}</a> : review.source ?? "Источник"}<br />{review.reason}<br /><span className="admin-muted">{review.review_reasons.join(', ') || "Источник обновил данные"}</span></td>
        <td><div className="admin-actions-cell"><button type="button" className="admin-btn admin-btn-ok admin-btn-sm" disabled={busy !== null} onClick={() => void resolve(review, 'approve')}>Принять</button><button type="button" className="admin-btn admin-btn-danger admin-btn-sm" disabled={busy === review.id} onClick={() => void resolve(review, 'reject')}>Отклонить</button></div></td>
      </tr>)}
    </tbody></table></div>}
  </div>
}