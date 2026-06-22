/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RandomRouteDraftEditor } from './RandomRouteDraftEditor'

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
    { id: 2, place_id: 102, position: 2, title: 'Парк', slug: 'park', category: 'park', lat: 1, lng: 2, visit_minutes: 30, open_status: 'unknown', user_locked: false, inserted_by_user: false, replacement_of_place_id: null, walk_minutes_from_prev: 5, walk_minutes_to_next: null },
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

  it('builds balanced random draft and edits points_new', async () => {
    render(<RandomRouteDraftEditor citySlug="zelenogradsk" />)
    await waitFor(() => expect(screen.getByText('Кофе')).toBeTruthy())
    fireEvent.click(screen.getByText('Кофе'))
    fireEvent.click(screen.getByText('Случайный маршрут'))
    await waitFor(() => expect(screen.getByText(/partial/)).toBeTruthy())
    expect(JSON.parse(String((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[1][1]?.body)).category_mode).toBe('balanced')
    fireEvent.click(screen.getAllByText('Удалить')[0])
    await waitFor(() => expect(screen.queryByText('Кофейня')).toBeFalsy())
    await waitFor(() => expect((screen.getByText('Найти место') as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByText('Найти место'))
    await waitFor(() => expect(screen.getByText(/Новая кофейня/)).toBeTruthy())
  })
})

const json = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }))