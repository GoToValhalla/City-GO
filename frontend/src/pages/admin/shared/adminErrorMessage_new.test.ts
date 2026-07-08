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

  it('renders a structured duplicate-active-job 409 detail with job_id, not a raw JSON dump', () => {
    const raw = JSON.stringify({
      detail: {
        result: 'blocked',
        reason: 'duplicate_active_job',
        message: 'Pipeline уже выполняется',
        job_id: 5,
        job_status: 'running',
        source: 'admin_photo_enrichment',
      },
    })
    const msg = toAdminErrorMessage(409, raw)
    expect(msg).toBe('Pipeline уже выполняется (job_id: 5)')
    expect(msg).not.toContain('{"detail"')
  })

  it('falls back to the reason field when message is absent from a structured detail', () => {
    const raw = JSON.stringify({ detail: { reason: 'duplicate_active_job', job_id: 9 } })
    const msg = toAdminErrorMessage(409, raw)
    expect(msg).toBe('duplicate_active_job (job_id: 9)')
  })
})
