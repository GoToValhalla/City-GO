/* @vitest-environment jsdom */
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminRouteDryRunPage } from './AdminRouteDryRunPage'
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
