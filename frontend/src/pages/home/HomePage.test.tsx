/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { HomePage } from './HomePage'
import { getPlacesByCityResponse } from '../../api/places/places.api'

vi.mock('../../api/places/places.api', () => ({
  getPlacesByCityResponse: vi.fn(),
}))

vi.mock('../../components/ui/AppHeader', () => ({
  AppHeader: () => <header data-testid="app-header" />,
}))

vi.mock('../../widgets/home/HomeCityMap', () => ({
  HomeCityMap: () => <div data-testid="home-city-map" />,
}))

vi.mock('../../shared/city/currentCity', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../shared/city/currentCity')>()
  return {
    ...actual,
    getCurrentCity: vi.fn(() => actual.DEFAULT_CITY),
    setCurrentCity: vi.fn(),
  }
})

const mockedGetPlacesByCityResponse = vi.mocked(getPlacesByCityResponse)

describe('HomePage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders the city hero, real places and random mood entry point', async () => {
    mockedGetPlacesByCityResponse.mockResolvedValueOnce({
      total: 2,
      limit: 20,
      offset: 0,
      items: [
      {
        id: 1,
        slug: 'mesto-1',
        title: 'Кофейня у моря',
        short_description: 'Вкусный кофе',
        category: 'cafe',
        address: 'ул. Морская, 1',
      },
      {
        id: 2,
        slug: 'mesto-2',
        title: 'Музей янтаря',
        short_description: null,
        category: 'museum',
        address: 'ул. Центральная, 5',
      },
      ],
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Зеленоградск', level: 1 })).toBeInTheDocument()
    expect(screen.getByTestId('home-city-map')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getAllByText(/2/).length).toBeGreaterThan(0)
    })

    expect(screen.getAllByText('Кофейня у моря').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Удивить меня/ })).toHaveAttribute('href', '/zelenogradsk/routes/build?mode=random_mood')
  })

  it('renders error state when places loading fails', async () => {
    mockedGetPlacesByCityResponse.mockRejectedValueOnce(new Error('network error'))

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Не удалось загрузить места')).toBeInTheDocument()
    })
  })

  it('shows only places returned by the current city API', async () => {
    mockedGetPlacesByCityResponse.mockResolvedValue({
      total: 2,
      limit: 20,
      offset: 0,
      items: [
        { id: 1, slug: 'mesto-1', title: 'Кофейня у моря', short_description: 'Вкусный кофе', category: 'cafe', address: 'ул. 1' },
        { id: 2, slug: 'mesto-2', title: 'Музей янтаря', short_description: null, category: 'museum', address: 'ул. 2' },
      ],
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Кофейня у моря')).toBeInTheDocument())

    expect(screen.getByRole('heading', { name: 'Зеленоградск', level: 1 })).toBeInTheDocument()
    expect(screen.getByText('Кофейня у моря')).toBeInTheDocument()
    expect(screen.getByText('Музей янтаря')).toBeInTheDocument()
  })
})
