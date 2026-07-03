/* @vitest-environment jsdom */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminOverviewPage } from './AdminOverviewPage'
import { clearAdminSession } from './adminSession'

const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
const backlogResponse = {
  generated_at: '2026-07-04T00:00:00Z',
  summary: {
    unique_problem_places: 0,
    total_problem_signals: 0,
    route_blocker_places: 0,
    auto_fixable_places: 0,
    manual_places: 0,
    verification_backlog_places: 0,
    content_gap_places: 0,
  },
  queues: [],
  overlaps: [],
}

describe('AdminOverviewPage CITYGO-171', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/overview/backlog-breakdown')) {
        return response(backlogResponse)
      }
      if (url.includes('/admin/overview')) {
        return response({
          critical: [],
          operations: [],
          recent_audit_count: 0,
          data_quality: [
            { code: 'not_route_eligible', title: 'Отключены вручную', count: 7, severity: 'yellow', link_path: '/admin/places?preset=published_not_route_eligible', action_label: 'Открыть отключённые', short_hint: 'Места, явно отключённые от маршрутов.' },
            { code: 'route_unknown', title: 'Неизвестные категории', count: 3, severity: 'yellow', link_path: '/admin/places?preset=route_unknown', action_label: 'Разобрать категории', short_hint: 'Нужно назначить понятную категорию.' },
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

    await waitFor(() => expect(screen.getByText('Отключены вручную')).toBeTruthy())

    expect(screen.getByText('7')).toBeTruthy()
    expect(screen.getByText('Неизвестные категории')).toBeTruthy()
    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.getByLabelText('Отключены вручную: 7. Открыть отключённые').getAttribute('href')).toBe('/admin/places?preset=published_not_route_eligible')
    expect(screen.getByLabelText('Неизвестные категории: 3. Разобрать категории').getAttribute('href')).toBe('/admin/places?preset=route_unknown')
  })
})
