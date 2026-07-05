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
    places_without_coordinates: 0,
    places_route_eligible: 80,
    open_review_items: 0,
    pending_photos: 0,
    active_import_jobs: 0,
    active_enrichment_tasks: 0,
  },
  queues: [],
  recent_runs: [],
  fetched_at: '2026-07-05T12:00:00',
}

describe('AdminDataPipelinePage UI states', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows loading state before first payload', () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    render(<MemoryRouter><AdminDataPipelinePage /></MemoryRouter>)
    expect(screen.getByText(/Загрузка данных из реестра/i)).toBeInTheDocument()
  })

  it('shows fatal error with retry when initial load fails', async () => {
    mockGet.mockRejectedValueOnce(new Error('503 unavailable'))
    render(<MemoryRouter><AdminDataPipelinePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Не удалось загрузить мониторинг')).toBeInTheDocument())
    expect(screen.getByText('503 unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /повторить/i })).toBeInTheDocument()
  })

  it('shows full degraded banner and Russian status label', async () => {
    mockGet.mockResolvedValueOnce({
      ...healthyPayload,
      overall_status: 'full_degraded',
      degraded_sections: ['Импорт', 'Обогащение', 'Проверка мест'],
    })
    render(<MemoryRouter><AdminDataPipelinePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText(/Часть данных временно недоступна/i)).toBeInTheDocument())
    expect(screen.getByText('Сильная деградация')).toBeInTheDocument()
  })

  it('disables refresh button while refreshing', async () => {
    mockGet.mockResolvedValueOnce(healthyPayload)
    render(<MemoryRouter><AdminDataPipelinePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId('admin-data-pipeline')).toBeInTheDocument())
    let resolveSecond: (v: unknown) => void = () => {}
    mockGet.mockReturnValueOnce(new Promise((resolve) => { resolveSecond = resolve }))
    fireEvent.click(screen.getByRole('button', { name: /Обновить данные мониторинга/i }))
    await waitFor(() => expect(screen.getByRole('button', { name: /Обновление/i })).toBeDisabled())
    resolveSecond(healthyPayload)
    await waitFor(() => expect(screen.getByRole('button', { name: /Обновить данные мониторинга/i })).not.toBeDisabled())
  })
})
