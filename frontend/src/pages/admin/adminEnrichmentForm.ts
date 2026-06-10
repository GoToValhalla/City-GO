import { useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import type { AdminCity, AdminCitiesResponse } from './adminTypes'

const MISSING_FIELDS = [
  { key: 'address', label: 'Адрес' },
  { key: 'website', label: 'Сайт' },
  { key: 'phone', label: 'Телефон' },
  { key: 'opening_hours', label: 'Часы работы' },
  { key: 'photo', label: 'Фото' },
  { key: 'description', label: 'Описание' },
  { key: 'menu_url', label: 'Меню' },
  { key: 'social_links', label: 'Соцсети' },
  { key: 'price_level', label: 'Ценовой уровень' },
  { key: 'dog_friendly', label: 'Можно с собакой' },
  { key: 'family_friendly', label: 'Семейное' },
  { key: 'outdoor', label: 'На улице' },
  { key: 'indoor', label: 'В помещении' },
]

export const useEnrichmentForm = () => {
  const [cities, setCities] = useState<AdminCity[]>([])
  const [citySlug, setCitySlug] = useState('')
  const [limit, setLimit] = useState(100)
  const [onlyPublished, setOnlyPublished] = useState(true)
  const [onlyRouteEligible, setOnlyRouteEligible] = useState(false)
  const [selectedFields, setSelectedFields] = useState<string[]>(['address', 'photo'])

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=50')
      .then((r) => {
        setCities(r.items)
        if (r.items[0]) setCitySlug(r.items[0].slug)
      })
      .catch(() => {})
  }, [])

  const toggleField = (key: string) =>
    setSelectedFields((prev) =>
      prev.includes(key) ? prev.filter((f) => f !== key) : [...prev, key],
    )

  return {
    cities, citySlug, setCitySlug, limit, setLimit,
    onlyPublished, setOnlyPublished,
    onlyRouteEligible, setOnlyRouteEligible,
    selectedFields, toggleField,
  }
}

export { MISSING_FIELDS }
