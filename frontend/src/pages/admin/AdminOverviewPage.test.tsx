/** @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { adminGetMock, adminPostMock, adminPostLongMock } = vi.hoisted(() => ({
  adminGetMock: vi.fn(),
  adminPostMock: vi.fn(),
  adminPostLongMock: vi.fn(),
}))

vi.mock('./adminApi', () => ({
  adminGet: adminGetMock,
  adminPost: adminPostMock,
  adminPostLong: adminPostLongMock,
}))

import { AdminOverviewPage } from './AdminOverviewPage'

type MockJob = {
  job_id: number
  status: string
  runtime_status: string
  is_running: boolean
  is_stale: boolean
  started_at: string
  last_heartbeat_at: string
  affected_count: number
  changed_count: number
  queued_count: number
  skipped_count: number
  failed_count: number
  remaining_count: number
  stop_requested: boolean
  actions: Array<{ action_code: string; title: string; status: string; affected_count: number; queued_count: number; skipped_count: number; failed_count: number }>
}

const fullRunPath = '/admin/overview/backlog-reduction/full-safe-run'
const applyPath = '/admin/overview/backlog-reduction/apply'
const safeActions = ['enqueue_photo_discovery', 'enqueue_address_recovery', 'enqueue_description_enrichment', 'auto_recheck_verification_backlog']
const forbiddenActions = ['recompute_route_eligibility', 'exclude_service_places_from_routes', 'classify_unknown_categories_deterministic', 'normalize_manual_review_backlog', 'recompute_low_confidence']
const titles: Record<string, string> = { enqueue_photo_discovery: 'Фото', enqueue_address_recovery: 'Адреса', enqueue_description_enrichment: 'Описания', auto_recheck_verification_backlog: 'Перепроверка данных' }

let latestJob: MockJob | null = null

const makeJob = (overrides: Partial<MockJob> = {}): MockJob => ({
  job_id: 42,
  status: 'running',
  runtime_status: 'running',
  is_running: true,
  is_stale: false,
  started_at: '2026-07-05T10:00:00',
  last_heartbeat_at: '2026-07-05T10:01:00',
  affected_count: 0,
  changed_count: 0,
  queued_count: 0,
  skipped_count: 0,
  failed_count: 0,
  remaining_count: safeActions.length,
  stop_requested: false,
  actions: safeActions.map((action) => ({ action_code: action, title: titles[action], status: 'pending', affected_count: 0, queued_count: 0, skipped_count: 0, failed_count: 0 })),
  ...overrides,
})

const report = { summary: { queued_24h: 0, active_tasks: 0, skipped_24h: 0, failed_24h: 0 }, last_result: null, task_stats: [], recent_runs: [] }

const renderOverview = () => render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

const mockReads = () => {
  adminGetMock.mockImplementation((path: string) => {
    if (path === '/admin/overview') return Promise.resolve({ critical: [], data_quality: [], operations: [], recent_audit_count: 0 })
    if (path === '/admin/overview/backlog-reduction/report') return Promise.resolve(report)
    if (path === `${fullRunPath}/latest`) return Promise.resolve(latestJob)
    if (path.match(new RegExp(`^${fullRunPath}/\\d+$`))) return Promise.resolve(latestJob)
    if (path === '/admin/overview/backlog-breakdown') return Promise.resolve({ summary: { unique_problem_places: 0, total_problem_signals: 0, auto_fixable_places: 0, manual_places: 0 }, queues: [], overlaps: [] })
    if (path === '/admin/overview/backlog-reduction-plan') return Promise.resolve({ summary: {}, actions: [] })
    throw new Error(`Unexpected adminGet path: ${path}`)
  })
}

describe('AdminOverviewPage backend-owned full safe backlog run', () => {
  beforeEach(() => {
    cleanup()
    vi.clearAllMocks()
    latestJob = null
    mockReads()
  })

  afterEach(() => cleanup())

  it('starts only the backend-owned full safe run and never calls client-side apply orchestration', async () => {
    adminPostMock.mockImplementation((path: string) => {
      if (path === `${fullRunPath}/start`) {
        latestJob = makeJob({ job_id: 77 })
        return Promise.resolve(latestJob)
      }
      throw new Error(`Unexpected adminPost path: ${path}`)
    })

    renderOverview()
    fireEvent.click(await screen.findByRole('button', { name: 'Запустить полный безопасный прогон' }))

    const result = await screen.findByTestId('full-safe-backlog-run-result')
    expect(result.textContent).toContain('Процесс #77')
    expect(adminPostMock).toHaveBeenCalledWith(`${fullRunPath}/start`)
    expect(adminPostMock.mock.calls.some(([path]) => path === applyPath)).toBe(false)
    expect(adminPostLongMock).not.toHaveBeenCalled()
    forbiddenActions.forEach((action) => expect(document.body.textContent).not.toContain(action))
  })

  it('shows the latest persisted stuck job after page load', async () => {
    latestJob = makeJob({ job_id: 78, runtime_status: 'stuck', is_stale: true, last_heartbeat_at: '2026-07-05T09:00:00' })

    renderOverview()

    const result = await screen.findByTestId('full-safe-backlog-run-result')
    expect(result.textContent).toContain('Процесс #78')
    expect(result.textContent).toContain('Нет прогресса больше 10 минут')
    expect(result.textContent).toContain('Фото')
    expect(result.textContent).toContain('Перепроверка данных')
    expect(adminGetMock.mock.calls.some(([path]) => path === `${fullRunPath}/latest`)).toBe(true)
  })

  it('calls stop endpoint and refreshes the current job state', async () => {
    latestJob = makeJob({ job_id: 99 })
    adminPostMock.mockImplementation((path: string) => {
      if (path === `${fullRunPath}/99/stop`) {
        latestJob = makeJob({ job_id: 99, status: 'stop_requested', runtime_status: 'stop_requested', stop_requested: true })
        return Promise.resolve(latestJob)
      }
      throw new Error(`Unexpected adminPost path: ${path}`)
    })

    renderOverview()

    const section = await screen.findByTestId('admin-full-safe-backlog-run')
    fireEvent.click(await within(section).findByRole('button', { name: 'Остановить процесс' }))

    await waitFor(() => expect(adminPostMock).toHaveBeenCalledWith(`${fullRunPath}/99/stop`))
    const result = await screen.findByTestId('full-safe-backlog-run-result')
    expect(result.textContent).toContain('Статус: Остановка запрошена / Остановка запрошена')
  })
})
