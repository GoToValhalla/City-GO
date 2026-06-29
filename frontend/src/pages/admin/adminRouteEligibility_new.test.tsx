/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminRouteEligibilityPage } from './AdminRouteEligibilityPage'
import { clearAdminSession } from './adminSession'

const cities = {
  items: [{ id: 1, slug: 'kemerovo', name: 'Кемерово', country: 'RU', region: null }],
  total: 1,
  limit: 100,
  offset: 0,
}

const eligibility = {
  items: [
    {
      place_id: 10,
      title: 'Краеведческий музей',
      slug: 'museum',
      category: 'museum',
      eligible: true,
      quality_score: 90,
      quality_bucket: 'high',
      reasons: [],
      primary_reason: 'selected',
      city_slug: 'kemerovo',
      placeholder_name: false,
      high_quality_route_candidate: true,
    },
    {
      place_id: 11,
      title: 'Культурное место OSM 15446625',
      slug: 'osm-culture',
      category: 'culture',
      eligible: false,
      quality_score: 70,
      quality_bucket: 'medium',
      reasons: ['placeholder_title'],
      primary_reason: 'placeholder_title',
      city_slug: 'kemerovo',
      placeholder_name: true,
      high_quality_route_candidate: false,
    },
  ],
  total: 125,
  limit: 50,
  offset: 0,
}

const diagnostics = {
  city_slug: 'kemerovo',
  city_name: 'Кемерово',
  places_total: 125,
  eligible_places: 80,
  published_places: 100,
  blockers_count_by_reason: { placeholder_title: 12, no_photo: 30 },
  near_ready_places: [],
  sample_blocked_places: [],
}

const jsonResponse = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }))
let failBulkApply = false
let failEligibilityList = false

const renderPage = () => render(
  <MemoryRouter initialEntries={['/admin/routes/eligibility?city_slug=kemerovo']}>
    <Routes>
      <Route path="/admin/routes/eligibility" element={<AdminRouteEligibilityPage />} />
    </Routes>
  </MemoryRouter>,
)

describe('AdminRouteEligibilityPage quality gates', () => {
  beforeEach(() => {
    failBulkApply = false
    failEligibilityList = false
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('confirm', vi.fn(() => true))
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/cities')) return jsonResponse(cities)
      if (url.includes('/admin/routes/eligibility/kemerovo')) return jsonResponse(diagnostics)
      if (url.includes('/admin/routes/eligibility?')) return failEligibilityList
        ? Promise.resolve(new Response(JSON.stringify({ detail: 'gateway failed' }), { status: 502, headers: { 'x-request-id': 'elig-502' } }))
        : jsonResponse(eligibility)
      if (url.includes('/admin/places/bulk/apply')) {
        return failBulkApply ? jsonResponse({ detail: 'bulk failed' }, 500) : jsonResponse({ affected_count: 1, warnings: [] })
      }
      return jsonResponse({})
    })
  })

  afterEach(() => {
    clearAdminSession()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    cleanup()
  })

  it('shows quality filters, pagination and placeholder flags', async () => {
    renderPage()

    await waitFor(() => expect(screen.getByText('Краеведческий музей')).toBeTruthy())

    expect(screen.getByLabelText('Готовность')).toBeTruthy()
    expect(screen.getByLabelText('Качество')).toBeTruthy()
    expect(screen.getByLabelText('Причина')).toBeTruthy()
    expect(screen.getByText('Показано: 1-2 из 125')).toBeTruthy()
    expect(screen.getByText('Страница 1 из 3')).toBeTruthy()
    expect(screen.getByText('можно массово подтвердить')).toBeTruthy()
    expect(screen.getByText('автоназвание, нужна проверка')).toBeTruthy()
  })

  it('high-quality preset sends quality gate query params', async () => {
    renderPage()

    await waitFor(() => expect(screen.getByText('Показать высокое качество')).toBeTruthy())
    fireEvent.click(screen.getByText('Показать высокое качество'))

    await waitFor(() => {
      const calls = (globalThis.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls
      const urls = calls.map((call) => String(call[0]))
      expect(urls.some((url) => url.includes('readiness=high_quality') && url.includes('quality=high') && url.includes('min_quality_score=75'))).toBe(true)
    })
  })

  it('next page requests the next offset', async () => {
    renderPage()

    await waitFor(() => expect(screen.getByText('Вперёд')).toBeTruthy())
    fireEvent.click(screen.getByText('Вперёд'))

    await waitFor(() => {
      const calls = (globalThis.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls
      const urls = calls.map((call) => String(call[0]))
      expect(urls.some((url) => url.includes('/admin/routes/eligibility?') && url.includes('offset=50'))).toBe(true)
    })
  })

  it('shows a visible error when bulk action fails', async () => {
    failBulkApply = true
    renderPage()

    await waitFor(() => expect(screen.getByText('Краеведческий музей')).toBeTruthy())
    fireEvent.click(screen.getByLabelText('Выбрать Краеведческий музей'))
    fireEvent.click(screen.getByRole('button', { name: 'Подтвердить для маршрутов' }))

    await waitFor(() => expect(screen.getByText(/bulk failed .*POST \/admin\/places\/bulk\/apply .*HTTP 500/)).toBeTruthy())
  })

  it('shows retryable section error when eligibility list returns 502', async () => {
    failEligibilityList = true
    renderPage()

    await waitFor(() => expect(screen.getByText('Готовность мест для маршрутов · Кемерово')).toBeTruthy())
    expect(screen.getByText(/gateway failed .*GET \/admin\/routes\/eligibility\?limit=50&offset=0&city_slug=kemerovo.*HTTP 502.*elig-502/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Повторить' })).toBeTruthy()
    expect(screen.queryByText(/^Загрузка…$/)).toBeNull()
  })
})
