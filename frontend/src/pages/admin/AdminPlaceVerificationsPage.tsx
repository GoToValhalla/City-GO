import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { VERIFY_STATUS_OPTIONS } from './adminPlacesPresets'
import { AdminCategorySelect } from './AdminCategorySelect'
import { categoryText } from './adminRouteCopy'
import { verificationStatusText } from './adminHumanText'
import type { AdminCitiesResponse, AdminVerificationQueue, AdminVerificationSummary, AdminVerificationTask } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const PAGE_SIZES = [20, 50, 100]

const verifyActionLabel = (action: string) => action === 'exists' ? 'Подтвердить место' : 'Исключить как не найденное'
const verifyActionHint = (action: string) => action === 'exists'
  ? 'Место считается найденным и пригодным для дальнейшей работы.'
  : 'Место помечается как не найденное. Используйте, если объект не удалось подтвердить.'
const confidenceText = (value: number) => value <= 1 ? `${Math.round(value * 100)}%` : `${Math.round(value)}%`

export const AdminPlaceVerificationsPage = () => {
  const [tasks, setTasks] = useState<AdminVerificationTask[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<AdminVerificationSummary | null>(null)
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [citySlug, setCitySlug] = useState('')
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [limit, setLimit] = useState(50)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const q = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (citySlug) q.set('city_slug', citySlug)
    if (status) q.set('status', status)
    if (category) q.set('category', category)
    Promise.all([
      adminGet<AdminVerificationQueue>(`/admin/place-verifications/queue?${q}`),
      adminGet<AdminVerificationSummary>('/admin/place-verifications/summary'),
      adminGet<AdminCitiesResponse>('/admin/cities?limit=100'),
    ])
      .then(([queue, s, c]) => {
        setTasks(queue.items)
        setTotal(queue.total)
        setStats(s)
        setCities(c.items)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [citySlug, status, category, limit, offset])

  useEffect(() => { load() }, [load])

  const verify = async (placeId: number, action: string) => {
    const label = verifyActionLabel(action)
    if (!window.confirm(`${label} для места #${placeId}? ${verifyActionHint(action)}`)) return
    setBusy(placeId)
    try {
      await adminPost(`/admin/place-verifications/places/${placeId}/verify`, { action })
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(null) }
  }

  const page = Math.floor(offset / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))

  return (
    <div>
      <h2 className="admin-page-title">Проверка мест ({total})</h2>
      <p className="admin-page-subtitle">Подтверждаем, что место реально существует и его можно использовать в каталоге.</p>
      {stats && (
        <div className="admin-metrics-grid admin-metrics-small">
          <div className="admin-metric-card"><div className="admin-metric-value">{stats.queue_total}</div><div className="admin-metric-label">В очереди</div></div>
          <div className="admin-metric-card"><div className="admin-metric-value">{stats.verified_today}</div><div className="admin-metric-label">Проверено сегодня</div></div>
          <div className="admin-metric-card"><div className="admin-metric-value">{stats.needs_recheck}</div><div className="admin-metric-label">Нужна перепроверка</div></div>
          <div className="admin-metric-card"><div className="admin-metric-value">{stats.low_confidence}</div><div className="admin-metric-label">Низкая уверенность</div></div>
        </div>
      )}
      <section className="admin-filter-card">
        <div className="admin-help-title">Фильтры проверки</div>
        <div className="admin-filters">
          <select value={citySlug} onChange={(e) => { setCitySlug(e.target.value); setOffset(0) }}>
            <option value="">Все города</option>
            {cities.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
          </select>
          <select value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0) }}>
            {VERIFY_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <AdminCategorySelect value={category} onChange={(value) => { setCategory(value); setOffset(0) }} includeAll />
          <select value={limit} onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0) }}>
            {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} на страницу</option>)}
          </select>
        </div>
      </section>
      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : tasks.length === 0 ? (
        <AdminEmpty message="Очередь пуста по выбранным фильтрам" />
      ) : (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Место</th><th>Город</th><th>Категория</th><th>Адрес</th><th>Статус</th><th>Уверенность</th><th>Действия</th></tr></thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.place_id}>
                    <td><Link to={`/admin/places/${t.place_id}`}>{t.title}</Link></td>
                    <td>{t.city_slug ?? '—'}</td>
                    <td>{categoryText(t.category)}</td>
                    <td>{t.address ?? '—'}</td>
                    <td>{verificationStatusText(t.verification_status)}</td>
                    <td>{confidenceText(t.existence_confidence_score)}</td>
                    <td>
                      <button type="button" disabled={busy === t.place_id} title={verifyActionHint('exists')} onClick={() => verify(t.place_id, 'exists')} className="admin-btn admin-btn-ok admin-btn-sm">Подтвердить место</button>
                      <button type="button" disabled={busy === t.place_id} title={verifyActionHint('not_found')} onClick={() => verify(t.place_id, 'not_found')} className="admin-btn admin-btn-danger admin-btn-sm">Исключить</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="admin-actions-cell">
            <button type="button" className="admin-btn admin-btn-sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Назад</button>
            <span className="admin-muted">Стр. {page} / {pages} · всего {total}</span>
            <button type="button" className="admin-btn admin-btn-sm" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Вперёд</button>
          </div>
        </>
      )}
    </div>
  )
}
