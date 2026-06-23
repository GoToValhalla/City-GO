import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminPlaceForm, type AdminPlaceFormValue } from './AdminPlaceForm'
import type { AdminCitiesResponse } from './adminTypes'
import { AdminError } from './shared/AdminStates'

type LookupCandidate = { title?: string; address?: string; lat?: number; lng?: number; source?: string; error?: string }
type LookupResponse = { candidates: LookupCandidate[]; similar_places: Array<{ id: number; title: string; match_reason: string }> }

const emptyForm = (): AdminPlaceFormValue => ({
  title: '', category: 'attraction', address: '', lat: '', lng: '', shortDescription: '', imageUrl: '', website: '', phone: '',
  source: 'admin_manual', sourceUrl: '', atmosphere: '', inside: '', bestFor: '', openingHours: '', visitDuration: '', priceLevel: '',
  indoor: false, outdoor: false, dogFriendly: false, familyFriendly: false, isActive: true, visibleToUsers: false, searchable: false,
  routeEnabled: false, routeExclusionReason: '', adminComment: '',
})

const optionalNumber = (value: string) => value.trim() ? Number(value) : null
const optionalText = (value: string) => value.trim() || null

export const AdminPlaceCreatePage = () => {
  const nav = useNavigate()
  const [searchParams] = useSearchParams()
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [cityId, setCityId] = useState(0)
  const [query, setQuery] = useState('')
  const [form, setForm] = useState<AdminPlaceFormValue>(emptyForm)
  const [candidates, setCandidates] = useState<LookupCandidate[]>([])
  const [dupes, setDupes] = useState<LookupResponse['similar_places']>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((response) => {
      setCities(response.items)
      const requested = response.items.find((city) => city.slug === searchParams.get('city'))
      if (requested ?? response.items[0]) setCityId((requested ?? response.items[0]).id)
    }).catch((caught: Error) => setError(caught.message))
  }, [searchParams])

  const city = useMemo(() => cities.find((item) => item.id === cityId), [cities, cityId])

  const selectCandidate = (candidate: LookupCandidate) => {
    setForm((current) => ({
      ...current,
      title: String(candidate.title || query),
      address: String(candidate.address || ''),
      lat: candidate.lat === undefined ? current.lat : String(candidate.lat),
      lng: candidate.lng === undefined ? current.lng : String(candidate.lng),
      source: candidate.source || current.source,
    }))
  }

  const search = async () => {
    if (!cityId || !query.trim()) return
    setBusy(true)
    setError(null)
    try {
      const response = await adminPost<LookupResponse>('/admin/places/lookup', { city_id: cityId, title: query.trim() })
      setCandidates(response.candidates)
      setDupes(response.similar_places)
      const first = response.candidates.find((candidate) => candidate.lat !== undefined && candidate.lng !== undefined && !candidate.error)
      if (first) selectCandidate(first)
      else setForm((current) => ({ ...current, title: query.trim() }))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось найти место')
    } finally {
      setBusy(false)
    }
  }

  const create = async () => {
    const lat = Number(form.lat)
    const lng = Number(form.lng)
    if (!form.title.trim()) return setError('Укажите название места')
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return setError('Найдите место или укажите корректные координаты')

    setBusy(true)
    setError(null)
    try {
      const duplicateResponse = await adminPost<{ items: typeof dupes }>('/admin/places/check-duplicates', {
        city_id: cityId, title: form.title.trim(), address: optionalText(form.address), lat, lng,
      })
      setDupes(duplicateResponse.items)
      if (duplicateResponse.items.length && !window.confirm(`Найдено похожих мест: ${duplicateResponse.items.length}. Всё равно создать новый черновик?`)) return

      const created = await adminPost<{ id: number }>('/admin/places/create-draft', {
        city_id: cityId,
        title: form.title.trim(),
        category: form.category,
        source: form.source,
        source_url: optionalText(form.sourceUrl),
        address: optionalText(form.address),
        lat,
        lng,
        short_description: optionalText(form.shortDescription),
        image_url: optionalText(form.imageUrl),
        website: optionalText(form.website),
        phone: optionalText(form.phone),
        atmosphere: optionalText(form.atmosphere),
        inside: optionalText(form.inside),
        best_for: optionalText(form.bestFor),
        opening_hours: form.openingHours.trim() ? { display: form.openingHours.trim(), raw: form.openingHours.trim() } : null,
        average_visit_duration_minutes: optionalNumber(form.visitDuration),
        price_level: optionalNumber(form.priceLevel),
        indoor: form.indoor,
        outdoor: form.outdoor,
        dog_friendly: form.dogFriendly,
        family_friendly: form.familyFriendly,
        route_enabled: form.routeEnabled,
        admin_comment: optionalText(form.adminComment),
      })
      nav(`/admin/places/${created.id}`, { replace: true })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось создать место')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <Link to={`/admin/places${city?.slug ? `?city=${city.slug}` : ''}`} className="admin-back-link">← К списку мест</Link>
      <div className="admin-page-header">
        <div><h2 className="admin-page-title">Новое место</h2><p className="admin-page-subtitle">Сначала найдите объект, затем проверьте и дополните его данные.</p></div>
      </div>

      <section className="admin-filter-card">
        <div className="admin-help-title">1. Найти объект и координаты</div>
        <div className="admin-search-row">
          <select aria-label="Город" value={cityId} onChange={(event) => setCityId(Number(event.target.value))}>
            {cities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <input aria-label="Название или адрес" placeholder="Название или адрес" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void search() }} />
          <button type="button" className="admin-btn admin-btn-primary" disabled={busy || !query.trim() || !cityId} onClick={() => void search()}>{busy ? 'Ищем…' : 'Найти'}</button>
        </div>
        {candidates.length > 0 && <div className="admin-candidate-list">{candidates.map((candidate, index) => (
          <button key={`${candidate.title}-${index}`} type="button" className="admin-candidate" disabled={Boolean(candidate.error)} onClick={() => selectCandidate(candidate)}>
            <strong>{candidate.title || 'Без названия'}</strong><span>{candidate.error || candidate.address || 'Адрес не указан'}</span>
          </button>
        ))}</div>}
      </section>

      <div className="admin-help-title">2. Проверить и заполнить карточку</div>
      <AdminPlaceForm value={form} onChange={setForm} citySlug={city?.slug} disabled={busy} />
      {error && <AdminError message={error} />}
      {dupes.length > 0 && <section className="admin-warning-panel"><strong>Похожие места</strong>{dupes.map((duplicate) => <Link key={duplicate.id} to={`/admin/places/${duplicate.id}`}>{duplicate.title} · {duplicate.match_reason}</Link>)}</section>}
      <div className="admin-sticky-actions">
        <span className="admin-muted">Новое место будет сохранено как черновик и не появится у пользователей автоматически.</span>
        <button type="button" className="admin-btn admin-btn-primary" disabled={busy || !form.title.trim() || !form.lat || !form.lng} onClick={() => void create()}>{busy ? 'Сохраняем…' : 'Создать черновик'}</button>
      </div>
    </div>
  )
}
