/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminReviewsPage } from './AdminReviewsPage'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('./adminApi', () => ({
  adminGet: (...args: unknown[]) => mockGet(...args),
  adminPost: (...args: unknown[]) => mockPost(...args),
}))

const review = { id: 5, place_id: 7, place_name: 'Музей', source: 'EXTERNAL_API_ENRICHED', confidence: 0.5, status: 'pending', reason: 'LOW_CONFIDENCE_SCORE', created_at: '2026-07-06T08:00:00Z', place_version_at_creation: 3 }
const diff = { ...review, proposed_diff: { address: { current: 'старый', proposed: 'новый', reason: 'LOW_CONFIDENCE_SCORE' } } }

describe('AdminReviewsPage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders list and diff without raw reason codes', async () => {
    mockGet.mockResolvedValueOnce([review]).mockResolvedValueOnce(diff)
    render(<MemoryRouter><AdminReviewsPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Музей')).toBeInTheDocument())
    expect(screen.getByText('Низкая уверенность источника')).toBeInTheDocument()
    expect(screen.queryByText('LOW_CONFIDENCE_SCORE')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Открыть diff/i }))
    await waitFor(() => expect(screen.getByText('новый')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Применить выбранное/i })).toBeDisabled()
  })

  it('merges selected fields and shows safe conflict message on failure', async () => {
    mockGet.mockResolvedValueOnce([review]).mockResolvedValueOnce(diff)
    mockPost.mockRejectedValueOnce(new Error('VERSION_MISMATCH'))
    render(<MemoryRouter><AdminReviewsPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Музей')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /Открыть diff/i }))
    await waitFor(() => expect(screen.getByLabelText('Выбрать Адрес')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Выбрать Адрес'))
    fireEvent.click(screen.getByRole('button', { name: /Применить выбранное/i }))

    await waitFor(() => expect(screen.getByText(/обновите diff/i)).toBeInTheDocument())
    expect(screen.queryByText('VERSION_MISMATCH')).not.toBeInTheDocument()
  })
})
