/* @vitest-environment jsdom */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminRouteEligibilityPage } from './AdminRouteEligibilityPage'
import { adminGet, adminPost } from './adminApi'
import { clearAdminSession } from './adminSession'

vi.mock('./adminApi', () => ({ adminGet: vi.fn(), adminPost: vi.fn() }))

const mockedAdminGet = vi.mocked(adminGet)

describe('AdminRouteEligibilityPage diagnostics', () => {
  beforeEach(() => {
    mockedAdminGet.mockImplementation((path: string) => {
      if (path.startsWith('/admin/cities')) return Promise.resolve({ items: [{ id: 1, slug: 'test-city', name: 'Test City' }], total: 1, limit: 100, offset: 0 })
      if (path === '/admin/routes/eligibility/test-city') return Promise.resolve(report)
      if (path.startsWith('/admin/routes/eligibility?')) return Promise.resolve({ items: [], total: 0, limit: 50, offset: 0 })
      return Promise.resolve({})
    })
    vi.mocked(adminPost).mockResolvedValue({})
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.clearAllMocks()
  })

  it('admin page renders eligibility summary_new', async () => {
    render(<MemoryRouter initialEntries={['/admin/routes/eligibility?city_slug=test-city']}><AdminRouteEligibilityPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText(/Route Readiness Diagnostics/)).toBeTruthy())
    expect(screen.getByText('Test City')).toBeTruthy()
    expect(screen.getAllByText('Eligible').length).toBeGreaterThan(0)
    expect(screen.getAllByText('no_photo').length).toBeGreaterThan(0)
    expect(screen.getByText('Near-ready Cafe')).toBeTruthy()
  })
})

const report = {
  city_slug: 'test-city',
  city_name: 'Test City',
  places_total: 3,
  eligible_places: 1,
  published_places: 2,
  blockers_count_by_reason: { no_photo: 1, no_address: 0, hidden_category: 0, draft_or_unpublished: 1, inactive: 0, low_quality: 0, missing_coordinates: 0 },
  near_ready_places: [{ place_id: 2, title: 'Near-ready Cafe', slug: 'near', category: 'cafe', blockers: ['no_photo'], quality_score: 80 }],
  sample_blocked_places: [{ place_id: 3, title: 'Draft Place', slug: 'draft', category: 'park', blockers: ['draft_or_unpublished'], quality_score: 80 }],
}
