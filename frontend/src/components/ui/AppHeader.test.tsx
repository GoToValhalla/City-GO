/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getAvailableCities } from '../../api/cities/cities.api'
import { DEFAULT_CITY } from '../../shared/city/currentCity'
import { AppHeader } from './AppHeader'

vi.mock('../../api/cities/cities.api', () => ({ getAvailableCities: vi.fn() }))

const LocationProbe = () => <output data-testid="location">{useLocation().pathname}</output>

describe('AppHeader city picker', () => {
  afterEach(() => {
    cleanup()
    window.localStorage.clear()
    vi.clearAllMocks()
  })

  it('finds duplicate city names by region and opens the selected city route', async () => {
    vi.mocked(getAvailableCities).mockResolvedValue([
      DEFAULT_CITY,
      { slug: 'pushkin-spb', name: 'Пушкин', region: 'Санкт-Петербург', country: 'Россия', places_count: 8 },
      { slug: 'pushkin-saratov', name: 'Пушкин', region: 'Саратовская область', country: 'Россия', places_count: 4 },
    ])
    render(<MemoryRouter initialEntries={['/zelenogradsk']}><AppHeader /><LocationProbe /></MemoryRouter>)

    fireEvent.click(screen.getByRole('button', { name: /Зеленоградск/ }))
    const search = screen.getByPlaceholderText('Город, регион или страна')
    fireEvent.change(search, { target: { value: 'Саратов' } })
    const city = await screen.findByRole('button', { name: 'Выбрать Пушкин · Саратовская область · Россия' })
    expect(screen.queryByRole('button', { name: 'Выбрать Пушкин · Санкт-Петербург · Россия' })).not.toBeInTheDocument()
    fireEvent.click(city)

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/pushkin-saratov'))
    expect(JSON.parse(String(window.localStorage.getItem('citygo:selectedCity')))).toMatchObject({ slug: 'pushkin-saratov' })
  })
})

describe('AppHeader theme toggle', () => {
  afterEach(() => {
    cleanup()
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    vi.restoreAllMocks()
  })

  it('keeps desktop and mobile controls in sync via one shared state_new', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }),
    })
    render(<MemoryRouter initialEntries={['/zelenogradsk']}><AppHeader /></MemoryRouter>)

    const darkButtons = screen.getAllByRole('radio', { name: 'Тёмная' })
    expect(darkButtons).toHaveLength(2)
    darkButtons.forEach((button) => expect(button).toHaveAttribute('aria-checked', 'false'))

    fireEvent.click(darkButtons[0])

    screen.getAllByRole('radio', { name: 'Тёмная' }).forEach((button) => expect(button).toHaveAttribute('aria-checked', 'true'))
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(window.localStorage.getItem('citygo:themeMode')).toBe('dark')
  })
})
