/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminAnalyticsPage } from './AdminAnalyticsPage'
import { AdminQualityPage } from './AdminQualityPage'
import { AdminSystemHealthPage } from './AdminSystemHealthPage'

const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

describe('admin platform screens', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/admin/quality')) return response({
        items: [{ city_slug: 'test', city_name: 'Тест', region: 'Регион', readiness_score: 70, places_total: 10, severity: 'warning', blockers: {} }],
        todo: ['Добавить snapshots'],
      })
      if (url.includes('/admin/system-health/alerts')) return response({ items: [], total: 0 })
      if (url.includes('/admin/system-health')) return response({
        services: [{ name: 'API', status: 'ok', description: 'Работает', queue_depth: 0 }],
      })
      return response({
        period_days: 30,
        metrics: { active_users: 3, route_success_rate: null },
        event_breakdown: [{ event: 'place_viewed', count: 2 }],
        availability: { dau_wau_mau: true },
      })
    }))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('renders quality filters and real city summary', async () => {
    render(<MemoryRouter><AdminQualityPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Тест')).toBeInTheDocument())
    expect(screen.getByText('Добавить snapshots')).toBeInTheDocument()
  })

  it('renders service health and empty alerts', async () => {
    render(<MemoryRouter><AdminSystemHealthPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('API')).toBeInTheDocument())
    expect(screen.getByText('Открытых инцидентов нет')).toBeInTheDocument()
  })

  it('renders analytics metrics without fake values', async () => {
    render(<MemoryRouter><AdminAnalyticsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument())
    expect(screen.getByText('Недостаточно данных')).toBeInTheDocument()
  })
})
