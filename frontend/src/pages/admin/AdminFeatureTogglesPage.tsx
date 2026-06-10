import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminGet, adminPut } from './adminApi'
import { AdminFeatureToggleRow } from './AdminFeatureToggleRow'
import type { AdminCitiesResponse } from './adminTypes'
import { AdminError, AdminLoading } from './shared/AdminStates'

type Toggle = {
  key: string
  label?: string | null
  description?: string | null
  value_bool: boolean
  default?: boolean | null
  group?: string | null
  updated_by?: string | null
  updated_at?: string | null
}

type Group = { code: string; label: string }

const GROUP_LABELS: Record<string, string> = {
  product: 'Продукт', routes: 'Маршруты', ai: 'AI', moderation: 'Модерация',
  data: 'Данные', system: 'Система', visibility: 'Видимость', channels: 'Каналы', quality: 'Качество',
}

export const AdminFeatureTogglesPage = () => {
  const [params, setParams] = useSearchParams()
  const scope = params.get('scope') === 'city' ? 'city' : 'global'
  const citySlug = params.get('city') ?? ''
  const [items, setItems] = useState<Toggle[]>([])
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const apiPath = scope === 'city' && citySlug
    ? `/admin/feature-toggles?scope=city&city_slug=${encodeURIComponent(citySlug)}`
    : '/admin/feature-toggles?scope=global'

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([
      adminGet<{ items: Toggle[] }>(apiPath),
      adminGet<Group[]>('/admin/feature-toggles/groups').catch(() => []),
      adminGet<AdminCitiesResponse>('/admin/cities?limit=100').catch(() => ({ items: [] })),
    ])
      .then(([toggles, grp, cityData]) => {
        setItems(toggles.items)
        setGroups(grp.length ? grp : Object.entries(GROUP_LABELS).map(([code, label]) => ({ code, label })))
        setCities(cityData.items)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [scope, citySlug]) // eslint-disable-line react-hooks/exhaustive-deps

  const grouped = useMemo(() => {
    const map = new Map<string, Toggle[]>()
    items.forEach((t) => {
      const g = t.group ?? 'other'
      map.set(g, [...(map.get(g) ?? []), t])
    })
    return map
  }, [items])

  const setScope = (next: 'global' | 'city') => {
    const p = new URLSearchParams(params)
    p.set('scope', next)
    if (next === 'global') p.delete('city')
    setParams(p)
  }

  const toggle = async (key: string, next: boolean) => {
    const label = items.find((t) => t.key === key)?.label ?? key
    if (!window.confirm(`Изменить «${label}» на ${next ? 'включено' : 'выключено'}?`)) return
    setBusy(key)
    try {
      const q = scope === 'city' && citySlug
        ? `?scope=city&city_slug=${encodeURIComponent(citySlug)}`
        : '?scope=global'
      await adminPut(`/admin/feature-toggles/${encodeURIComponent(key)}${q}`, { value_bool: next, reason: 'Изменено в админке' })
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка сохранения')
    } finally { setBusy(null) }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />

  return (
    <div>
      <h2 className="admin-page-title">Фичи и настройки</h2>
      <p className="admin-page-subtitle">Переключатели влияют на backend-логику, не только на UI</p>
      <div className="admin-filters admin-filters-stack">
        <button type="button" className={scope === 'global' ? 'admin-tab active' : 'admin-tab'} onClick={() => setScope('global')}>Глобальные</button>
        <button type="button" className={scope === 'city' ? 'admin-tab active' : 'admin-tab'} onClick={() => setScope('city')}>По городу</button>
        {scope === 'city' && (
          <select value={citySlug} onChange={(e) => { const p = new URLSearchParams(params); p.set('scope', 'city'); p.set('city', e.target.value); setParams(p) }}>
            <option value="">Выберите город</option>
            {cities.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
          </select>
        )}
      </div>
      {scope === 'city' && !citySlug ? (
        <p className="admin-state">Выберите город для настройки переключателей</p>
      ) : (
        groups.map((g) => grouped.has(g.code) ? (
          <section key={g.code} className="admin-section">
            <h3 className="admin-section-title">{g.label}</h3>
            <div className="admin-toggle-list">
              {(grouped.get(g.code) ?? []).map((t) => (
                <AdminFeatureToggleRow key={t.key} item={t} busy={busy} onToggle={toggle} />
              ))}
            </div>
          </section>
        ) : null)
      )}
    </div>
  )
}
