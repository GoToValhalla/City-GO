/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminPlaceDetailPage } from './AdminPlaceDetailPage'

const mockGet = vi.fn()
const mockPatch = vi.fn()
const mockPost = vi.fn()

vi.mock('./adminApi', () => ({
  adminGet: (...args: unknown[]) => mockGet(...args),
  adminPatch: (...args: unknown[]) => mockPatch(...args),
  adminPost: (...args: unknown[]) => mockPost(...args),
}))

const detail = {
  id: 7,
  slug: 'museum-place', title: 'Музей места', city_id: 1, city_slug: 'zelenogradsk', city_name: 'Зеленоградск',
  category: 'museum', canonical_category: 'museum', address: 'Улица 1', address_source: null, address_confidence: null,
  address_updated_at: null, lat: 54.9, lng: 20.4, short_description: 'Описание', image_url: null,
  source: 'admin_manual', source_url: null, website: null, phone: null, atmosphere: null, inside: null, best_for: null,
  opening_hours: null, average_visit_duration_minutes: 30, price_level: null, indoor: true, outdoor: false,
  dog_friendly: false, family_friendly: false, is_active: true, status: 'active', lifecycle_status: 'active',
  quality_tier: 'silver', quality_score: 70, completeness_score: 30, photo_score: 20, description_score: 10,
  confidence_score: 80, freshness_score: 9, publication_status: 'published', verification_status: 'verified',
  visible_to_users: true, searchable: true, route_enabled: true, route_exclusion_reason: null,
  existence_confidence_level: 'high', existence_confidence_score: 90, admin_comment: null,
  route_usage_count: 0, route_usage_note: null, tags: [], audit_history: [],
}

const renderPage = () => render(
  <MemoryRouter initialEntries={['/admin/places/7']}>
    <Routes><Route path="/admin/places/:id" element={<AdminPlaceDetailPage />} /></Routes>
  </MemoryRouter>,
)

describe('AdminPlaceDetailPage emergency hide', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('requires confirmation and calls emergency hide endpoint', async () => {
    mockGet.mockResolvedValue(detail)
    mockPost.mockResolvedValueOnce({ publication_status: 'hidden' })
    renderPage()

    await waitFor(() => expect(screen.getByText('Экстренное скрытие')).toBeInTheDocument())
    const button = screen.getByRole('button', { name: /Экстренно скрыть место/i })
    expect(button).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Причина скрытия'), {
      target: { value: 'Подтверждена жалоба на закрытую локацию' },
    })
    fireEvent.click(screen.getByLabelText('Подтверждаю экстренное скрытие места'))
    fireEvent.click(button)

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/admin/places/7/emergency-hide', expect.objectContaining({
      reason: 'Подтверждена жалоба на закрытую локацию',
    })))
    expect(await screen.findByText(/Место экстренно скрыто/i)).toBeInTheDocument()
  })
})
