/* @vitest-environment jsdom */
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminRouteDryRunPage } from './AdminRouteDryRunPage'
import { AdminRouteEligibilityPage } from './AdminRouteEligibilityPage'
import { adminGet, adminPost } from './adminApi'
import { clearAdminSession } from './adminSession'

vi.mock('./adminApi', () => ({
  adminGet: vi.fn(),
  adminPost: vi.fn(),
}))

const cities = { items: [{ id: 1, slug: 'test-city', name: 'Test', places_total: 10 }], total: 1, limit: 100, offset: 0 }

const dryRunResult = {
  request_summary: { city_slug: 'test-city' },
  generation_run_id: 42,
  selected_places: [{ place_id: 1, title: 'Museum', category: 'museum', is_eligible: true, selected: true, score: 0.9, rejection_reasons: [], selection_reasons: ['score'] }],
  rejected_candidates: [{ place_id: 2, title: 'Pharm', category: 'pharmacy', is_eligible: false, selected: false, score: null, rejection_reasons: ['forbidden_category:pharmacy'], selection_reasons: [] }],
  counts: { total_candidates: 2, eligible_candidates: 1, rejected_candidates: 1, selected_places: 1 },
  quality: { status: 'acceptable', score: 0.58, score_percent: 58, warnings: ['route_built_without_selected_interests'], breakdown: { completeness: 0.8 }, partial_reason: 'route_incomplete' },
}

const zeroCandidatesResult = {
  request_summary: { city_slug: 'test-city' },
  generation_run_id: 197,
  selected_places: [],
  rejected_candidates: [],
  counts: { total_candidates: 0, eligible_candidates: 0, rejected_candidates: 0, selected_places: 0 },
  quality: { status: 'failed', score: 0, score_percent: 0, warnings: ['route_failed_no_places'], breakdown: { completeness: 0 }, partial_reason: 'route_incomplete' },
}

const draftResult = {
  draft: { draft_id: 7, route_status: 'partial', total_minutes: 40, budget_minutes: 180, points: [{ id: 1, place_id: 1, position: 1, title: 'Museum', category: 'museum' }] },
  dry_run: dryRunResult,
}

const publishResult = {
  draft_id: 7,
  route: { id: 99, slug: 'test-city-route-7', title: 'Route', is_active: true },
  message: 'Маршрут опубликован',
}

const eligibilityResult = {
  items: [
    { place_id: 1, title: 'Museum', slug: 'museum', category: 'museum', eligible: false, quality_score: 80, quality_bucket: 'silver', reasons: ['route_eligible_false'], primary_reason: 'route_eligible_false', city_slug: 'test-city' },
    { place_id: 2, title: 'Cafe', slug: 'cafe', category: 'food', eligible: true, quality_score: 90, quality_bucket: 'gold', reasons: [], primary_reason: 'selected', city_slug: 'test-city' },
  ],
  total: 2,
  limit: 50,
  offset: 0,
}

const eligibilityDiagnostics = {
  city_slug: 'test-city',
  city_name: 'Test',
  places_total: 2,
  eligible_places: 1,
  published_places: 2,
  blockers_count_by_reason: { route_eligible_false: 1 },
  near_ready_places: [{ place_id: 1, title: 'Museum', slug: 'museum', category: 'museum', blockers: ['route_eligible_false'], quality_score: 80 }],
  sample_blocked_places: [{ place_id: 1, title: 'Museum', slug: 'museum', category: 'museum', blockers: ['route_eligible_false'], quality_score: 80 }],
}

const mockedAdminGet = vi.mocked(adminGet)
const mockedAdminPost = vi.mocked(adminPost)

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/admin/routes/dry-run']}>
      <Routes>
        <Route path="/admin/routes/dry-run" element={<AdminRouteDryRunPage />} />
        <Route path="/admin/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>,
  )

const renderEligibilityPage = () =>
  render(
    <MemoryRouter initialEntries={['/admin/routes/eligibility?city_slug=test-city']}>
      <Routes>
        <Route path="/admin/routes/eligibility" element={<AdminRouteEligibilityPage />} />
      </Routes>
    </MemoryRouter>,
  )

const selectedCityValue = () => (screen.getByLabelText('Город dry-run') as HTMLSelectElement).value
const runButtonDisabled = () => (screen.getByText('Проверить сборку') as HTMLButtonElement).disabled

describe('AdminRouteDryRunPage', () => {
  beforeEach(() => {
    mockedAdminGet.mockResolvedValue(cities)
    mockedAdminPost.mockImplementation((path: string) => {
      if (path === '/admin/routes/drafts/generate') return Promise.resolve(draftResult)
      if (path === '/admin/routes/drafts/7/publish') return Promise.resolve(publishResult)
      return Promise.resolve(dryRunResult)
    })
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.clearAllMocks()
  })

  it('renders form and submits dry run_new', async () => {
    renderPage()
    expect(screen.getByText('Маршруты → проверка сборки')).toBeTruthy()
    await waitFor(() => expect(selectedCityValue()).toBe('test-city'))
    fireEvent.click(screen.getByText('Проверить сборку'))
    await waitFor(() => expect(mockedAdminPost).toHaveBeenCalledWith('/admin/routes/dry-run', expect.objectContaining({ city_slug: 'test-city' })))
    await waitFor(() => expect(screen.getByText(/Проверка #42/)).toBeTruthy())
    expect(screen.getByText('Museum')).toBeTruthy()
    expect(screen.getByText('Pharm')).toBeTruthy()
    expect(screen.getByText('Выбрано в маршрут')).toBeTruthy()
    expect(screen.getByText('Не вошли в маршрут')).toBeTruthy()
    expect(screen.getByText(/Категория не подходит для маршрутов/)).toBeTruthy()
    expect(screen.getByText(/Маршрут собран без выбранных интересов/)).toBeTruthy()
  })

  it('explains empty route dry run_new', async () => {
    mockedAdminPost.mockResolvedValueOnce(zeroCandidatesResult)
    renderPage()
    await waitFor(() => expect(selectedCityValue()).toBe('test-city'))
    fireEvent.click(screen.getByText('Проверить сборку'))
    await waitFor(() => expect(screen.getByText('Маршрут не из чего собирать')).toBeTruthy())
    expect(screen.getByText('В этом городе сейчас нет мест, из которых можно собрать маршрут.')).toBeTruthy()
    expect(screen.getByText('Проверить готовность мест')).toBeTruthy()
    expect(screen.getByText('Открыть города')).toBeTruthy()
    expect(screen.queryByText('Выбрано в маршрут')).toBeNull()
    expect(screen.queryByText('Не вошли в маршрут')).toBeNull()
    expect(screen.queryByText(/Для мини-карты нет координат/)).toBeNull()
  })

  it('saves and publishes draft route_new', async () => {
    renderPage()
    await waitFor(() => expect(selectedCityValue()).toBe('test-city'))
    fireEvent.click(screen.getByText('Проверить сборку'))
    await waitFor(() => expect(screen.getByText(/Можно сохранить черновик/)).toBeTruthy())
    fireEvent.click(screen.getByText('Сохранить черновик'))
    await waitFor(() => expect(screen.getByText(/Черновик #7/)).toBeTruthy())
    fireEvent.click(screen.getByText('Опубликовать маршрут'))
    await waitFor(() => expect(screen.getByText(/Маршрут опубликован: #99/)).toBeTruthy())
  })

  it('selects first loaded city by default_new', async () => {
    renderPage()
    await waitFor(() => expect(selectedCityValue()).toBe('test-city'))
    expect(runButtonDisabled()).toBe(false)
  })
})

describe('AdminRouteEligibilityPage', () => {
  beforeEach(() => {
    mockedAdminGet.mockImplementation((path: string) => {
      if (path.startsWith('/admin/cities')) return Promise.resolve(cities)
      if (path.startsWith('/admin/routes/eligibility/test-city')) return Promise.resolve(eligibilityDiagnostics)
      if (path.startsWith('/admin/routes/eligibility?')) return Promise.resolve(eligibilityResult)
      return Promise.resolve({})
    })
    mockedAdminPost.mockResolvedValue({ ok: true })
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.clearAllMocks()
  })

  it('shows Russian route eligibility copy_new', async () => {
    renderEligibilityPage()
    await waitFor(() => expect(screen.getByText('Маршруты → готовность мест')).toBeTruthy())
    expect(screen.getByText('Готовность мест для маршрутов · Test')).toBeTruthy()
    expect(screen.getAllByText('Место не подтверждено для маршрутов.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('музей').length).toBeGreaterThan(0)
    expect(screen.getAllByText('нужно исправить').length).toBeGreaterThan(0)
    expect(screen.queryByText('route_eligible_false')).toBeNull()
    expect(screen.queryByText('Eligibility')).toBeNull()
  })

  it('selects visible places and confirms route eligibility in bulk_new', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderEligibilityPage()
    await waitFor(() => expect(screen.getByLabelText('Выбрать все видимые места')).toBeTruthy())
    fireEvent.click(screen.getByLabelText('Выбрать все видимые места'))
    await waitFor(() => expect(screen.getByText('Выбрано: 2')).toBeTruthy())
    fireEvent.click(screen.getByText('Подтвердить для маршрутов'))
    await waitFor(() => expect(mockedAdminPost).toHaveBeenCalledWith('/admin/places/bulk/apply', { place_ids: [1, 2], action: 'enable_route', params: {}, confirm: true }))
    expect(confirmSpy).toHaveBeenCalledWith('Подтвердить для маршрутов: 2 мест?')
    confirmSpy.mockRestore()
  })
})
