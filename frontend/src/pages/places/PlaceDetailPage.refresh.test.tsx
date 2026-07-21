/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PlaceDetailPage } from './PlaceDetailPage'

const mockGet = vi.fn()

vi.mock('../../api/places/places.api', () => ({
  getPlaceBySlug: (...args: unknown[]) => mockGet(...args),
}))
vi.mock('../../components/ui/AppHeader', () => ({ AppHeader: () => <header /> }))

const place = { id: 1, slug: 'museum', title: 'Музей', category: 'museum', address: 'ул. 1', short_description: 'Описание' }

describe('PlaceDetailPage refresh', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('renders skeleton and refreshes open detail every 45 seconds', async () => {
    vi.useFakeTimers()
    mockGet.mockResolvedValue(place)
    const { container } = render(<MemoryRouter initialEntries={['/places/museum']}><Routes><Route path="/places/:slug" element={<PlaceDetailPage />} /></Routes></MemoryRouter>)

    // Skeletons are decorative and intentionally aria-hidden (Stage 4.2:
    // "keep skeletons presentation-only") -- they are not meant to be
    // individually announced to screen readers, so they are asserted by
    // structure rather than by accessible name/label.
    expect(container.querySelectorAll('.place-detail-loading [aria-hidden="true"]')).toHaveLength(2)
    await act(async () => { await Promise.resolve() })
    expect(screen.getByRole('heading', { name: 'Музей' })).toBeInTheDocument()

    await act(async () => { vi.advanceTimersByTime(45_000); await Promise.resolve() })
    expect(mockGet).toHaveBeenCalledTimes(2)
  })
})
