/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { RandomRouteDraftEditor } from './RandomRouteDraftEditor'

vi.mock('../../shared/map/MapLibreMap', () => ({
  MapLibreMap: ({ points, routeLine }: { points: unknown[]; routeLine?: boolean }) => (
    <div data-testid="random-route-map" data-points={points.length} data-route-line={String(Boolean(routeLine))} />
  ),
}))

const draft = {
  draft_id: 10,
  version: 1,
  route_status: 'partial',
  total_minutes: 80,
  budget_minutes: 120,
  category_mode: 'balanced',
  selected_category_slugs: ['cafe'],
  warnings: [{ code: 'RANDOM_FALLBACK_USED', message: 'Частичный маршрут' }],
  category_summary: { requested: ['cafe'], matched: { cafe: 1 }, neutral_added: 1, missing: [] },
  points: [
    { id: 1, place_id: 101, position: 1, title: 'Кофейня', slug: 'coffee', category: 'cafe', lat: 1, lng: 2, visit_minutes: 25, open_status: 'unknown', user_locked: false, inserted_by_user: false, replacement_of_place_id: null, walk_minutes_from_prev: null, walk_minutes_to_next: 5 },
    { id: 2, place_id: 102, position: 2, title: 'Парк', slug: 'park', category: 'park', lat: 1.1, lng: 2.1, visit_minutes: 30, open_status: 'unknown', user_locked: false, inserted_by_user: false, replacement_of_place_id: null, walk_minutes_from_prev: 5, walk_minutes_to_next: null },
  ],
}

describe('RandomRouteDraftEditor', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/categories/')) return json([{ code: 'cafe', name: 'Кофе' }])
      if (url.includes('/routes/random')) return json(draft)
      if (url.includes('/search-places')) return json({ items: [{ place_id: 999, title: 'Новая кофейня', category: 'cafe', address: null, fit_reason: 'category_match', estimated_extra_minutes: 0, score: 3 }] })
      if (url.includes('/remove-point')) return json({ ...draft, version: 2, points: [draft.points[1]] })
      if (url.includes('/add-point') || url.includes('/replace-point')) return json({ ...draft, version: 3 })
      return json({}, 404)
    }))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('builds random places without category filters and keeps draft editing', async () => {
    render(<MemoryRouter><RandomRouteDraftEditor citySlug="zelenogradsk" /></MemoryRouter>)
    fireEvent.click(screen.getByText('Собрать случайные места'))
    await waitFor(() => expect(screen.getByText(/Маршрут собран частично/)).toBeTruthy())
    const randomCall = vi.mocked(fetch).mock.calls.find(([input]) => String(input).includes('/routes/random'))
    const payload = JSON.parse(String((randomCall?.[1] as RequestInit | undefined)?.body))
    expect(payload).toMatchObject({ city_slug: 'zelenogradsk', budget_minutes: 120, category_mode: 'none', selected_category_slugs: [] })
    expect(payload.seed).toEqual(expect.any(Number))
    expect(screen.getByTestId('random-route-map')).toHaveAttribute('data-points', '2')
    expect(screen.getByTestId('random-route-map')).toHaveAttribute('data-route-line', 'true')
    expect(screen.queryByRole('textbox')).toBeNull()
    expect(screen.getByRole('button', { name: /Показать места/ })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Категория места'), { target: { value: 'cafe' } })
    fireEvent.click(screen.getByRole('button', { name: /Показать места/ }))
    await waitFor(() => expect(screen.getByText('Новая кофейня')).toBeTruthy())
    expect(screen.queryByText(/category_match|name_or_quality_match/)).toBeFalsy()
  })

  it('builds random mood with real categories and a randomized supported duration', async () => {
    render(<MemoryRouter><RandomRouteDraftEditor citySlug="zelenogradsk" /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: /Случайное настроение/ }))
    await waitFor(() => expect(screen.getByText(/1 доступных категорий/)).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Удивить меня' }))
    await waitFor(() => expect(screen.getByText(/Маршрут собран частично/)).toBeTruthy())
    const randomCalls = vi.mocked(fetch).mock.calls.filter(([input]) => String(input).includes('/routes/random'))
    const payload = JSON.parse(String((randomCalls.at(-1)?.[1] as RequestInit | undefined)?.body))
    expect(payload.category_mode).toBe('balanced')
    expect(payload.selected_category_slugs).toEqual(['cafe'])
    expect([60, 120, 180, 240]).toContain(payload.budget_minutes)
  })
})

const json = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }))
