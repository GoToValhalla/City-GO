/* @vitest-environment jsdom */
/**
 * tests/usePlacesPagination_new.test.ts
 *
 * Unit-тесты хука пагинации. Используем renderHook из @testing-library/react.
 */
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { usePlacesPagination } from './usePlacesPagination'

const mockPage = (items: object[], total: number, limit = 50, offset = 0) =>
  new Response(JSON.stringify({ items, total, limit, offset }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })

const fakePlace = (id: number) => ({
  id,
  slug: `place-${id}`,
  title: `Место ${id}`,
  category: 'museum',
  average_visit_duration_minutes: 30,
})

describe('usePlacesPagination_new', () => {
  afterEach(() => vi.restoreAllMocks())

  it('loads first page on mount', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockPage([fakePlace(1), fakePlace(2)], 2),
    )
    const { result } = renderHook(() => usePlacesPagination('zelenogradsk'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.places).toHaveLength(2)
    expect(result.current.total).toBe(2)
  })

  it('hasMore=false when all places loaded', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockPage([fakePlace(1)], 1),
    )
    const { result } = renderHook(() => usePlacesPagination('zelenogradsk'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.hasMore).toBe(false)
  })

  it('hasMore=true when more pages exist', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockPage(Array.from({ length: 50 }, (_, i) => fakePlace(i + 1)), 203),
    )
    const { result } = renderHook(() => usePlacesPagination('zelenogradsk'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.hasMore).toBe(true)
  })

  it('appends items on loadMore', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(mockPage([fakePlace(1)], 2, 50, 0))
      .mockResolvedValueOnce(mockPage([fakePlace(2)], 2, 50, 1))

    const { result } = renderHook(() => usePlacesPagination('zelenogradsk'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.places).toHaveLength(1)

    result.current.loadMore()
    await waitFor(() => expect(result.current.places).toHaveLength(2))
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
