/* @vitest-environment jsdom */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminOverviewPage } from './AdminOverviewPage'
import { clearAdminSession } from './adminSession'

const forbiddenTerms = [
  'published/catalog',
  'route policy',
  'canonical category',
  'taxonomy',
  'enrichment/policy',
  'verification backlog',
  'critical confidence',
  'is_route_eligible',
]

const apiResponse = {
  critical: [],
  operations: [],
  recent_audit_count: 0,
  data_quality: [
    {
      code: 'route_blockers',
      title: 'Проблемы маршрутов',
      count: 12,
      severity: 'yellow',
      link_path: '/admin/places?preset=route_blockers',
      hint: 'Published/catalog places, которые не проходят route policy.',
      action_label: 'Открыть проблемы',
      queue_type: 'route_blocker',
      primary_action: 'open_queue',
      short_hint: 'Эти места сейчас не попадут в маршруты.',
      sample_endpoint: '/admin/places/search?preset=route_blockers',
      owner: 'data',
      is_human_actionable: true,
      mobile_priority: 'high',
    },
  ],
}

const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

describe('AdminOverviewPage product contract', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/overview')) return response(apiResponse)
      return response({})
    }))
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('renders operator cards without technical copy_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Проблемы маршрутов')).toBeTruthy())

    const text = document.body.textContent?.toLowerCase() ?? ''
    forbiddenTerms.forEach((term) => expect(text.includes(term)).toBe(false))
    expect(screen.getByText('Эти места сейчас не попадут в маршруты.')).toBeTruthy()
    expect(screen.queryByText(/Published\/catalog/i)).toBeNull()
  })

  it('card click applies expected filter_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByLabelText('Проблемы маршрутов: 12. Открыть проблемы')).toBeTruthy())

    expect(screen.getByLabelText('Проблемы маршрутов: 12. Открыть проблемы').getAttribute('href')).toBe('/admin/places?preset=route_blockers')
  })

  it('mobile overview cards use compact short hints_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    const hint = await screen.findByTestId('overview-card-hint-route_blockers')

    expect(hint.textContent).toBe('Эти места сейчас не попадут в маршруты.')
    expect((hint.textContent ?? '').length).toBeLessThanOrEqual(90)
  })
})
