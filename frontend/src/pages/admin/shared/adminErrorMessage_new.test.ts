import { describe, expect, it } from 'vitest'
import { toAdminErrorMessage } from './adminErrorMessage'

describe('toAdminErrorMessage', () => {
  it('maps nginx html to human message', () => {
    const msg = toAdminErrorMessage(502, '<html><head><title>502 Bad Gateway</title></head></html>')
    expect(msg).toContain('недоступен')
  })

  it('parses json detail', () => {
    const msg = toAdminErrorMessage(422, '{"detail":"city_slug required"}')
    expect(msg).toBe('city_slug required')
  })
})
