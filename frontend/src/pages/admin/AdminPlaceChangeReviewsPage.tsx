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
  const [busy, setBusy] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    const query = new URLSearchParams({ status: 'open', limit: '100' })
    if (citySlug) query.set('city_slug', citySlug)
    try {
      const response = await adminGet<AdminPlaceChangeReviewsResponse>(`/admin/place-change-reviews?${query}`)
      setItems(response.items)
      setTotal(response.total)
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
    </section>
    {error && <AdminError message={error} />}
    {loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="Новых изменений мест нет" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Место</th><th>Город</th><th>Что изменилось</th><th>Источник и причина</th><th>Действия</th></tr></thead><tbody>
      {items.map((review) => <tr key={review.id}>
        <td><Link to={`/admin/places/${review.place_id}`}>{review.place_title}</Link></td>
        <td><Link to={`/admin/cities/${review.city_slug}`}>{review.city_name}</Link></td>
        <td>{Object.entries(review.changes).map(([field, change]) => <div key={field}><strong>{field}:</strong> {valueText(change.before)} → {valueText(change.after)}</div>)}</td>
        <td>{review.reason}<br /><span className="admin-muted">{review.review_reasons.join(', ') || 'Источник обновил данные'}</span></td>
        <td><div className="admin-actions-cell"><button type="button" className="admin-btn admin-btn-ok admin-btn-sm" disabled={busy === review.id} onClick={() => void resolve(review, 'approve')}>Принять</button><button type="button" className="admin-btn admin-btn-danger admin-btn-sm" disabled={busy === review.id} onClick={() => void resolve(review, 'reject')}>Отклонить</button></div></td>
      </tr>)}
    </tbody></table></div>}
  </div>
}