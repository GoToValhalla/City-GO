/* @vitest-environment jsdom */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminPlacesPage } from './AdminPlacesPage'
import { clearAdminSession } from './adminSession'

const page1 = Array.from({ length: 50 }, (_, i) => ({
  id: i + 1, slug: `p-${i}`, title: `Place ${i}`, category: 'cafe', address: 'a', city_id: 1,
  publication_status: 'published', is_published: true, is_visible_in_catalog: true,
  is_route_eligible: true, verification_status: 'unverified', source: 'osm', confidence: 0.5, status: 'active', short_description: null,
}))

class MockIntersectionObserver {
  observe = vi.fn()
  disconnect = vi.fn()
  constructor(_cb: IntersectionObserverCallback, _opts?: IntersectionObserverInit) {}
}

describe('AdminPlacesPage', () => {
  beforeEach(() => {
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    let offset = 0
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/cities')) {
        return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0, limit: 100, offset: 0 }), { status: 200 }))
      }
      if (url.includes('/admin/places?')) {
        const u = new URL(url, 'http://localhost')
        offset = Number(u.searchParams.get('offset') || 0)
        const items = offset === 0 ? page1 : [{ ...page1[0], id: 999, title: 'Place 999' }]
        return Promise.resolve(new Response(JSON.stringify({ items, total: 51, limit: 50, offset }), { status: 200 }))
      }
      return Promise.resolve(new Response('{}', { status: 404 }))
    }))
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('shows pagination hint and total_new', async () => {
    render(<MemoryRouter><AdminPlacesPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Места (51)')).toBeTruthy())
    expect(screen.getByText('Показано 50 из 51')).toBeTruthy()
  })
})
