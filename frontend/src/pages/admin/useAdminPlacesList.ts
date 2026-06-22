import { useCallback, useState } from 'react'
import { adminGet } from './adminApi'
import type { AdminPlace, AdminPlacesResponse } from './adminTypes'

const PAGE_SIZE = 50

export type PlacesListFilters = {
  citySlug: string
  preset: string
  pubStatus: string
  verifyStatus: string
  category: string
  routeEligible: string
  q: string
}

const buildQuery = (filters: PlacesListFilters, offset: number) => {
  const sp = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) })
  if (filters.citySlug) sp.set('city_slug', filters.citySlug)
  if (filters.preset) sp.set('preset', filters.preset)
  if (filters.pubStatus) sp.set('publication_status', filters.pubStatus)
  if (filters.verifyStatus) sp.set('verification_status', filters.verifyStatus)
  if (filters.category) sp.set('category', filters.category)
  if (filters.routeEligible) sp.set('route_eligible', filters.routeEligible)
  if (filters.q) sp.set('q', filters.q)
  return sp.toString()
}

export const useAdminPlacesList = (filters: PlacesListFilters) => {
  const [items, setItems] = useState<AdminPlace[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const hasMore = items.length < total

  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    adminGet<AdminPlacesResponse>(`/admin/places?${buildQuery(filters, 0)}`)
      .then((r) => { setItems(r.items); setTotal(r.total) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [filters])

  const loadMore = useCallback(() => {
    if (loading || loadingMore || !hasMore) return
    setLoadingMore(true)
    adminGet<AdminPlacesResponse>(`/admin/places?${buildQuery(filters, items.length)}`)
      .then((r) => {
        setItems((prev) => [...prev, ...r.items])
        setTotal(r.total)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingMore(false))
  }, [filters, hasMore, items.length, loading, loadingMore])

  return { items, total, loading, loadingMore, error, hasMore, reload, loadMore, setError }
}
