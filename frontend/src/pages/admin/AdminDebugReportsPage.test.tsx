/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDebugReportsPage } from './AdminDebugReportsPage'

const mockAdminGet = vi.fn()

vi.mock('./adminApi', () => ({
  adminGet: (...args: unknown[]) => mockAdminGet(...args),
}))

describe('AdminDebugReportsPage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders report list and sanitized payload_new', async () => {
    mockAdminGet.mockResolvedValueOnce({
      items: [{
        id: 1,
        public_id: 'DBG-ABC',
        created_at: '2026-07-07T10:00:00Z',
        screen: 'route',
        severity: 'warning',
        category: 'route',
        city_slug: 'zelenogradsk',
        request_id: 'req-1',
        title: 'Route diagnostics',
        summary: 'route collapsed',
        telegram_sent: true,
        sanitized_payload: { request_payload: { Authorization: '[REDACTED]' } },
      }],
    })

    render(<AdminDebugReportsPage />)

    await waitFor(() => expect(screen.getByText('DBG-ABC')).toBeInTheDocument())
    expect(screen.getByText('Отчёты диагностики')).toBeInTheDocument()
    expect(screen.getAllByText('route collapsed').length).toBeGreaterThan(0)
    expect(screen.getByText('Да')).toBeInTheDocument()
    expect(screen.getByText('Полная очищенная диагностика')).toBeInTheDocument()
  })

  it('renders empty state_new', async () => {
    mockAdminGet.mockResolvedValueOnce({ items: [] })

    render(<AdminDebugReportsPage />)

    await waitFor(() => expect(screen.getByText('Отчётов пока нет')).toBeInTheDocument())
  })
})
