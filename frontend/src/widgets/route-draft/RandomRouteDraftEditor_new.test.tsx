import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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

  it('hides sea chip for cities without sea feature', async () => {
    render(<RandomRouteDraftEditor citySlug="khanty-mansiysk" features={[]} />)

    await waitFor(() => expect(screen.getByRole('button', { name: 'Кофе' })).toBeInTheDocument())

    expect(screen.queryByRole('button', { name: 'Море' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Музеи' })).toBeInTheDocument()
  })

  it('shows sea chip for cities with sea feature', async () => {
    render(<RandomRouteDraftEditor citySlug="zelenogradsk" features={['sea']} />)

    await waitFor(() => expect(screen.getByRole('button', { name: 'Море' })).toBeInTheDocument())
  })
})
