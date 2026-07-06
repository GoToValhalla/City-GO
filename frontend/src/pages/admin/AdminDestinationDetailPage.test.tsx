/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDestinationDetailPage } from './AdminDestinationDetailPage'

const mockGet = vi.fn()
const mockPost = vi.fn()
const mockPostLong = vi.fn()
const mockPatch = vi.fn()
const mockDelete = vi.fn()
vi.mock('./adminApi', () => ({
  adminDelete: (...args: unknown[]) => mockDelete(...args),
  adminGet: (...args: unknown[]) => mockGet(...args),
  adminPatch: (...args: unknown[]) => mockPatch(...args),
  adminPost: (...args: unknown[]) => mockPost(...args),
  adminPostLong: (...args: unknown[]) => mockPostLong(...args),
}))

describe('AdminDestinationDetailPage', () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.clearAllMocks() })

  const mockWorkspace = () => {
    mockGet.mockImplementation((path: string) => {
      if (path.includes('/memberships')) {
        return Promise.resolve([{ id: 1, place_id: 10, assignment_type: 'legacy_city', is_primary: true, is_hidden: false }])
      }
      if (path.includes('/orphans')) {
        return Promise.resolve([{ id: 99, slug: 'orphan', title: 'Без направления' }])
      }
      if (path.includes('/readiness')) {
        return Promise.resolve({
          bootstrap_ready: true,
          bootstrap_blockers: [],
          readiness_score: 72,
          places_total: 5,
          published_places: 4,
          route_eligible_places: 3,
          service_only_hidden: 1,
          pending_reviews: 1,
          address_coverage_pct: 80,
          photo_coverage_pct: 20,
          description_coverage_pct: 60,
          coordinates_coverage_pct: 100,
          opening_hours_coverage_pct: 40,
          degraded_sections: ['photo', 'opening_hours'],
        })
      }
      if (path.includes('/latest')) {
        return Promise.resolve({ run: { id: 7, status: 'succeeded', stage: 'completed', mode: 'full', counters: { candidates_found: 3, places_created: 2 } } })
      }
      if (path.includes('/data-pipeline/runs')) {
        return Promise.resolve({ items: [{ id: 7, status: 'succeeded', stage: 'completed', mode: 'full', counters: { candidates_found: 3, places_created: 2 } }] })
      }
      if (path.includes('/review-items')) {
        return Promise.resolve([{ id: 3, place_id: 10, place_name: 'Место с конфликтом', reason: 'VALUE_CONFLICT' }])
      }
      return Promise.resolve({
        slug: 'dest-city-a',
        title: 'Город А',
        destination_type: 'city',
        places_count: 5,
        scopes: [{ id: 1, code: 'default', name: 'Каталог', scope_type: 'catalog', import_strategy: 'single_bbox', import_profile: 'tourist_core', bbox: { south: 54.5, west: 20, north: 55, east: 21 }, enabled: true }],
      })
    })
  }

  const renderPage = () => render(
    <MemoryRouter initialEntries={['/admin/destinations/dest-city-a']}>
      <Routes>
        <Route path="/admin/destinations/:slug" element={<AdminDestinationDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )

  it('renders destination workspace metrics, reviews and public link in Russian', async () => {
    mockWorkspace()
    renderPage()
    await waitFor(() => expect(screen.getByTestId('admin-destination-detail')).toBeInTheDocument())
    expect(screen.getByText('Рабочее пространство данных')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText(/Успешно · Завершено/)).toBeInTheDocument()
    expect(screen.getByText('Контуры')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Открыть места направления' })).toHaveAttribute('href', '/admin/places?destination=dest-city-a')
    expect(screen.getByTestId('memberships-table')).toBeInTheDocument()
    expect(screen.getByTestId('orphans-table')).toBeInTheDocument()
    expect(screen.getByTestId('pipeline-history-table')).toBeInTheDocument()
    expect(screen.getByTestId('destination-reviews-table')).toBeInTheDocument()
    expect(screen.getByText('Без направления')).toBeInTheDocument()
    expect(screen.getByText('Значение отличается от текущего')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Открыть публичный каталог направления' })).toHaveAttribute('href', '/places?destination_slug=dest-city-a')
    expect(screen.queryByText('VALUE_CONFLICT')).not.toBeInTheDocument()
    expect(screen.queryByText('legacy_city')).not.toBeInTheDocument()
    expect(screen.queryByText('catalog')).not.toBeInTheDocument()
  })

  it('runs confirmed full collection and recalculation actions with loading state', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockWorkspace()
    mockPostLong.mockResolvedValue({ message: 'Прогон завершён' })
    mockPost.mockResolvedValue({ message: 'Принадлежность мест пересчитана' })
    renderPage()
    await waitFor(() => expect(screen.getByText('Собрать и обогатить места')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Собрать и обогатить места'))
    await waitFor(() => expect(mockPostLong).toHaveBeenCalledWith('/admin/destinations/dest-city-a/data-pipeline/run', { mode: 'full' }))
    fireEvent.click(screen.getByText('Пересчитать принадлежность мест'))
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/admin/destinations/dest-city-a/memberships/recalculate'))
    expect(screen.getByText('Принадлежность мест пересчитана')).toBeInTheDocument()
  })

  it('edits and deletes scope with bbox fields', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockWorkspace()
    mockPatch.mockResolvedValue({})
    mockDelete.mockResolvedValue({})
    renderPage()
    await waitFor(() => expect(screen.getByText('Править')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Править'))
    fireEvent.change(screen.getByLabelText('Север'), { target: { value: '55.2' } })
    fireEvent.click(screen.getByText('Сохранить контур'))
    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/admin/destinations/dest-city-a/scopes/1', expect.objectContaining({ bbox: expect.objectContaining({ north: 55.2 }) })))
    fireEvent.click(screen.getByText('Удалить'))
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/admin/destinations/dest-city-a/scopes/1'))
  })

  it('disables collection when bootstrap blockers are present', async () => {
    mockWorkspace()
    const baseGet = mockGet.getMockImplementation()
    mockGet.mockImplementation((path: string) => path.includes('/readiness')
      ? Promise.resolve({ bootstrap_ready: false, bootstrap_blockers: ['NO_SCOPES'], readiness_score: 0, places_total: 0, published_places: 0, route_eligible_places: 0, service_only_hidden: 0, pending_reviews: 0, address_coverage_pct: 0, photo_coverage_pct: 0, description_coverage_pct: 0, coordinates_coverage_pct: 0, opening_hours_coverage_pct: 0, degraded_sections: [] })
      : baseGet?.(path))
    renderPage()
    await waitFor(() => expect(screen.getByText(/нет контуров/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Собрать и обогатить места' })).toBeDisabled()
  })

  it('creates scope from geo candidate and reloads destination data', async () => {
    const candidate = {
      candidate_key: 'nominatim:relation:123',
      title: 'Куршская коса',
      display_name: 'Куршская коса, Калининградская область',
      lat: 55.12,
      lng: 20.85,
      bbox: { south: 54.8, west: 20.4, north: 55.4, east: 21.1 },
      destination_type: 'natural_region',
      import_strategy: 'single_bbox',
    }
    mockWorkspace()
    mockGet.mockImplementation((path: string) => {
      if (path.includes('/geo-search')) return Promise.resolve({ query: 'Куршская коса', items: [candidate] })
      if (path.includes('/memberships')) return Promise.resolve([{ id: 1, place_id: 10, assignment_type: 'legacy_city', is_primary: true, is_hidden: false }])
      if (path.includes('/orphans')) return Promise.resolve([])
      if (path.includes('/readiness')) return Promise.resolve({ bootstrap_ready: true, bootstrap_blockers: [], readiness_score: 72, places_total: 5, published_places: 4, route_eligible_places: 3, service_only_hidden: 1, pending_reviews: 1, address_coverage_pct: 80, photo_coverage_pct: 20, description_coverage_pct: 60, coordinates_coverage_pct: 100, opening_hours_coverage_pct: 40, degraded_sections: [] })
      if (path.includes('/latest')) return Promise.resolve({ run: { id: 7, status: 'succeeded', stage: 'completed', mode: 'full', counters: { candidates_found: 3, places_created: 2 } } })
      if (path.includes('/data-pipeline/runs')) return Promise.resolve({ items: [] })
      if (path.includes('/review-items')) return Promise.resolve([])
      return Promise.resolve({ slug: 'dest-city-a', title: 'Город А', destination_type: 'city', places_count: 5, scopes: [] })
    })
    mockPost.mockResolvedValueOnce({ action: 'created', scope: { id: 2, code: 'catalog-core' } })
    renderPage()
    await waitFor(() => expect(screen.getByText('Контуры')).toBeInTheDocument())
    const geoPanel = within(screen.getByTestId('destination-geo-search'))
    fireEvent.change(geoPanel.getByLabelText('Город или регион'), { target: { value: 'Куршская коса' } })
    fireEvent.click(geoPanel.getByRole('button', { name: 'Найти' }))
    await waitFor(() => expect(geoPanel.getByTestId('geo-candidate-list')).toBeInTheDocument())
    fireEvent.click(geoPanel.getByRole('button', { name: 'Добавить контур' }))
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/admin/destinations/dest-city-a/scopes/from-geo-candidate', expect.objectContaining({ recover: false, candidate: expect.objectContaining({ candidate_key: candidate.candidate_key }) })))
    await waitFor(() => expect(mockGet.mock.calls.filter(([path]) => String(path).includes('/admin/destinations/dest-city-a') && !String(path).includes('geo-search')).length).toBeGreaterThan(1))
  })
})
