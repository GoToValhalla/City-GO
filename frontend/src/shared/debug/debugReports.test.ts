/* @vitest-environment jsdom */
import { beforeEach, describe, expect, it } from 'vitest'
import { buildDebugReportPayload, diagnosticsSummary } from './debugReports'

describe('debug report payload', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/routes/generate?debug=1')
  })

  it('redacts secrets and keeps useful diagnostics_new', () => {
    const payload = buildDebugReportPayload({
      screen: 'route',
      city_slug: 'zelenogradsk',
      request_id: 'req-1',
      request_payload: {
        Authorization: 'Bearer super-secret',
        nested: { token: 'abc' },
      },
      summary: 'route collapsed',
    })

    expect(payload.url).toContain('/routes/generate?debug=1')
    expect(payload.request_payload?.Authorization).toBe('[REDACTED]')
    expect((payload.request_payload?.nested as { token: string }).token).toBe('[REDACTED]')
    expect(payload.browser?.user_agent).toBeTruthy()
  })

  it('creates a compact copy summary_new', () => {
    const summary = diagnosticsSummary({
      screen: 'open_now',
      city_slug: 'zelenogradsk',
      request_id: 'req-2',
      severity: 'warning',
      warnings: ['empty'],
      summary: 'no open places',
    })

    expect(summary).toContain('Screen: open_now')
    expect(summary).toContain('Warnings: 1')
    expect(summary).toContain('no open places')
  })
})
