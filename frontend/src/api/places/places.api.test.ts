import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPlacesByCity, getPlacesByCityResponse, getPlaceBySlug } from './places.api'

describe('places.api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns places when backend response is ok', async () => {
    const responseData = {
      items: [
        {
          id: 1,
          slug: 'mesto',
          title: 'Тестовое место',
          short_description: null,
          category: 'museum',
          address: 'Адрес 1',
          average_visit_duration_minutes: 45,
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(responseData), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getPlacesByCity('zelenogradsk')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/places/?city_slug=zelenogradsk',
    )
    expect(result[0].visit_minutes).toBe(45)
  })

  it('returns places response total from backend', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 215, limit: 20, offset: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getPlacesByCityResponse('khanty-mansiysk')

    expect(result.total).toBe(215)
    expect(result.limit).toBe(20)
  })

  it('throws error when response is not ok', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 500 }))

    await expect(getPlacesByCity('zelenogradsk')).rejects.toThrow('HTTP 500')
  })

  it('does not return demo places when backend is unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(getPlacesByCity('zelenogradsk')).rejects.toThrow('Failed to fetch')
  })

  it('loads place detail from backend only', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 10, slug: 'khanty-place', title: 'Место из БД' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getPlaceBySlug('khanty-place')

    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/places/by-slug/khanty-place')
    expect(result.title).toBe('Место из БД')
  })
})
