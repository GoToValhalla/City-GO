import { useCallback, useRef, useState } from 'react'
import { adminGet } from './adminApi'
import type { AdminPlace, AdminPlacesResponse } from './adminTypes'

export type PlacesListFilters = {
  citySlug: string
  preset: string
  pubStatus: string
  verifyStatus: string
  category: string
  routeEligible: string
  active: string
  searchable: string
  hasPhoto: string
  hasAddress: string
  hasDescription: string
  hasPhone: string
  hasWebsite: string
  hasHours: string
  lowConfidence: string
  qualityTier: string
  source: string
  sort: string
  direction: string
  limit: number
  q: string
}

const buildQuery = (filters: PlacesListFilters, offset: number) => {
  const sp = new URLSearchParams({ limit: String(filters.limit), offset: String(offset), sort: filters.sort, direction: filters.direction })
  const values: Record<string, string> = {
    city_slug: filters.citySlug,
    preset: filters.preset,
    publication_status: filters.pubStatus,
    verification_status: filters.verifyStatus,
    category: filters.category,
    route_eligible: filters.routeEligible,
    is_active: filters.active,
    searchable: filters.searchable,
    has_photo: filters.hasPhoto,
    has_address: filters.hasAddress,
    has_description: filters.hasDescription,
    has_phone: filters.hasPhone,
    has_website: filters.hasWebsite,
    has_opening_hours: filters.hasHours,
    low_confidence: filters.lowConfidence,
    quality_tier: filters.qualityTier,
    source: filters.source,
    q: filters.q,
  }
  Object.entries(values).forEach(([key, value]) => { if (value) sp.set(key, value) })
  return sp.toString()
}

export const useAdminPlacesList = (filters: PlacesListFilters) => {
  const [items, setItems] = useState<AdminPlace[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestSequence = useRef(0)
  const hasMore = items.length < total

  const reload = useCallback(async () => {
    const requestId = ++requestSequence.current
    setLoading(true)
    setError(null)
    try {
      const response = await adminGet<AdminPlacesResponse>(`/admin/places/search?${buildQuery(filters, 0)}`)
      if (requestId !== requestSequence.current) return
      setItems(response.items)
      setTotal(response.total)
    } catch (caught) {
      if (requestId === requestSequence.current) setError(caught instanceof Error ? caught.message : 'Не удалось загрузить места')
    } finally {
      if (requestId === requestSequence.current) setLoading(false)
    }
  }, [filters])

  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const response = await adminGet<AdminPlacesResponse>(`/admin/places/search?${buildQuery(filters, items.length)}`)
      setItems((current) => [...current, ...response.items.filter((item) => !current.some((existing) => existing.id === item.id))])
      setTotal(response.total)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить следующую страницу')
    } finally {
      setLoadingMore(false)
    }
  }, [filters, hasMore, items.length, loading, loadingMore])

  return { items, total, loading, loadingMore, error, hasMore, reload, loadMore, setError }
}
