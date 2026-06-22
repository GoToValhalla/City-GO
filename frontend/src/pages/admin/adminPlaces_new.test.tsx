/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminPlacesPage } from './AdminPlacesPage'
import { clearAdminSession } from './adminSession'

const page1 = Array.from({ length: 50 }, (_, i) => ({
  id: i + 1, slug: `p-${i}`, title: `Place ${i}`, category: 'cafe', address: 'a', city_id: 1,
  publication_status: 'published', is_published: true, is_visible_in_catalog: true,
  is_route_eligible: true, verification_status: 'unverified', source: 'osm', confidence: 0.5, status: 'active', short_description: null,
}))

const categories = [
  { code: 'service', label: 'Сервис', is_active: true, is_route_eligible: false, is_catalog_visible: true, is_default_enabled: true, is_observed: true, observed_count: 2, source: 'catalog+observed' },
  { code: 'park', label: 'Парк', is_active: true, is_route_eligible: true, is_catalog_visible: true, is_default_enabled: true, is_observed: true, observed_count: 1, source: 'catalog+observed' },
]

class MockIntersectionObserver {
  observe = vi.fn()
  disconnect = vi.fn()
  constructor() {}
}

const response = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }))
let fetchMock: ReturnType<typeof vi.fn>

describe('AdminPlacesPage', () => {
  beforeEach(() => {
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('confirm', vi.fn(() => true))
    fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/cities')) {
        return response({ items: [{ id: 1, slug: 'khanty', name: 'Ханты', country: 'RU', region: null }], total: 1, limit: 100, offset: 0 })
      }
      if (url.includes('/admin/taxonomy/categories')) {
        return response({ categories })
      }
      if (url.includes('/admin/places/bulk/preview')) {
        return response({ affected_count: 1, warnings: [] })
      }
      if (url.includes('/admin/places/bulk/apply')) {
        return response({ affected_count: 1, warnings: [] })
      }
      if (url.includes('/admin/places?')) {
        const u = new URL(url, 'http://localhost')
        const offset = Number(u.searchParams.get('offset') || 0)
        const items = offset === 0 ? page1 : [{ ...page1[0], id: 999, title: 'Place 999' }]
        return response({ items, total: 51, limit: 50, offset })
      }
      return response({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)
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

  it('requests category counters for the selected city_new', async () => {
    render(<MemoryRouter><AdminPlacesPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Места (51)')).toBeTruthy())

    fireEvent.change(screen.getByLabelText('Город'), { target: { value: 'khanty' } })

    await waitFor(() => {
      const calls = fetchMock.mock.calls.map(([url]) => String(url))
      expect(calls.some((url) => url.includes('/admin/taxonomy/categories?city_slug=khanty'))).toBe(true)
    })
  })

  it('applies route eligibility filter to places query_new', async () => {
    render(<MemoryRouter><AdminPlacesPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Места (51)')).toBeTruthy())

    fireEvent.change(screen.getByLabelText('Фильтр маршрутов'), { target: { value: 'true' } })

    await waitFor(() => {
      const calls = fetchMock.mock.calls.map(([url]) => String(url))
      expect(calls.some((url) => url.includes('/admin/places?') && url.includes('route_eligible=true'))).toBe(true)
    })
  })

  it('bulk changes selected places category_new', async () => {
    render(<MemoryRouter><AdminPlacesPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Места (51)')).toBeTruthy())
    await waitFor(() => expect(screen.getAllByText('Парк (park) · 1').length).toBeGreaterThan(0))

    fireEvent.click(screen.getByLabelText('Выбрать Place 0'))
    fireEvent.change(screen.getByLabelText('Новая категория'), { target: { value: 'park' } })
    fireEvent.click(screen.getByRole('button', { name: 'Сменить категорию' }))

    await waitFor(() => {
      const apply = fetchMock.mock.calls.find(([url]) => String(url).includes('/admin/places/bulk/apply'))
      expect(apply).toBeTruthy()
      const body = JSON.parse(String((apply?.[1] as RequestInit).body))
      expect(body).toMatchObject({ place_ids: [1], action: 'set_category', params: { category: 'park' }, confirm: true })
    })
  })
})
