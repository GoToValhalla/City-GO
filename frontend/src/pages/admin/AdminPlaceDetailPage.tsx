import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { adminGet, adminPatch, adminPost } from './adminApi'
import { AdminPlaceForm, type AdminPlaceFormValue } from './AdminPlaceForm'
import { categoryText } from './adminRouteCopy'
import { publicationStatusText, verificationStatusText } from './adminHumanText'
import { AdminError, AdminLoading } from './shared/AdminStates'

type Detail = {
  id: number; slug: string; title: string; city_id: number; city_slug: string | null; city_name: string | null
  category: string | null; canonical_category: string | null; address: string | null; address_source: string | null
  address_confidence: number | null; address_updated_at: string | null; lat: number; lng: number; short_description: string | null
  image_url: string | null; source: string | null; source_url: string | null; website: string | null; phone: string | null
  atmosphere: string | null; inside: string | null; best_for: string | null; opening_hours: Record<string, unknown> | null
  average_visit_duration_minutes: number | null; price_level: number | null; indoor: boolean; outdoor: boolean
  dog_friendly: boolean; family_friendly: boolean; is_active: boolean; status: string; lifecycle_status: string
  quality_tier: string; quality_score: number; completeness_score: number; photo_score: number; description_score: number
  confidence_score: number; freshness_score: number; publication_status: string; verification_status: string
  visible_to_users: boolean; searchable: boolean; route_enabled: boolean; route_exclusion_reason: string | null
  existence_confidence_level: string; existence_confidence_score: number; admin_comment: string | null
  route_usage_count: number; route_usage_note: string | null; tags: Array<{ id: number; name: string }>
  audit_history: Array<{ id?: number; action: string; actor: string; reason?: string | null; created_at: string }>
}

const openingHoursText = (value: Record<string, unknown> | null) => {
  if (!value) return ''
  const display = value.display ?? value.raw
  return typeof display === 'string' ? display : JSON.stringify(value, null, 2)
}

const toForm = (data: Detail): AdminPlaceFormValue => ({
  title: data.title, category: data.category || 'attraction', address: data.address || '', lat: String(data.lat), lng: String(data.lng),
  shortDescription: data.short_description || '', imageUrl: data.image_url || '', website: data.website || '', phone: data.phone || '',
  source: data.source || 'admin_manual', sourceUrl: data.source_url || '', atmosphere: data.atmosphere || '', inside: data.inside || '',
  bestFor: data.best_for || '', openingHours: openingHoursText(data.opening_hours), visitDuration: data.average_visit_duration_minutes ? String(data.average_visit_duration_minutes) : '',
  priceLevel: data.price_level ? String(data.price_level) : '', indoor: data.indoor, outdoor: data.outdoor, dogFriendly: data.dog_friendly,
  familyFriendly: data.family_friendly, isActive: data.is_active, visibleToUsers: data.visible_to_users, searchable: data.searchable,
  routeEnabled: data.route_enabled, routeExclusionReason: data.route_exclusion_reason || '', adminComment: data.admin_comment || '',
})

const optionalText = (value: string) => value.trim() || null
const optionalNumber = (value: string) => value.trim() ? Number(value) : null

export const AdminPlaceDetailPage = () => {
  const { id } = useParams()
  const location = useLocation()
  const [data, setData] = useState<Detail | null>(null)
  const [form, setForm] = useState<AdminPlaceFormValue | null>(null)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [emergencyReason, setEmergencyReason] = useState('')
  const [emergencyConfirmed, setEmergencyConfirmed] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const response = await adminGet<Detail>(`/admin/places/${id}/detail`)
      setData(response)
      setForm(toForm(response))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить место')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { void load() }, [load])

  const backUrl = useMemo(() => {
    const from = new URLSearchParams(location.search).get('from')
    return from?.startsWith('/admin/places') ? from : `/admin/places${data?.city_slug ? `?city=${data.city_slug}` : ''}`
  }, [data?.city_slug, location.search])

  const save = async () => {
    if (!id || !form) return
    const lat = Number(form.lat)
    const lng = Number(form.lng)
    if (!form.title.trim()) return setError('Укажите название места')
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return setError('Укажите корректные координаты')
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const response = await adminPatch<Detail>(`/admin/places/${id}`, {
        title: form.title.trim(), category: form.category, address: optionalText(form.address), lat, lng,
        short_description: optionalText(form.shortDescription), image_url: optionalText(form.imageUrl), website: optionalText(form.website),
        phone: optionalText(form.phone), source: form.source, source_url: optionalText(form.sourceUrl), atmosphere: optionalText(form.atmosphere),
        inside: optionalText(form.inside), best_for: optionalText(form.bestFor),
        opening_hours: form.openingHours.trim() ? { display: form.openingHours.trim(), raw: form.openingHours.trim() } : {},
        average_visit_duration_minutes: optionalNumber(form.visitDuration), price_level: optionalNumber(form.priceLevel), indoor: form.indoor,
        outdoor: form.outdoor, dog_friendly: form.dogFriendly, family_friendly: form.familyFriendly, is_active: form.isActive,
        visible_to_users: form.visibleToUsers, searchable: form.searchable, route_enabled: form.routeEnabled,
        route_exclusion_reason: optionalText(form.routeExclusionReason), admin_comment: optionalText(form.adminComment), reason: 'Редактирование карточки места',
      })
      setData(response)
      setForm(toForm(response))
      setEditing(false)
      setNotice('Изменения сохранены')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось сохранить изменения')
    } finally {
      setBusy(false)
    }
  }

  const action = async (path: string, body: object, success: string) => {
    if (!id) return
    setBusy(true)
    setError(null)
    try {
      await adminPost(`/admin/places/${id}/${path}`, body)
      setNotice(success)
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось выполнить действие')
    } finally {
      setBusy(false)
    }
  }

  const unpublish = () => {
    const reason = window.prompt('Почему место нужно скрыть?')
    if (reason?.trim()) void action('unpublish', { reason: reason.trim() }, 'Место скрыто с сайта')
  }

  const reject = () => {
    const reason = window.prompt('Почему место отклоняем?')
    if (reason?.trim()) void action('reject', { reason: reason.trim() }, 'Место отклонено')
  }

  const refreshAddress = async () => {
    if (!id || !window.confirm('Поставить обновление адреса в очередь?')) return
    setBusy(true)
    try {
      await adminPost('/admin/places/address-refresh', { place_ids: [Number(id)] })
      setNotice('Обновление адреса поставлено в очередь')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось обновить адрес')
    } finally {
      setBusy(false)
    }
  }

  const emergencyHide = async () => {
    if (!id || emergencyReason.trim().length < 10 || !emergencyConfirmed) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await adminPost(`/admin/places/${id}/emergency-hide`, {
        reason: emergencyReason.trim(),
        idempotency_key: `emergency-hide-${globalThis.crypto?.randomUUID?.() ?? Date.now()}`,
      })
      setEmergencyReason('')
      setEmergencyConfirmed(false)
      setNotice('Место экстренно скрыто: оно убрано из каталога, поиска и маршрутов')
      await load()
    } catch {
      setError('Не удалось экстренно скрыть место. Проверьте причину и повторите.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <AdminLoading />
  if (!data || !form) return <AdminError message={error || 'Место не найдено'} />

  return (
    <div>
      <Link to={backUrl} className="admin-back-link">← К списку мест</Link>
      <div className="admin-page-header">
        <div><h2 className="admin-page-title">{data.title}</h2><p className="admin-page-subtitle">{data.city_name} · {categoryText(data.category)} · ID {data.id}</p></div>
        <button type="button" className="admin-btn admin-btn-primary" disabled={busy} onClick={() => { setEditing((current) => !current); setForm(toForm(data)) }}>{editing ? 'Отменить редактирование' : 'Редактировать'}</button>
      </div>

      {notice && <p className="admin-success-text">{notice}</p>}
      {error && <AdminError message={error} />}

      <div className="admin-status-strip">
        <span className={`admin-badge pub-${data.publication_status}`}>{publicationStatusText(data.publication_status)}</span>
        <span className="admin-badge">{verificationStatusText(data.verification_status)}</span>
        <span className="admin-badge">Качество {data.quality_score}% · {data.quality_tier}</span>
        <span className="admin-badge">Уверенность {data.existence_confidence_score}%</span>
        <span className="admin-badge">В маршрутах: {data.route_enabled ? 'да' : 'нет'}</span>
      </div>

      {data.image_url && <img className="admin-place-hero" src={data.image_url} alt={data.title} onError={(event) => { event.currentTarget.hidden = true }} />}

      {editing ? (
        <>
          <AdminPlaceForm value={form} onChange={setForm} citySlug={data.city_slug || undefined} showPublication disabled={busy} />
          <div className="admin-sticky-actions"><span className="admin-muted">Все изменения попадут в журнал аудита.</span><button type="button" className="admin-btn admin-btn-primary" disabled={busy} onClick={() => void save()}>{busy ? 'Сохраняем…' : 'Сохранить изменения'}</button></div>
        </>
      ) : (
        <>
          <section className="admin-detail-grid">
            <div className="admin-detail-panel"><h3>Основное</h3><p><strong>Адрес:</strong> {data.address || 'Не указан'}</p><p><strong>Координаты:</strong> {data.lat}, {data.lng}</p><p><strong>Описание:</strong> {data.short_description || 'Не заполнено'}</p><p><strong>Часы:</strong> {openingHoursText(data.opening_hours) || 'Не указаны'}</p></div>
            <div className="admin-detail-panel"><h3>Контакты</h3><p><strong>Телефон:</strong> {data.phone || 'Не указан'}</p><p><strong>Сайт:</strong> {data.website ? <a href={data.website} target="_blank" rel="noreferrer">Открыть</a> : 'Не указан'}</p><p><strong>Источник:</strong> {data.source || 'Не указан'}</p></div>
            <div className="admin-detail-panel"><h3>Качество</h3><p>Полнота: {data.completeness_score}/40</p><p>Фото: {data.photo_score}/25</p><p>Описание: {data.description_score}/15</p><p>Свежесть: {data.freshness_score}/10</p></div>
            <div className="admin-detail-panel"><h3>Использование</h3><p>Шаблонных маршрутов: {data.route_usage_count}</p><p className="admin-muted">{data.route_usage_note}</p><p>Теги: {data.tags.map((tag) => tag.name).join(', ') || 'нет'}</p></div>
          </section>
          <section className="admin-action-toolbar">
            <button className="admin-btn admin-btn-ok" disabled={busy} onClick={() => void action('verify', {}, 'Место подтверждено')}>Подтвердить</button>
            <button className="admin-btn" disabled={busy || data.publication_status === 'published'} onClick={() => void action('publish', {}, 'Место опубликовано')}>Опубликовать</button>
            <button className="admin-btn admin-btn-danger" disabled={busy || data.publication_status === 'rejected'} onClick={reject}>Отклонить</button>
            <button className="admin-btn admin-btn-danger" disabled={busy || data.publication_status !== 'published'} onClick={unpublish}>Скрыть с сайта</button>
            <button className="admin-btn" disabled={busy} onClick={() => void refreshAddress()}>Обновить адрес</button>
            <Link className="admin-btn" to={`/admin/audit?entity_id=${data.id}`}>Полный аудит</Link>
          </section>
          <section className="admin-detail-panel">
            <h3>Экстренное скрытие</h3>
            <p className="admin-muted">Скрывает место из каталога, поиска и маршрутов без удаления данных.</p>
            <label className="admin-field" htmlFor="emergency-hide-reason">
              <span>Причина скрытия</span>
              <textarea
                id="emergency-hide-reason"
                value={emergencyReason}
                disabled={busy}
                onChange={(event) => setEmergencyReason(event.target.value)}
                placeholder="Например: подтверждена жалоба, место закрыто или данные опасно неверны"
              />
            </label>
            <label className="admin-checkbox-row">
              <input
                type="checkbox"
                checked={emergencyConfirmed}
                disabled={busy}
                onChange={(event) => setEmergencyConfirmed(event.target.checked)}
              />
              Подтверждаю экстренное скрытие места
            </label>
            <button
              type="button"
              className="admin-btn admin-btn-danger"
              disabled={busy || emergencyReason.trim().length < 10 || !emergencyConfirmed}
              onClick={() => void emergencyHide()}
            >
              {busy ? 'Скрываем…' : 'Экстренно скрыть место'}
            </button>
          </section>
        </>
      )}

      {data.audit_history.length > 0 && <section className="admin-detail-panel"><h3>Последние изменения</h3><div className="admin-audit-list">{data.audit_history.map((item, index) => <div key={item.id ?? index}><strong>{item.action}</strong><span>{item.actor} · {new Date(item.created_at).toLocaleString('ru-RU')}</span>{item.reason && <span>{item.reason}</span>}</div>)}</div></section>}
    </div>
  )
}
