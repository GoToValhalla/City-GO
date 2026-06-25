import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MapPoint } from './mapTypes'
import { loadWalkingRoute } from './walkingRoute.api'

const points: MapPoint[] = [
  { id: 1, latitude: 46.35, longitude: 48.04, title: 'Старт' },
  { id: 2, latitude: 46.354, longitude: 48.045, title: 'Финиш' },
]

describe('Пешеходная геометрия маршрута', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('использует геометрию улиц и пошаговые инструкции backend', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'routed', provider: 'osrm-foot',
        geometry: [[48.04, 46.35], [48.041, 46.352], [48.045, 46.354]],
        distance_meters: 740, duration_seconds: 560,
        legs: [{ from_index: 0, to_index: 1, distance_meters: 740, duration_seconds: 560, steps: [
          { instruction: 'Поверните направо', street_name: null, distance_meters: 200, duration_seconds: 120 },
        ] }],
        warning: null,
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await loadWalkingRoute(points, new AbortController().signal)

    expect(result.status).toBe('routed')
    expect(result.geometry).toHaveLength(3)
    expect(result.geometry[1]).toEqual([48.041, 46.352])
    expect(result.legs[0].steps[0].instruction).toBe('Поверните направо')
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/routes/walking-geometry'), expect.objectContaining({ method: 'POST' }))
  })

  it('не создаёт прямую линию, когда pedestrian router недоступен', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'unavailable', provider: 'osrm-foot', geometry: [], legs: [], warning: 'Роутер недоступен' }),
    }))

    const result = await loadWalkingRoute(points, new AbortController().signal)

    expect(result.status).toBe('unavailable')
    expect(result.geometry).toEqual([])
    expect(result.warning).toBe('Роутер недоступен')
  })
})
