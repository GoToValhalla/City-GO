/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('renders heading and places count after loading', async () => {
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

    expect(
      screen.getByRole('heading', { name: /Найди куда сходить/ }),
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    expect(screen.getAllByText('Кофейня у моря').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Собрать маршрут/ })).toBeInTheDocument()
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

  it('does not crash when typing letters into hero search', async () => {
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

    const input = screen.getByPlaceholderText(/Кафе, музей/i)
    fireEvent.change(input, { target: { value: 'м' } })
    fireEvent.change(input, { target: { value: 'муз' } })

    expect(screen.getByRole('heading', { name: /Найди куда сходить/ })).toBeInTheDocument()
    expect(screen.getByText('Музей янтаря')).toBeInTheDocument()
  })
})
