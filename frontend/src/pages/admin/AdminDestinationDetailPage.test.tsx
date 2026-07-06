/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDestinationDetailPage } from './AdminDestinationDetailPage'

const mockGet = vi.fn()
vi.mock('./adminApi', () => ({
  adminGet: (...args: unknown[]) => mockGet(...args),
  adminPost: vi.fn(),
}))

describe('AdminDestinationDetailPage', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('renders scopes, memberships and orphans in Russian', async () => {
    mockGet.mockImplementation((path: string) => {
      if (path.includes('/memberships')) {
        return Promise.resolve([{ id: 1, place_id: 10, assignment_type: 'legacy_city', is_primary: true, is_hidden: false }])
      }
      if (path.includes('/orphans')) {
        return Promise.resolve([{ id: 99, slug: 'orphan', title: 'Без направления' }])
      }
      return Promise.resolve({
        slug: 'dest-city-a',
        title: 'Город А',
        destination_type: 'city',
        places_count: 5,
        scopes: [{ id: 1, code: 'default', name: 'Каталог', scope_type: 'catalog', enabled: true }],
      })
    })
    render(
      <MemoryRouter initialEntries={['/admin/destinations/dest-city-a']}>
        <Routes>
          <Route path="/admin/destinations/:slug" element={<AdminDestinationDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByTestId('admin-destination-detail')).toBeInTheDocument())
    expect(screen.getByText('Контуры')).toBeInTheDocument()
    expect(screen.getByTestId('memberships-table')).toBeInTheDocument()
    expect(screen.getByTestId('orphans-table')).toBeInTheDocument()
    expect(screen.getByText('Без направления')).toBeInTheDocument()
  })
})
