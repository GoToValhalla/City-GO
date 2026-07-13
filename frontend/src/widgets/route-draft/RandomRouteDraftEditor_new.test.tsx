/* @vitest-environment jsdom */

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RandomRouteDraftEditor } from './RandomRouteDraftEditor'

vi.mock('../../api/routes/routeDraft.api', () => ({
  addDraftPoint: vi.fn(),
  createRandomDraft: vi.fn(),
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
