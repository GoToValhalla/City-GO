import { useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import { categoryText } from './adminRouteCopy'
import type { AdminTaxonomyCategory, AdminTaxonomyResponse } from './adminTypes'

type Props = {
  value: string
  onChange: (value: string) => void
  includeAll?: boolean
  ariaLabel?: string
}

const fallbackCategories: AdminTaxonomyCategory[] = [
  'attraction', 'museum', 'park', 'walk', 'coffee', 'food', 'bar', 'beach',
  'culture', 'viewpoint', 'transport', 'useful', 'health',
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

export const AdminCategorySelect = ({ value, onChange, includeAll = false, ariaLabel = 'Категория' }: Props) => {
  const [items, setItems] = useState<AdminTaxonomyCategory[]>(fallbackCategories)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    adminGet<AdminTaxonomyResponse>('/admin/taxonomy/categories')
      .then((payload) => {
        if (alive && payload.categories.length) setItems(payload.categories)
      })
      .catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [])

  return (
    <label className="admin-field-inline">
      <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={ariaLabel}>
        {includeAll && <option value="">Все категории</option>}
        {items.map((item) => (
          <option key={item.code} value={item.code}>
            {item.label || categoryText(item.code)}{item.is_observed ? ` · ${item.observed_count}` : ''}
          </option>
        ))}
      </select>
      {failed && <span className="admin-muted">Справочник категорий недоступен, показан базовый список.</span>}
    </label>
  )
}
