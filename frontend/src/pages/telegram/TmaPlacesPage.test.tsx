/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as featuresApi from '../../api/features/publicFeatures.api'
import * as placesApi from '../../api/places/places.api'
import { TmaPlacesPage } from './TmaPlacesPage'

vi.mock('../../api/features/publicFeatures.api', () => ({ getPublicFeatures: vi.fn() }))
vi.mock('../../api/places/places.api', () => ({ getPlacesByCityResponse: vi.fn() }))

const renderPage = () => render(<MemoryRouter initialEntries={['/telegram/places']}><TmaPlacesPage /></MemoryRouter>)

describe('TmaPlacesPage', () => {
  afterEach(() => {
    cleanup()
    window.localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders published places once the toggle and places resolve_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    vi.mocked(placesApi.getPlacesByCityResponse).mockResolvedValue({
      items: [{ id: 1, slug: 'cafe-one', title: 'Cafe One', category: 'cafe', address: 'ул. Тестовая, 1' }] as never,
      total: 1,
      limit: 20,
      offset: 0,
    })

    renderPage()

    await waitFor(() => expect(screen.getByText('Cafe One')).toBeInTheDocument())
  })

  it('shows an empty state when the city has no published places_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    vi.mocked(placesApi.getPlacesByCityResponse).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 })

    renderPage()

    await waitFor(() => expect(screen.getByText('Мест пока нет')).toBeInTheDocument())
  })

  it('shows an error state when the places request fails_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    vi.mocked(placesApi.getPlacesByCityResponse).mockRejectedValue(new Error('network down'))

    renderPage()

    await waitFor(() => expect(screen.getAllByText('Не удалось загрузить места').length).toBeGreaterThan(0))
  })

  it('does not render the catalog when tma_enabled is false_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: false })
    vi.mocked(placesApi.getPlacesByCityResponse).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 })

    renderPage()

    await waitFor(() => expect(screen.getByText('Приложение временно недоступно')).toBeInTheDocument())
  })
})
