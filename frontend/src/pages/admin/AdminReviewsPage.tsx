import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type Review = { id: number; place_id: number; place_name: string; source: string | null; confidence: number | null; status: string; reason: string | null; created_at: string; place_version_at_creation: number }
type Diff = Review & { proposed_diff: Record<string, { current: unknown; proposed: unknown; reason?: string | null }> }

const REASONS: Record<string, string> = {
  LOW_CONFIDENCE_SCORE: 'Низкая уверенность источника',
  MANUAL_OVERRIDE_PROTECTED: 'Поле защищено ручной правкой',
  SOURCE_PRIORITY_LOWER: 'Источник ниже по приоритету',
  VERSION_MISMATCH: 'Данные места изменились, обновите diff',
  VALUE_CONFLICT: 'Значение отличается от текущего',
}
const FIELDS: Record<string, string> = {
  title: 'Название', short_description: 'Описание', address: 'Адрес', category: 'Категория',
  canonical_category: 'Категория', lat: 'Широта', lng: 'Долгота', image_url: 'Фото',
  opening_hours: 'Часы работы', average_visit_duration_minutes: 'Время посещения',
}
const text = (value: unknown) => value == null || value === '' ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value)
const reasonText = (value?: string | null) => (value ?? '').split(',').map((item) => REASONS[item] ?? '').filter(Boolean).join(', ') || 'Требует проверки'

export const AdminReviewsPage = () => {
  const [items, setItems] = useState<Review[]>([])
  const [diff, setDiff] = useState<Diff | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setItems(await adminGet<Review[]>('/admin/reviews')) }
    catch { setError('Не удалось загрузить очередь слияния данных') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  const open = async (id: number) => {
    setError(null); setNotice(null)
    try { const data = await adminGet<Diff>(`/admin/reviews/${id}/diff`); setDiff(data); setSelected(new Set()) }
    catch { setError('Не удалось открыть diff') }
  }
  const merge = async () => {
    if (!diff || selected.size === 0) return
    setBusy(true); setError(null)
    try {
      await adminPost(`/admin/reviews/${diff.id}/merge`, { fields_to_apply: [...selected], expected_version: diff.place_version_at_creation })
      setNotice('Выбранные поля применены'); setDiff(null); await load()
    } catch { setError('Данные места изменились или merge не применился. Обновите diff и повторите.') }
    finally { setBusy(false) }
  }
  const reject = async () => {
    if (!diff) return
    setBusy(true); setError(null)
    try { await adminPost(`/admin/reviews/${diff.id}/reject`, { reason: 'Отклонено оператором' }); setNotice('Заявка отклонена'); setDiff(null); await load() }
    catch { setError('Не удалось отклонить заявку') }
    finally { setBusy(false) }
  }
  const toggle = (field: string) => setSelected((current) => {
    const next = new Set(current)
    if (next.has(field)) {
      next.delete(field)
    } else {
      next.add(field)
    }
    return next
  })

  if (loading) return <AdminLoading />
  return <div>
    <header className="admin-page-header"><div><h1 className="admin-page-title">Слияние данных мест</h1><p className="admin-page-subtitle">Проверка изменений enrichment перед публикацией в карточках.</p></div></header>
    {notice && <p className="admin-success-text">{notice}</p>}{error && <AdminError message={error} />}
    {!items.length ? <AdminEmpty message="Заявок на слияние нет" /> : <section className="admin-section"><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Место</th><th>Источник</th><th>Причина</th><th>Создано</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><Link to={`/admin/places/${item.place_id}`}>{item.place_name}</Link></td><td>{item.source ?? '—'} · {item.confidence != null ? `${Math.round(item.confidence * 100)}%` : '—'}</td><td>{reasonText(item.reason)}</td><td>{new Date(item.created_at).toLocaleString('ru-RU')}</td><td><button className="admin-btn admin-btn-sm" onClick={() => void open(item.id)}>Открыть diff</button></td></tr>)}</tbody></table></div></section>}
    {diff ? <section className="admin-detail-panel"><h2>Diff: {diff.place_name}</h2><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Применить</th><th>Поле</th><th>Сейчас</th><th>Предложено</th><th>Причина</th></tr></thead><tbody>{Object.entries(diff.proposed_diff).map(([field, row]) => <tr key={field}><td><input aria-label={`Выбрать ${FIELDS[field] ?? field}`} type="checkbox" checked={selected.has(field)} onChange={() => toggle(field)} /></td><td>{FIELDS[field] ?? field}</td><td>{text(row.current)}</td><td>{text(row.proposed)}</td><td>{reasonText(row.reason ?? diff.reason)}</td></tr>)}</tbody></table></div><div className="admin-actions-cell"><button className="admin-btn admin-btn-primary" disabled={busy || selected.size === 0} onClick={() => void merge()}>{busy ? 'Применяем…' : 'Применить выбранное'}</button><button className="admin-btn admin-btn-danger" disabled={busy} onClick={() => void reject()}>Отклонить</button><button className="admin-btn" disabled={busy} onClick={() => void open(diff.id)}>Обновить diff</button></div></section> : null}
  </div>
}
