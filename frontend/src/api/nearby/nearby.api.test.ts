import { afterEach, describe, expect, it, vi } from 'vitest'
import { getNearbyPlaces } from './nearby.api'

describe('getNearbyPlaces', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('throws when backend is unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(getNearbyPlaces(54.96, 20.48, 1)).rejects.toThrow('Failed to fetch')
  })
})
