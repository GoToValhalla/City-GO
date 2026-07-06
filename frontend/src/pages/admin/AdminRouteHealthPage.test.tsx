/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminRouteHealthPage } from './AdminRouteHealthPage'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('./adminApi', () => ({
  adminGet: (...args: unknown[]) => mockGet(...args),
  adminPost: (...args: unknown[]) => mockPost(...args),
}))

const summary = {
  city_slug: null,
  checked_at: '2026-07-06T10:00:00',
  routes_checked: 2,
  critical_count: 1,
  warning_count: 1,
  status: 'critical',
  issues: [
    {
      code: 'route_service_places_detected',
      label: 'raw service label',
      severity: 'critical',
      route_id: 1,
      route_title: 'Маршрут с аптекой',
      details: { total: 1, places: [{ id: 7, title: 'Аптека', category: 'pharmacy' }] },
    },
    {
      code: 'route_long_transition_warning',
      label: 'raw distance label',
      severity: 'warning',
      route_id: 2,
      route_title: 'Длинный маршрут',
      details: { distance_km: 7.2 },
    },
  ],
}

describe('AdminRouteHealthPage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders readable issue details without raw JSON codes', async () => {
    mockGet.mockResolvedValueOnce(summary)
    render(<AdminRouteHealthPage />)

    await waitFor(() => expect(screen.getByText('Диагностика маршрутов')).toBeInTheDocument())
    expect(screen.getByText('Служебных точек: 1')).toBeInTheDocument()
    expect(screen.getByText('Длина маршрута: 7.2 км')).toBeInTheDocument()
    expect(screen.queryByText(/"places"/)).not.toBeInTheDocument()
    expect(screen.queryByText(/route_service_places_detected/)).not.toBeInTheDocument()
  })

  it('disables re-run button while backend check is running', async () => {
    mockGet.mockResolvedValueOnce({ ...summary, issues: [] })
    render(<AdminRouteHealthPage />)

    await waitFor(() => expect(screen.getByText('Диагностика маршрутов')).toBeInTheDocument())
    let resolvePost: (value: unknown) => void = () => {}
    mockPost.mockReturnValueOnce(new Promise((resolve) => { resolvePost = resolve }))
    fireEvent.click(screen.getByRole('button', { name: /Перезапустить диагностику/i }))

    await waitFor(() => expect(screen.getByRole('button', { name: /Проверка выполняется/i })).toBeDisabled())
    resolvePost({ result: { ...summary, status: 'healthy', critical_count: 0, warning_count: 0, issues: [] } })
    await waitFor(() => expect(screen.getByRole('button', { name: /Перезапустить диагностику/i })).not.toBeDisabled())
  })
})
