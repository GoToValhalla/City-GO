import { useEffect, useMemo, useState } from 'react'
import { adminGet, adminPost } from './adminApi'

type City = { slug: string; name: string; needs_review: number; rejected: number }
type Place = { id: number; title: string; category?: string | null; address?: string | null; short_description?: string | null; image_url?: string | null; image_urls?: string[] | null; photo_urls?: string[] | null; publication_status?: string | null; publication_blockers?: string[] }
type NextPayload = { remaining: number; place: Place | null }

const getPhotos = (place: Place | null) => [...new Set([...(place?.image_urls ?? []), ...(place?.photo_urls ?? []), place?.image_url].filter(Boolean) as string[])]

export const AdminMobileToolsPage = () => {
  const [cities, setCities] = useState<City[]>([])
  const [citySlug, setCitySlug] = useState('')
  const [place, setPlace] = useState<Place | null>(null)
  const [rejected, setRejected] = useState<Place[]>([])
  const [remaining, setRemaining] = useState(0)
  const [photoIndex, setPhotoIndex] = useState(0)
  const [mode, setMode] = useState<'queue' | 'rejected'>('queue')
  const [message, setMessage] = useState('')
  const photos = useMemo(() => getPhotos(place), [place])
  const photo = photos[photoIndex] ?? photos[0]

  const loadCities = async () => {
    const data = await adminGet<{ items: City[] }>('/admin/mobile-tools/cities')
    setCities(data.items)
    if (!citySlug && data.items[0]) setCitySlug(data.items[0].slug)
  }
  const loadNext = async (slug = citySlug) => {
    if (!slug) return
    const data = await adminGet<NextPayload>(`/admin/mobile-tools/places/next?city_slug=${encodeURIComponent(slug)}`)
    setPlace(data.place)
    setRemaining(data.remaining)
    setPhotoIndex(0)
    setMode('queue')
  }
  const loadRejected = async () => {
    const data = await adminGet<{ items: Place[] }>(`/admin/mobile-tools/places/rejected?city_slug=${encodeURIComponent(citySlug)}`)
    setRejected(data.items)
    setMode('rejected')
  }
  const act = async (action: 'publish' | 'reject' | 'defer') => {
    if (!place) return
    await adminPost(`/admin/mobile-tools/places/${place.id}/${action}`, {})
    setMessage(action)
    await loadNext()
    await loadCities()
  }

  useEffect(() => { void loadCities() }, [])
  useEffect(() => { if (citySlug) void loadNext(citySlug) }, [citySlug])

  return <main className="admin-page">
    <h2 className="admin-page-title">Мобильные инструменты</h2>
    <section className="admin-filter-card">
      <select value={citySlug} onChange={(event) => setCitySlug(event.target.value)} aria-label="Город">
        {cities.map((city) => <option key={city.slug} value={city.slug}>{city.name} · {city.needs_review} · {city.rejected}</option>)}
      </select>
      <button className="admin-btn admin-btn-sm" type="button" onClick={() => loadNext()}>Следующая</button>
      <button className="admin-btn admin-btn-sm" type="button" onClick={loadRejected}>Отклонённые</button>
    </section>
    {message ? <p className="admin-success-text">{message}</p> : null}
    {mode === 'rejected' ? <section className="admin-card">{rejected.map((item) => <article key={item.id} className="admin-help-panel"><strong>{item.title}</strong><button className="admin-btn admin-btn-sm" type="button" onClick={async () => { await adminPost(`/admin/mobile-tools/places/${item.id}/defer`, {}); await loadRejected(); await loadCities() }}>↩</button></article>)}</section> : <section className="admin-card">
      <p className="admin-muted">Осталось: {remaining}</p>
      {place ? <>
        {photo ? <img src={photo} alt={place.title} style={{ width: '100%', maxHeight: 260, objectFit: 'cover', borderRadius: 16 }} /> : <p>Фото нет</p>}
        {photos.length > 1 ? <div>{photos.map((_, index) => <button key={index} className="admin-btn admin-btn-sm" type="button" onClick={() => setPhotoIndex(index)}>Фото {index + 1}</button>)}</div> : null}
        <h3>{place.title}</h3>
        <p>{place.category || 'без категории'} · {place.address || 'адрес не указан'}</p>
        <p>{place.short_description || 'описание не заполнено'}</p>
        <button className="admin-btn admin-btn-sm admin-btn-primary" type="button" onClick={() => act('publish')}>Опубликовать</button>
        <button className="admin-btn admin-btn-sm" type="button" onClick={() => act('reject')}>Отклонить</button>
        <button className="admin-btn admin-btn-sm" type="button" onClick={() => act('defer')}>В конец очереди</button>
      </> : <p>Очередь пуста.</p>}
    </section>}
  </main>
}
