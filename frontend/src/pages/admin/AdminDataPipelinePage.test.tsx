/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDataPipelinePage } from './AdminDataPipelinePage'

const mockGet = vi.fn()

vi.mock('./adminApi', () => ({
  adminGet: (...args: unknown[]) => mockGet(...args),
}))

const healthyPayload = {
  overall_status: 'healthy',
  degraded_sections: [],
  metrics: {
    places_total: 120,
    places_without_coordinates: 3,
    places_route_eligible: 80,
    open_review_items: 0,
    pending_photos: 0,
    active_import_jobs: 0,
    active_enrichment_tasks: 0,
  },
  queues: [
    { code: 'import', label: 'Импорт данных', pending_count: 0, running_count: 0, failed_count: 0, status: 'idle', updated_at: '2026-07-05T12:00:00' },
    { code: 'enrichment', label: 'Обогащение', pending_count: 0, running_count: 0, failed_count: 0, status: 'idle', updated_at: '2026-07-05T12:00:00' },
    { code: 'photo_review', label: 'Проверка фотографий', pending_count: 0, running_count: 0, failed_count: 0, status: 'idle', updated_at: '2026-07-05T12:00:00' },
    { code: 'verification', label: 'Проверка мест', pending_count: 0, running_count: 0, failed_count: 0, status: 'idle', updated_at: '2026-07-05T12:00:00' },
  ],
  recent_runs: [],
  fetched_at: '2026-07-05T12:00:00',
}

describe('AdminDataPipelinePage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders read-only dashboard without write buttons', async () => {
    mockGet.mockResolvedValueOnce(healthyPayload)
    render(<MemoryRouter><AdminDataPipelinePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Мониторинг конвейера данных')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Обновить данные мониторинга/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /применить|repair|импорт|enqueue/i })).not.toBeInTheDocument()
    expect(screen.queryByText('import')).not.toBeInTheDocument()
  })

  it('shows partial degraded banner', async () => {
    mockGet.mockResolvedValueOnce({
      ...healthyPayload,
      overall_status: 'partial_degraded',
      degraded_sections: ['Импорт', 'Координаты'],
    })
    render(<MemoryRouter><AdminDataPipelinePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText(/Часть данных временно недоступна/i)).toBeInTheDocument())
  })

  it('refresh button reloads status and stays stable on error', async () => {
    mockGet.mockResolvedValueOnce(healthyPayload)
    render(<MemoryRouter><AdminDataPipelinePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Мониторинг конвейера данных')).toBeInTheDocument())
    mockGet.mockRejectedValueOnce(new Error('network'))
    fireEvent.click(screen.getByRole('button', { name: /Обновить данные мониторинга/i }))
    await waitFor(() => expect(screen.getByText(/network|Сбой выполнения операции/i)).toBeInTheDocument())
    expect(screen.getByText('Мониторинг конвейера данных')).toBeInTheDocument()
  })
})
