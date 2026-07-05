/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LegacyCityRedirect } from './LegacyCityRedirect'
import { setCurrentCity } from '../../shared/city/currentCity'

describe('LegacyCityRedirect state transitions', () => {
  afterEach(() => {
    cleanup()
    setCurrentCity({ slug: 'zelenogradsk', name: 'Зеленоградск', country: 'Россия' })
  })

  it('redirects legacy /places to city catalog', async () => {
    setCurrentCity({ slug: 'kutaisi', name: 'Кутаиси', country: 'Грузия' })
    render(
      <MemoryRouter initialEntries={['/places']}>
        <Routes>
          <Route path="/places" element={<LegacyCityRedirect target="catalog" />} />
          <Route path="/kutaisi/catalog" element={<div>Каталог Кутаиси</div>} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('Каталог Кутаиси')).toBeInTheDocument())
  })

  it('redirects legacy /routes/generate to routes build', async () => {
    render(
      <MemoryRouter initialEntries={['/routes/generate']}>
        <Routes>
          <Route path="/routes/generate" element={<LegacyCityRedirect target="routes-build" />} />
          <Route path="/zelenogradsk/routes/build" element={<div>Сборка маршрута</div>} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('Сборка маршрута')).toBeInTheDocument())
  })
})
