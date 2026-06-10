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
const runButtonDisabled = () => (screen.getByText('Запустить') as HTMLButtonElement).disabled

describe('AdminRouteDryRunPage', () => {
  beforeEach(() => {
    mockedAdminGet.mockResolvedValue(cities)
    mockedAdminPost.mockResolvedValue(dryRunResult)
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.clearAllMocks()
  })

  it('renders form and submits dry run_new', async () => {
    renderPage()
    expect(screen.getByText('Маршруты → Dry Run')).toBeTruthy()
    await waitFor(() => expect(selectedCityValue()).toBe('test-city'))
    fireEvent.click(screen.getByText('Запустить'))
    await waitFor(() => expect(mockedAdminPost).toHaveBeenCalledWith('/admin/routes/dry-run', expect.objectContaining({ city_slug: 'test-city' })))
    await waitFor(() => expect(screen.getByText(/Run #42/)).toBeTruthy())
    expect(screen.getByText('Museum')).toBeTruthy()
    expect(screen.getByText('Pharm')).toBeTruthy()
  })

  it('selects first loaded city by default_new', async () => {
    renderPage()
    await waitFor(() => expect(selectedCityValue()).toBe('test-city'))
    expect(runButtonDisabled()).toBe(false)
  })
})
