/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as featuresApi from '../../api/features/publicFeatures.api'
import * as placesApi from '../../api/places/places.api'
import { DEFAULT_CITY, setCurrentCity } from '../../shared/city/currentCity'
import { TmaPlaceDetailPage } from './TmaPlaceDetailPage'
import { TmaRouteStartUnavailableError } from './tmaRouteActions'

vi.mock('../../api/features/publicFeatures.api', () => ({ getPublicFeatures: vi.fn() }))
vi.mock('../../api/places/places.api', () => ({ getPlaceBySlug: vi.fn() }))
vi.mock('./tmaRouteActions', async () => {
  const actual = await vi.importActual<typeof import('./tmaRouteActions')>('./tmaRouteActions')
  return { ...actual, addPlaceToTmaRoute: vi.fn() }
})

const place = { id: 1, slug: 'cafe-one', title: 'Cafe One', category: 'cafe' } as never

const renderPage = () => render(
  <MemoryRouter initialEntries={['/telegram/places/cafe-one']}>
    <Routes><Route path="/telegram/places/:slug" element={<TmaPlaceDetailPage />} /></Routes>
  </MemoryRouter>,
)

describe('TmaPlaceDetailPage', () => {
  afterEach(() => {
    cleanup()
    window.localStorage.clear()
    vi.clearAllMocks()
    setCurrentCity(DEFAULT_CITY)
  })

  it('shows the truthful start-unavailable message instead of a generic failure_new', async () => {
    const { addPlaceToTmaRoute } = await import('./tmaRouteActions')
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    vi.mocked(placesApi.getPlaceBySlug).mockResolvedValue(place)
    vi.mocked(addPlaceToTmaRoute).mockRejectedValue(new TmaRouteStartUnavailableError())

    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Добавить в маршрут' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Добавить в маршрут' }))

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Не удалось определить точку старта'))
  })

  it('shows a generic message for a non-start-related failure_new', async () => {
    const { addPlaceToTmaRoute } = await import('./tmaRouteActions')
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    vi.mocked(placesApi.getPlaceBySlug).mockResolvedValue(place)
    vi.mocked(addPlaceToTmaRoute).mockRejectedValue(new Error('network down'))

    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Добавить в маршрут' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Добавить в маршрут' }))

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Не удалось добавить место в маршрут.'))
  })

  it('confirms success when the route accepts the place_new', async () => {
    const { addPlaceToTmaRoute } = await import('./tmaRouteActions')
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    vi.mocked(placesApi.getPlaceBySlug).mockResolvedValue(place)
    vi.mocked(addPlaceToTmaRoute).mockResolvedValue({} as never)

    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Добавить в маршрут' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Добавить в маршрут' }))

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Место добавлено в маршрут.'))
  })
})
