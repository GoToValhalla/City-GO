import { useCallback, useEffect, useState } from 'react'
import { getPlacesByCityResponse } from '../../api/places/places.api'
import type { Place } from '../../entities/place/model/types'

const PAGE_SIZE = 50

export type PlacesPaginationState = {
  places: Place[]
  total: number
  loading: boolean
  error: string | null
  hasMore: boolean
  loadMore: () => void
  retry: () => void
}

/**
 * Хук пагинации для списка мест.
 * При смене citySlug сбрасывает список и загружает первую страницу.
 * loadMore() дозагружает следующую страницу (вызывается IntersectionObserver).
 */
export const usePlacesPagination = (citySlug: string): PlacesPaginationState => {
  const [places, setPlaces] = useState<Place[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)

  const loadPage = useCallback(async (slug: string, pageOffset: number) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getPlacesByCityResponse(slug, PAGE_SIZE, pageOffset)
      setPlaces(prev => pageOffset === 0 ? data.items : [...prev, ...data.items])
      setTotal(data.total)
      const loaded = pageOffset + data.items.length
      setOffset(loaded)
      setHasMore(loaded < data.total)
    } catch (err) {
      console.error(err)
      setError('Не удалось загрузить места')
      if (pageOffset === 0) {
        setPlaces([])
        setTotal(0)
        setOffset(0)
        setHasMore(false)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // Сброс и загрузка первой страницы при смене города.
  useEffect(() => {
    setPlaces([])
    setTotal(0)
    setOffset(0)
    setHasMore(true)
    void loadPage(citySlug, 0)
  }, [citySlug, loadPage])

  const loadMore = useCallback(() => {
    if (!loading && hasMore) void loadPage(citySlug, offset)
  }, [loading, hasMore, citySlug, offset, loadPage])

  const retry = useCallback(() => {
    void loadPage(citySlug, 0)
  }, [citySlug, loadPage])

  return { places, total, loading, error, hasMore, loadMore, retry }
}
