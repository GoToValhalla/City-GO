import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCityCreateForm } from './AdminCityCreateForm'
import { AdminCitySettingsPanel, type CitySettings } from './AdminCitySettingsPanel'
import type { AdminCitiesResponse, AdminCityPublicationResponse } from './adminTypes'
import type { CityReadiness } from './adminRouteTypes'
import { AdminError, AdminLoading } from './shared/AdminStates'

const CITY_STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик',
  importing: 'Импортируется',
  review_required: 'На проверке',
  import_failed: 'Ошибка импорта',
  unpublished: 'Снят с сайта',
  published: 'Опубликован',
}

export const AdminCitiesPage = () => {
  const [data, setData] = useState<AdminCitiesResponse | null>(null)
  const [settings, setSettings] = useState<CitySettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyCityId, setBusyCityId] = useState<number | null>(null)
  const [readiness, setReadiness] = useState<Record<string, CityReadiness>>({})

  const reload = useCallback(() => {
    setLoading(true)
    Promise.all([
      adminGet<AdminCitiesResponse>('/admin/cities?limit=100'),
      adminGet<{ items: CityReadiness[] }>('/admin/routes/readiness'),
    ])
      .then(([citiesRes, readinessRes]) => {
        setData(citiesRes)
        setReadiness(Object.fromEntries(readinessRes.items.map((r) => [r.city_slug, r])))
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { void Promise.resolve().then(reload) }, [reload])

  const openSettings = (slug: string) => {
    adminGet<CitySettings>(`/admin/cities/${slug}/settings`).then(setSettings).catch((e: Error) => setError(e.message))
  }

  const refreshAddresses = async (slug: string) => {
    if (!window.confirm(`Обновить адреса города ${slug}?`)) return
    await adminPost('/admin/places/address-refresh', { city_slug: slug })
  }

  const publishCity = async (cityId: number, cityName: string) => {
    if (!window.confirm(`Опубликовать город ${cityName} на сайте?`)) return
    setBusyCityId(cityId)
    setError(null)
    setNotice(null)
    try {
      const response = await adminPost<AdminCityPublicationResponse>(`/admin/cities/${cityId}/publish`, {})
      setNotice(response.message)
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка публикации города')
    } finally {
      setBusyCityId(null)
    }
  }

  const unpublishCity = async (cityId: number, cityName: string) => {
    const reason = window.prompt(`Причина снятия города ${cityName} с сайта`, 'Ручное снятие с публикации')
    if (!reason) return
    setBusyCityId(cityId)
    setError(null)
    setNotice(null)
    try {
      const response = await adminPost<AdminCityPublicationResponse>(`/admin/cities/${cityId}/unpublish`, { reason })
      setNotice(response.message)
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка снятия города')
    } finally {
      setBusyCityId(null)
    }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />

  return (
    <div>
      <h2 className="admin-page-title">Города</h2>
      <AdminCityCreateForm onCreated={reload} />
      {notice && <p className="admin-success-text">{notice}</p>}
      {!data?.items.length ? (
        <p className="admin-muted">Города пока не созданы. После создания они появятся в списке и в разделе Импорты.</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr><th>Город</th><th>Статус</th><th>Readiness</th><th>Мест</th><th>Действия</th></tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/admin/cities/${c.slug}`}><strong>{c.name}</strong></Link><div className="admin-muted">{c.slug}</div></td>
                  <td>{CITY_STATUS_LABELS[c.launch_status ?? ''] ?? c.launch_status ?? '—'}{c.is_active ? <div className="admin-muted">активен</div> : <div className="admin-muted">скрыт</div>}</td>
                  <td>
                    {readiness[c.slug] ? (
                      <span className={`admin-quality admin-quality-${readiness[c.slug].status === 'ready' ? 'green' : readiness[c.slug].status === 'needs_review' ? 'yellow' : 'red'}`}>
                        {readiness[c.slug].readiness_score}% · {readiness[c.slug].status}
                      </span>
                    ) : '—'}
                  </td>
                  <td>{c.places_total ?? 0}<div className="admin-muted">на сайте: {c.places_published ?? 0}</div></td>
                  <td className="admin-actions-cell">
                    <button type="button" className="admin-btn admin-btn-sm" onClick={() => openSettings(c.slug)}>Настройки</button>
                    <Link className="admin-btn admin-btn-sm" to={`/admin/coverage?city=${c.slug}`}>Покрытие</Link>
                    <Link className="admin-btn admin-btn-sm" to={`/admin/routes/data-quality?city=${c.slug}`}>Quality</Link>
                    <button type="button" className="admin-btn admin-btn-sm" onClick={() => void refreshAddresses(c.slug)}>Адреса</button>
                    {c.can_publish && <button type="button" className="admin-btn admin-btn-sm" disabled={busyCityId === c.id} onClick={() => void publishCity(c.id, c.name)}>Опубликовать</button>}
                    {c.can_unpublish && <button type="button" className="admin-btn admin-btn-sm admin-btn-danger" disabled={busyCityId === c.id} onClick={() => void unpublishCity(c.id, c.name)}>Снять</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {settings && (
        <AdminCitySettingsPanel
          settings={settings}
          busy={null}
          onClose={() => setSettings(null)}
          onRefresh={openSettings}
          onError={setError}
        />
      )}
    </div>
  )
}
