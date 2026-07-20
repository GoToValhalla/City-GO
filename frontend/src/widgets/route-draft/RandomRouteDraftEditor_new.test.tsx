/* @vitest-environment jsdom */

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RandomRouteDraftEditor } from './RandomRouteDraftEditor'

vi.mock('../../api/routes/routeDraft.api', () => ({
  addDraftPoint: vi.fn(),
  createRandomDraft: vi.fn(async () => ({
    draft: { draft_id: 1, version: 1, route_status: 'partial', total_minutes: 60, budget_minutes: 120, category_mode: 'none', selected_category_slugs: [], points: [], warnings: [], category_summary: { requested: [], matched: {}, neutral_added: 0, missing: [] } },
    ownershipToken: 'test-draft-session-token',
  })),
  loadCategories: vi.fn(async () => [
    { code: 'coffee', name: 'Кофе' },
    { code: 'sea', name: 'Море' },
    { code: 'museum', name: 'Музеи' },
  ]),
  removeDraftPoint: vi.fn(),
  replaceDraftPoint: vi.fn(),
  searchDraftPlaces: vi.fn(),
}))

describe('RandomRouteDraftEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => cleanup())

  it('excludes sea from the random mood pool for cities without sea feature', async () => {
    render(<RandomRouteDraftEditor citySlug="khanty-mansiysk" features={[]} />)
    fireEvent.click(screen.getByRole('button', { name: /Случайное настроение/ }))
    await waitFor(() => expect(screen.getByText(/2 доступных категорий/)).toBeInTheDocument())
  })

  it('includes sea in the random mood pool for cities with sea feature', async () => {
    render(<RandomRouteDraftEditor citySlug="zelenogradsk" features={['sea']} />)
    fireEvent.click(screen.getByRole('button', { name: /Случайное настроение/ }))
    await waitFor(() => expect(screen.getByText(/3 доступных категорий/)).toBeInTheDocument())
  })
})
