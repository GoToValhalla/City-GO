/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PlacesListPage } from './PlacesListPage'

vi.mock('../../api/places/places.api', () => ({
  getPlacesByCityResponse: vi.fn().mockResolvedValue({
    total: 3,
    limit: 50,
    offset: 0,
    items: [
      { id: 1, slug: 'muzej', title: 'Музей', short_description: 'История', category: 'museum', address: 'ул. 1', lat: 54.96, lng: 20.48 },
      { id: 2, slug: 'kafe', title: 'Кафе', short_description: 'Кофе', category: 'cafe', address: 'ул. 2', lat: 54.95, lng: 20.47 },
      { id: 3, slug: 'park', title: 'Парк', short_description: null, category: 'park', address: 'ул. 3', lat: 54.94, lng: 20.46 },
    ],
  }),
}))

vi.mock('../../components/ui/AppHeader', () => ({
  AppHeader: () => <header data-testid="app-header" />,
}))

vi.mock('../../shared/map/MapLibreMap', () => ({
  MapLibreMap: () => <div data-testid="map-placeholder">Карта</div>,
}))

vi.mock('../../features/places-list/PlacesLoadMoreTrigger', () => ({
  PlacesLoadMoreTrigger: () => null,
}))

vi.mock('../../shared/location/useLocationProvider', () => ({
  useLocationProvider: () => ({
    status: 'idle',
    message: '',
    snapshot: null,
    request: vi.fn(),
    useManualPoint: vi.fn(),
  }),
}))

vi.mock('../../shared/city/currentCity', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../shared/city/currentCity')>()
  return {
    ...actual,
    getCurrentCity: vi.fn(() => actual.DEFAULT_CITY),
  }
})

describe('PlacesListPage search regression', () => {
  afterEach(() => {
    cleanup()
  })

  it('does not white-screen when typing letters into search', async () => {
    render(
      <MemoryRouter>
        <PlacesListPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('Музей').length).toBeGreaterThan(0))

    const input = screen.getByPlaceholderText(/Поиск мест в городе/i)
    fireEvent.change(input, { target: { value: 'м' } })
    fireEvent.change(input, { target: { value: 'муз' } })

    await waitFor(() => expect(screen.getAllByText('Музей').length).toBeGreaterThan(0))
    expect(screen.getByTestId('app-header')).toBeInTheDocument()
    expect(screen.queryByText(/undefined|null|object Object/i)).not.toBeInTheDocument()
  })

  it('shows empty state message for unmatched search', async () => {
    render(
      <MemoryRouter>
        <PlacesListPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('Музей').length).toBeGreaterThan(0))
    const input = screen.getByPlaceholderText(/Поиск мест в городе/i)
    fireEvent.change(input, { target: { value: 'zzz-no-match' } })

    await waitFor(() => expect(screen.getByText('Ничего не найдено')).toBeInTheDocument(), { timeout: 3000 })
  })
})
