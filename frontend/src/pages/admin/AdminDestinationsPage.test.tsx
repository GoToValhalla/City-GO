/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDestinationsPage } from './AdminDestinationsPage'

const mockGet = vi.fn()
vi.mock('./adminApi', () => ({ adminGet: (...args: unknown[]) => mockGet(...args) }))

describe('AdminDestinationsPage', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('renders destinations list in Russian', async () => {
    mockGet.mockResolvedValueOnce({
      items: [{ id: 1, slug: 'zelenogradsk', title: 'Зеленоградск', destination_type: 'city', places_count: 10 }],
    })
    render(<MemoryRouter><AdminDestinationsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Направления')).toBeInTheDocument())
    expect(screen.getByText('Зеленоградск')).toBeInTheDocument()
    expect(screen.queryByText('city')).not.toBeInTheDocument()
  })
})
