/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDiscoveryPage } from './AdminDiscoveryPage'

const mockSearch = vi.fn()
const mockDiscover = vi.fn()
const mockBulk = vi.fn()

vi.mock('./discoveryApi', () => ({
  searchDiscoveryRegions: (...args: unknown[]) => mockSearch(...args),
  discoverRegion: (...args: unknown[]) => mockDiscover(...args),
  bulkCreateDiscovery: (...args: unknown[]) => mockBulk(...args),
}))

vi.mock('./AdminDestinationGeoSearchPanel', () => ({
  AdminDestinationGeoSearchPanel: () => <div data-testid="destination-geo-search">city fallback</div>,
}))

const region = {
  id: 'test:RU-KGD',
  provider: 'deterministic',
  name: 'Калининградская область',
  english_name: 'Kaliningrad Oblast',
  country: 'Russia',
  type: 'region',
  center: { lat: 54.75, lon: 20.45 },
  matched_query: 'Калининградская область',
  warnings: [],
}

const candidate = {
  id: 'cand-1',
  external_id: 'zelenogradsk',
  name: 'Зеленоградск',
  english_name: 'Zelenogradsk',
  type: 'town',
  tier: 'high',
  confidence: { overall: 0.82, reasons: ['Тип: town'] },
  reasons: ['Тип: town'],
  warnings: [{ code: 'POI_SIGNAL_UNAVAILABLE', severity: 'info', message: 'POI недоступен' }],
  scope_overlaps: [],
  recommended_scopes: [{ code: 'city_core', name: 'Ядро', import_profile: 'tourist_core', reason: 'Базовый контур' }],
  existing_match: null,
}

describe('AdminDiscoveryPage', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('renders region-first tab by default', () => {
    render(<MemoryRouter><AdminDiscoveryPage /></MemoryRouter>)
    expect(screen.getByTestId('admin-discovery-page')).toBeInTheDocument()
    expect(screen.getByTestId('discovery-region-search')).toBeInTheDocument()
    expect(screen.getByText('Центр открытия направлений')).toBeInTheDocument()
  })

  it('searches Cyrillic region and starts discovery', async () => {
    mockSearch.mockResolvedValueOnce({ items: [region] })
    mockDiscover.mockResolvedValueOnce({
      job: { id: 'job-1', status: 'completed', progress_percent: 100 },
      preview: { region, total_candidates: 1, tiers: { top: 0, high: 1, medium: 0, low: 0, unknown: 0 }, warnings: [], candidates: [candidate] },
    })
    render(<MemoryRouter><AdminDiscoveryPage /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Регион / страна'), { target: { value: 'Калининградская область' } })
    fireEvent.click(screen.getByRole('button', { name: 'Найти регион' }))
    await waitFor(() => expect(mockSearch).toHaveBeenCalled())
    fireEvent.click(screen.getByRole('button', { name: 'Показать кандидаты' }))
    await waitFor(() => expect(screen.getByTestId('discovery-proposals')).toBeInTheDocument())
    expect(screen.getByTestId('discovery-tier')).toHaveTextContent('Высокий')
    expect(screen.getByText('POI_SIGNAL_UNAVAILABLE')).toBeInTheDocument()
  })

  it('bulk create confirmation keeps update scopes off by default', async () => {
    mockSearch.mockResolvedValueOnce({ items: [region] })
    mockDiscover.mockResolvedValueOnce({
      job: { id: 'job-1', status: 'completed', progress_percent: 100 },
      preview: { region, total_candidates: 1, tiers: { top: 0, high: 1, medium: 0, low: 0, unknown: 0 }, warnings: [], candidates: [candidate] },
    })
    mockBulk.mockResolvedValueOnce({ created: 1, skipped_existing: 0, conflicts: 0, errors: 0, items: [], warnings: [] })
    render(<MemoryRouter><AdminDiscoveryPage /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Регион / страна'), { target: { value: 'Калининградская область' } })
    fireEvent.click(screen.getByRole('button', { name: 'Найти регион' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Показать кандидаты' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Показать кандидаты' }))
    await waitFor(() => expect(screen.getByTestId('discovery-candidate-table')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Выбрать Зеленоградск'))
    fireEvent.click(screen.getByRole('button', { name: /Создать выбранные/ }))
    const confirm = screen.getByTestId('discovery-bulk-confirm')
    expect(within(confirm).getByLabelText(/Обновить существующие контуры/)).not.toBeChecked()
    fireEvent.click(within(confirm).getByRole('button', { name: 'Подтвердить создание' }))
    await waitFor(() => expect(mockBulk).toHaveBeenCalledWith('job-1', ['cand-1'], { update_existing_scopes: false }))
    await waitFor(() => expect(screen.getByTestId('discovery-result-summary')).toBeInTheDocument())
  })

  it('shows city geo-search fallback tab', () => {
    render(<MemoryRouter><AdminDiscoveryPage /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Поиск города' }))
    expect(screen.getByTestId('destination-geo-search')).toBeInTheDocument()
  })
})
