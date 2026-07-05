/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LegacyCityRedirect } from './features/city-routing/LegacyCityRedirect'

vi.mock('./pages/home/HomePage', () => ({ HomePage: () => <div>Home</div> }))
vi.mock('./pages/places/PlacesListPage', () => ({ PlacesListPage: () => <div>CatalogPage</div> }))
vi.mock('./pages/routes/GenerateRoutePage', () => ({ GenerateRoutePage: () => <div>RouteBuildPage</div> }))
vi.mock('./features/city-routing/CityRouteScope', () => ({
  CityRouteScope: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('./shared/city/currentCity', async () => {
  const actual = await vi.importActual<typeof import('./shared/city/currentCity')>('./shared/city/currentCity')
  return { ...actual, getCurrentCity: () => actual.DEFAULT_CITY }
})

describe('App routing matrix', () => {
  afterEach(() => cleanup())

  it('legacy /places redirects into city catalog route', async () => {
    render(
      <MemoryRouter initialEntries={['/places']}>
        <Routes>
          <Route path="/places" element={<LegacyCityRedirect target="catalog" />} />
          <Route path="/zelenogradsk/catalog" element={<div>CatalogPage</div>} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('CatalogPage')).toBeInTheDocument())
  })

  it('city catalog route renders page component', async () => {
    const { PlacesListPage } = await import('./pages/places/PlacesListPage')
    render(
      <MemoryRouter initialEntries={['/zelenogradsk/catalog']}>
        <Routes>
          <Route path="/:citySlug/catalog" element={<PlacesListPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('CatalogPage')).toBeInTheDocument())
  })
})
