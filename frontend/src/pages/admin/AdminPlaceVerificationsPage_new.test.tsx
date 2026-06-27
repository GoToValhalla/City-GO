/* @vitest-environment jsdom */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminApiError } from './adminApi'
import { AdminErrorBoundary } from './AdminErrorBoundary'
import { AdminPlaceVerificationsPage } from './AdminPlaceVerificationsPage'
import { adminGet } from './adminApi'

vi.mock('./adminApi', async () => {
  const actual = await vi.importActual<typeof import('./adminApi')>('./adminApi')
  return { ...actual, adminGet: vi.fn(), adminPost: vi.fn() }
})

vi.mock('./AdminCategorySelect', () => ({
  AdminCategorySelect: () => <select aria-label="Категория"><option value="">Все категории</option></select>,
}))

const mockedAdminGet = vi.mocked(adminGet)
const summary = { queue_total: 3, needs_recheck: 2, unverified: 1, low_confidence: 1, verified_today: 4 }
const queue = {
  items: [{ place_id: 7, title: 'Музей', slug: 'museum', city_slug: 'zelenogradsk', category: 'museum', lat: 1, lng: 2, address: 'ул. 1', verification_status: 'unverified', existence_confidence_score: 30 }],
  total: 1, limit: 50, offset: 0,
}
const cities = { items: [{ id: 1, slug: 'zelenogradsk', name: 'Зеленоградск' }] }

afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('AdminPlaceVerificationsPage', () => {
  it('shows summary even when queue request fails', async () => {
    mockAdminGet({ queueError: apiError('/admin/place-verifications/queue', 500), summary, cities })
    renderPage()

    expect(await screen.findByText('В очереди')).toBeTruthy()
    expect(await screen.findByText(/GET \/admin\/place-verifications\/queue/)).toBeTruthy()
    expect(screen.queryByText(/backend запущен/i)).toBeNull()
  })

  it('shows queue even when summary request fails', async () => {
    mockAdminGet({ summaryError: apiError('/admin/place-verifications/summary', 404), queue, cities })
    renderPage()

    expect(await screen.findByText('Музей')).toBeTruthy()
    expect(await screen.findByText(/GET \/admin\/place-verifications\/summary/)).toBeTruthy()
    expect(await screen.findByText(/HTTP 404/)).toBeTruthy()
  })

  it('shows network error with endpoint', async () => {
    mockAdminGet({ queueError: new AdminApiError({ method: 'GET', endpoint: '/admin/place-verifications/queue', responseText: 'Failed to fetch' }), summary, cities })
    renderPage()

    expect(await screen.findByText(/Backend недоступен для GET \/admin\/place-verifications\/queue/)).toBeTruthy()
  })
})

describe('AdminErrorBoundary', () => {
  it('catches render errors', async () => {
    const Broken = () => { throw new Error('render exploded') }
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    render(<AdminErrorBoundary title="Проверка мест"><Broken /></AdminErrorBoundary>)

    expect(await screen.findByText('Проверка мест')).toBeTruthy()
    expect(await screen.findByText('render exploded')).toBeTruthy()
  })
})

const renderPage = () => render(<MemoryRouter><AdminPlaceVerificationsPage /></MemoryRouter>)

const apiError = (endpoint: string, status: number) => new AdminApiError({
  method: 'GET', endpoint, status, statusText: 'Broken',
  responseText: JSON.stringify({ detail: 'boom', request_id: 'req-1' }),
  requestId: 'req-1',
})

const mockAdminGet = (data: {
  queue?: typeof queue
  summary?: typeof summary
  cities?: typeof cities
  queueError?: Error
  summaryError?: Error
  citiesError?: Error
}) => {
  mockedAdminGet.mockImplementation((path: string) => {
    if (path.startsWith('/admin/place-verifications/queue')) return data.queueError ? Promise.reject(data.queueError) : Promise.resolve(data.queue ?? queue)
    if (path === '/admin/place-verifications/summary') return data.summaryError ? Promise.reject(data.summaryError) : Promise.resolve(data.summary ?? summary)
    if (path === '/admin/cities?limit=100') return data.citiesError ? Promise.reject(data.citiesError) : Promise.resolve(data.cities ?? cities)
    return Promise.reject(new Error(`Unexpected path ${path}`))
  })
}
