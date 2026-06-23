import { useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import { categoryText } from './adminRouteCopy'
import type { AdminTaxonomyCategory, AdminTaxonomyResponse } from './adminTypes'

type Props = {
  value: string
  onChange: (value: string) => void
  includeAll?: boolean
  ariaLabel?: string
  citySlug?: string
}

const fallbackCategories: AdminTaxonomyCategory[] = [
  'attraction', 'museum', 'park', 'walk', 'coffee', 'food', 'bar', 'beach',
  'shopping_mall', 'pharmacy', 'clinic', 'hospital', 'healthcare', 'bank', 'atm',
  'transport', 'bus_stop', 'parking', 'police', 'toilets', 'information', 'service',
].map((code) => ({
  code,
  label: categoryText(code),
  is_active: true,
  is_route_eligible: false,
  is_catalog_visible: false,
  is_default_enabled: true,
  is_observed: false,
  observed_count: 0,
  source: 'fallback',
}))

const categoryOptionLabel = (item: AdminTaxonomyCategory) => {
  const label = item.label || categoryText(item.code)
  const count = item.is_observed ? ` · ${item.observed_count}` : ''
  return `${label} (${item.code})${count}`
}

const taxonomyPath = (citySlug?: string) => {
  const sp = new URLSearchParams()
  if (citySlug) sp.set('city_slug', citySlug)
  const qs = sp.toString()
  return `/admin/taxonomy/categories${qs ? `?${qs}` : ''}`
}

export const AdminCategorySelect = ({ value, onChange, includeAll = false, ariaLabel = 'Категория', citySlug }: Props) => {
  const [items, setItems] = useState<AdminTaxonomyCategory[]>(fallbackCategories)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    void Promise.resolve().then(() => { if (alive) setFailed(false) })
    adminGet<AdminTaxonomyResponse>(taxonomyPath(citySlug))
      .then((payload) => {
        if (alive && payload.categories.length) setItems(payload.categories)
      })
      .catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [citySlug])

  return (
    <label className="admin-field-inline">
      <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={ariaLabel}>
        {includeAll && <option value="">Все категории</option>}
        {items.map((item) => (
          <option key={item.code} value={item.code}>{categoryOptionLabel(item)}</option>
        ))}
      </select>
      {failed && <span className="admin-muted">Справочник категорий недоступен, показан базовый список.</span>}
    </label>
  )
}
