/* @vitest-environment jsdom */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminOverviewPage } from './AdminOverviewPage'
import { clearAdminSession } from './adminSession'

const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

describe('AdminOverviewPage CITYGO-171', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/overview')) {
        return response({
          critical: [],
          operations: [],
          recent_audit_count: 0,
          data_quality: [
            { code: 'not_route_eligible', title: 'Исключены из маршрутов', count: 7, severity: 'yellow', link_path: '/admin/places?preset=not_in_routes' },
            { code: 'route_unknown', title: 'Маршруты: нужно пересчитать', count: 3, severity: 'yellow', link_path: '/admin/places?preset=route_unknown' },
          ],
        })
      }
      return response({})
    }))
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('shows excluded and route unknown metrics with drill-down links_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Исключены из маршрутов')).toBeTruthy())

    expect(screen.getByText('7')).toBeTruthy()
    expect(screen.getByText('Маршруты: нужно пересчитать')).toBeTruthy()
    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.getByLabelText('Исключены из маршрутов: 7. Открыть выборку').getAttribute('href')).toBe('/admin/places?preset=not_in_routes')
    expect(screen.getByLabelText('Маршруты: нужно пересчитать: 3. Открыть выборку').getAttribute('href')).toBe('/admin/places?preset=route_unknown')
  })
})
