import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCityCreateForm } from './AdminCityCreateForm'
import { AdminCitySettingsPanel, type CitySettings } from './AdminCitySettingsPanel'
import type { AdminCitiesResponse } from './adminTypes'
import type { CityReadiness } from './adminRouteTypes'
import { AdminError, AdminLoading } from './shared/AdminStates'

export const AdminCitiesPage = () => {
  const [data, setData] = useState<AdminCitiesResponse | null>(null)
  const [settings, setSettings] = useState<CitySettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
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

  useEffect(() => { reload() }, [reload])

  const openSettings = (slug: string) => {
    adminGet<CitySettings>(`/admin/cities/${slug}/settings`).then(setSettings).catch((e: Error) => setError(e.message))
  }

  const refreshAddresses = async (slug: string) => {
    if (!window.confirm(`Обновить адреса города ${slug}?`)) return
    await adminPost('/admin/places/address-refresh', { city_slug: slug })
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />

  return (
    <div>
      <h2 className="admin-page-title">Города</h2>
      <AdminCityCreateForm onCreated={reload} />
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
                  <td><strong>{c.name}</strong><div className="admin-muted">{c.slug}</div></td>
                  <td>{c.launch_status ?? '—'}</td>
                  <td>
                    {readiness[c.slug] ? (
                      <span className={`admin-quality admin-quality-${readiness[c.slug].status === 'ready' ? 'green' : readiness[c.slug].status === 'needs_review' ? 'yellow' : 'red'}`}>
                        {readiness[c.slug].readiness_score}% · {readiness[c.slug].status}
                      </span>
                    ) : '—'}
                  </td>
                  <td>{c.places_total ?? 0}</td>
                  <td className="admin-actions-cell">
                    <button type="button" className="admin-btn admin-btn-sm" onClick={() => openSettings(c.slug)}>Настройки</button>
                    <Link className="admin-btn admin-btn-sm" to={`/admin/coverage?city=${c.slug}`}>Покрытие</Link>
                    <Link className="admin-btn admin-btn-sm" to={`/admin/routes/data-quality?city=${c.slug}`}>Quality</Link>
                    <button type="button" className="admin-btn admin-btn-sm" onClick={() => refreshAddresses(c.slug)}>Адреса</button>
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
