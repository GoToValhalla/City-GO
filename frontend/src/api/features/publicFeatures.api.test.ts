import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPublicFeatures } from './publicFeatures.api'

describe('getPublicFeatures', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('returns the parsed feature flags_new', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ tma_enabled: true }) }))

    const result = await getPublicFeatures()

    expect(result).toEqual({ tma_enabled: true })
  })

  it('throws on a non-ok response_new', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))

    await expect(getPublicFeatures()).rejects.toThrow('HTTP 503')
  })
})
