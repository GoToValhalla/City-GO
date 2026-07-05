/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CityRouteScope } from './CityRouteScope'
import { getCurrentCity, setCurrentCity } from '../../shared/city/currentCity'

vi.mock('../../api/cities/cities.api', () => ({
  getAvailableCities: vi.fn().mockResolvedValue([
    { slug: 'zelenogradsk', name: 'Зеленоградск', country: 'Россия', launch_status: 'published' },
  ]),
}))

describe('CityRouteScope', () => {
  afterEach(() => {
    cleanup()
    setCurrentCity(getCurrentCity())
  })

  it('syncs city from URL slug', async () => {
    render(
      <MemoryRouter initialEntries={['/zelenogradsk/catalog']}>
        <Routes>
          <Route path="/:citySlug/catalog" element={<CityRouteScope><div>Каталог</div></CityRouteScope>} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Каталог')).toBeInTheDocument())
    expect(getCurrentCity().slug).toBe('zelenogradsk')
  })

  it('redirects reserved slug admin', async () => {
    render(
      <MemoryRouter initialEntries={['/admin/catalog']}>
        <Routes>
          <Route path="/" element={<div>Главная</div>} />
          <Route path="/:citySlug/catalog" element={<CityRouteScope><div>Каталог</div></CityRouteScope>} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Главная')).toBeInTheDocument())
  })
})
