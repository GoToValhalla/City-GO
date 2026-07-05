/** @vitest-environment jsdom */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

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

type MockStep = {
  action_code: string
  title: string
  status: string
  affected_count: number
  changed_count: number
  queued_count: number
  skipped_count: number
  failed_count: number
  started_at: string | null
  finished_at: string | null
  message: string | null
}
type MockJob = {
  job_id: number
  status: string
  runtime_status: string
  is_running: boolean
  is_stale: boolean
  created_at: string
  updated_at: string
  actor: string
  action_code: string
  status_label: string
  started_at: string
  finished_at: string | null
  last_heartbeat_at: string
  total_actions: number
  processed_actions: number
  remaining_actions: number
  affected_count: number
  changed_count: number
  queued_count: number
  skipped_count: number
  failed_count: number
  remaining_count: number
  stop_requested: boolean
  actions: MockStep[]
}

type ApplyResult = {
  action_code: string
  status: string
  dry_run: boolean
  affected_count: number
  changed_count: number
  queued_count: number
  skipped_count: number
  failed_count: number
  message: string
}

const fullRunPath = '/admin/overview/backlog-reduction/full-safe-run'
const applyPath = '/admin/overview/backlog-reduction/apply'
const safeActions = [
  'enqueue_photo_discovery',
  'enqueue_address_recovery',
  'enqueue_description_enrichment',
  'auto_recheck_verification_backlog',
]
const forbiddenActions = [
  'recompute_route_eligibility',
  'exclude_service_places_from_routes',
  'classify_unknown_categories_deterministic',
  'normalize_manual_review_backlog',
  'recompute_low_confidence',
]
const actionTitles: Record<string, string> = {
  enqueue_photo_discovery: 'Фото',
  enqueue_address_recovery: 'Адреса',
  enqueue_description_enrichment: 'Описания',
  auto_recheck_verification_backlog: 'Перепроверка данных',
}
const report = {
  summary: {
    runs_24h: 0,
    runs_7d: 0,
    queued_24h: 0,
    queued_7d: 0,
    skipped_24h: 0,
    skipped_7d: 0,
    failed_24h: 0,
    failed_7d: 0,
    tasks_created_24h: 0,
    tasks_created_7d: 0,
    active_tasks: 0,
  },
  last_result: null,
  task_stats: [],
  recent_runs: [],
}

let latestJob: MockJob | null = null

const renderOverview = () => render(
  <MemoryRouter>
    <AdminOverviewPage />
  </MemoryRouter>,
)

const makeJob = (overrides: Partial<MockJob> = {}): MockJob => ({
  job_id: 42,
  status: 'running',
  runtime_status: 'running',
  is_running: true,
  is_stale: false,
  created_at: '2026-07-05T10:00:00',
  updated_at: '2026-07-05T10:00:00',
  actor: 'admin',
  action_code: 'full_safe_queue_run',
  status_label: 'Выполняется',
  started_at: '2026-07-05T10:00:00',
  finished_at: null,
  last_heartbeat_at: '2026-07-05T10:01:00',
  total_actions: safeActions.length,
  processed_actions: 0,
  remaining_actions: safeActions.length,
  affected_count: 0,
  changed_count: 0,
  queued_count: 0,
  skipped_count: 0,
  failed_count: 0,
  remaining_count: safeActions.length,
  stop_requested: false,
  actions: safeActions.map((action) => ({
    action_code: action,
    title: actionTitles[action],
    status: 'pending',
    affected_count: 0,
    changed_count: 0,
    queued_count: 0,
    skipped_count: 0,
    failed_count: 0,
    started_at: null,
    finished_at: null,
    message: null,
  })),
  ...overrides,
})

const recomputeJob = (job: MockJob): MockJob => {
  const doneStatuses = new Set(['applied', 'completed', 'partial', 'failed', 'unsupported'])
  const processed = job.actions.filter((action) => doneStatuses.has(action.status)).length
  return {
    ...job,
    processed_actions: processed,
    remaining_actions: job.actions.length - processed,
    remaining_count: job.actions.length - processed,
    affected_count: job.actions.reduce((sum, action) => sum + action.affected_count, 0),
    changed_count: job.actions.reduce((sum, action) => sum + action.changed_count, 0),
    queued_count: job.actions.reduce((sum, action) => sum + action.queued_count, 0),
    skipped_count: job.actions.reduce((sum, action) => sum + action.skipped_count, 0),
    failed_count: job.actions.reduce((sum, action) => sum + action.failed_count, 0),
    last_heartbeat_at: '2026-07-05T10:02:00',
  }
}

const applyStepResult = (actionCode: string, result: Partial<ApplyResult>) => {
  if (!latestJob) throw new Error('Missing latest job')
  latestJob = recomputeJob({
    ...latestJob,
    actions: latestJob.actions.map((action) => action.action_code === actionCode ? {
      ...action,
      status: result.status ?? 'completed',
      affected_count: result.affected_count ?? 0,
      changed_count: result.changed_count ?? 0,
      queued_count: result.queued_count ?? 0,
      skipped_count: result.skipped_count ?? 0,
      failed_count: result.failed_count ?? 0,
      message: result.message ?? null,
      finished_at: '2026-07-05T10:02:00',
    } : action),
  })
  return latestJob
}

const getStepAction = (path: string) => path.match(/steps\/([^/]+)\/(running|result|error)$/)?.[1]

const mockAdminReads = () => {
  adminGetMock.mockImplementation((path: string) => {
    if (path === '/admin/overview') {
      return Promise.resolve({ critical: [], data_quality: [], operations: [], recent_audit_count: 0 })
    }
    if (path === '/admin/overview/backlog-reduction/report') {
      return Promise.resolve(report)
    }
    if (path === `${fullRunPath}/latest`) {
      return Promise.resolve(latestJob)
    }
    if (path.match(new RegExp(`^${fullRunPath}/\\d+$`))) {
      return Promise.resolve(latestJob)
    }
    if (path === '/admin/overview/backlog-breakdown') {
      return Promise.resolve({
        summary: {
          unique_problem_places: 0,
          total_problem_signals: 0,
          route_blocker_places: 0,
          auto_fixable_places: 0,
          manual_places: 0,
          verification_backlog_places: 0,
          content_gap_places: 0,
        },
        queues: [],
        overlaps: [],
      })
    }
    if (path === '/admin/overview/backlog-reduction-plan') {
      return Promise.resolve({ summary: {}, actions: [] })
    }
    throw new Error(`Unexpected adminGet path: ${path}`)
  })
}

const mockFullRunWrites = () => {
  adminPostLongMock.mockImplementation((path: string, body?: unknown) => {
    if (path === fullRunPath) {
      latestJob = makeJob()
      return Promise.resolve(latestJob)
    }
    if (path.endsWith('/running')) {
      const actionCode = getStepAction(path)
      if (!latestJob || !actionCode) throw new Error(`Unexpected running path: ${path}`)
      latestJob = {
        ...latestJob,
        actions: latestJob.actions.map((action) => action.action_code === actionCode ? { ...action, status: 'running', started_at: '2026-07-05T10:01:00' } : action),
      }
      return Promise.resolve(latestJob)
    }
    if (path === applyPath) {
      const actionCode = (body as { action_code: string }).action_code
      if (actionCode === 'enqueue_address_recovery') {
        return Promise.reject(new Error('address failed'))
      }
      const response = {
        action_code: actionCode,
        status: 'applied',
        dry_run: false,
        affected_count: actionCode === 'enqueue_photo_discovery' ? 10 : actionCode === 'enqueue_description_enrichment' ? 5 : 3,
        changed_count: 0,
        queued_count: actionCode === 'enqueue_photo_discovery' ? 8 : actionCode === 'enqueue_description_enrichment' ? 5 : 2,
        skipped_count: actionCode === 'enqueue_photo_discovery' ? 2 : actionCode === 'enqueue_description_enrichment' ? 0 : 1,
        failed_count: actionCode === 'auto_recheck_verification_backlog' ? 1 : 0,
        message: `${actionCode} done`,
      }
      return Promise.resolve(response)
    }
    if (path.endsWith('/result')) {
      const actionCode = getStepAction(path)
      if (!actionCode) throw new Error(`Unexpected result path: ${path}`)
      return Promise.resolve(applyStepResult(actionCode, body as ApplyResult))
    }
    if (path.endsWith('/error')) {
      const actionCode = getStepAction(path)
      if (!actionCode) throw new Error(`Unexpected error path: ${path}`)
      return Promise.resolve(applyStepResult(actionCode, { status: 'failed', failed_count: 1, message: (body as { message: string }).message }))
    }
    if (path.endsWith('/complete')) {
      if (!latestJob) throw new Error('Missing latest job')
      latestJob = { ...latestJob, status: latestJob.failed_count ? 'partial' : 'completed', runtime_status: latestJob.failed_count ? 'partial' : 'completed', is_running: false, finished_at: '2026-07-05T10:03:00' }
      return Promise.resolve(latestJob)
    }
    throw new Error(`Unexpected adminPostLong path: ${path}`)
  })
}

describe('AdminOverviewPage persistent full safe backlog reduction', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    latestJob = null
    mockAdminReads()
  })

  it('creates a persistent full-run job, records running/result/error per action, and renders the saved report', async () => {
    mockFullRunWrites()

    renderOverview()

    const startButton = await screen.findByRole('button', { name: 'Запустить полный безопасный прогон' })
    fireEvent.click(startButton)

    const runningButton = await screen.findByRole('button', { name: 'Запускаем полный прогон…' })
    expect((runningButton as HTMLButtonElement).disabled).toBe(true)

    await waitFor(() => expect(adminPostLongMock.mock.calls.some(([path]) => path === `${fullRunPath}/42/complete`)).toBe(true))

    expect(adminPostLongMock.mock.calls[0][0]).toBe(fullRunPath)
    safeActions.forEach((action) => {
      expect(adminPostLongMock.mock.calls.some(([path]) => path === `${fullRunPath}/42/steps/${action}/running`)).toBe(true)
    })
    expect(adminPostLongMock.mock.calls.some(([path]) => path === `${fullRunPath}/42/steps/enqueue_photo_discovery/result`)).toBe(true)
    expect(adminPostLongMock.mock.calls.some(([path]) => path === `${fullRunPath}/42/steps/enqueue_address_recovery/error`)).toBe(true)

    const applyCalls = adminPostLongMock.mock.calls.filter(([path]) => path === applyPath)
    expect(applyCalls.map(([, body]) => (body as { action_code: string }).action_code)).toEqual(safeActions)
    applyCalls.forEach(([, body]) => {
      expect(body).toMatchObject({ confirmation_text: 'APPLY', limit: 500, include_samples: true })
    })
    forbiddenActions.forEach((action) => {
      expect(applyCalls.map(([, body]) => (body as { action_code: string }).action_code)).not.toContain(action)
    })

    const resultCalls = adminPostLongMock.mock.calls.filter(([path]) => String(path).endsWith('/result'))
    expect(resultCalls[0][1]).toMatchObject({ action_code: 'enqueue_photo_discovery', affected_count: 10, queued_count: 8 })
    const errorCall = adminPostLongMock.mock.calls.find(([path]) => path === `${fullRunPath}/42/steps/enqueue_address_recovery/error`)
    expect(errorCall?.[1]).toEqual({ message: 'address failed' })

    const result = await screen.findByTestId('full-safe-backlog-run-result')
    expect(within(result).getByText('Процесс #42')).toBeTruthy()
    expect(within(result).getByText('Всего кандидатов')).toBeTruthy()
    expect(within(result).getByText('18')).toBeTruthy()
    expect(within(result).getByText('Всего поставлено в очередь')).toBeTruthy()
    expect(within(result).getByText('15')).toBeTruthy()
    expect(within(result).getByText('Всего ошибок')).toBeTruthy()
    expect(within(result).getAllByText('2').length).toBeGreaterThan(0)
    expect(within(result).getByText('Фото')).toBeTruthy()
    expect(within(result).getByText('Адреса')).toBeTruthy()
    await waitFor(() => expect(adminGetMock.mock.calls.filter(([path]) => path === '/admin/overview/backlog-reduction/report').length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(adminGetMock.mock.calls.filter(([path]) => path === `${fullRunPath}/latest`).length).toBeGreaterThanOrEqual(2))
  })

  it('shows the latest persisted job after page load', async () => {
    latestJob = recomputeJob(makeJob({
      job_id: 77,
      status: 'running',
      runtime_status: 'stuck',
      is_stale: true,
      last_heartbeat_at: '2026-07-05T09:00:00',
      actions: makeJob().actions.map((action, index) => index === 0 ? { ...action, status: 'applied', affected_count: 11, queued_count: 9, skipped_count: 2 } : action),
    }))

    renderOverview()

    const result = await screen.findByTestId('full-safe-backlog-run-result')
    expect(within(result).getByText('Процесс #77')).toBeTruthy()
    expect(within(result).getByText('Нет прогресса больше 10 минут')).toBeTruthy()
    expect(within(result).getByText('Фото')).toBeTruthy()
    expect(within(result).getByText('Перепроверка данных')).toBeTruthy()
    expect(adminGetMock.mock.calls.some(([path]) => path === `${fullRunPath}/latest`)).toBe(true)
  })

  it('calls stop endpoint and refreshes the current job state', async () => {
    latestJob = makeJob({ job_id: 99 })
    adminPostMock.mockImplementation((path: string) => {
      if (path === `${fullRunPath}/99/stop`) {
        latestJob = { ...makeJob({ job_id: 99 }), status: 'stop_requested', runtime_status: 'stop_requested', stop_requested: true }
        return Promise.resolve(latestJob)
      }
      throw new Error(`Unexpected adminPost path: ${path}`)
    })

    renderOverview()

    const stopButton = await screen.findByRole('button', { name: 'Остановить процесс' })
    fireEvent.click(stopButton)

    await waitFor(() => expect(adminPostMock).toHaveBeenCalledWith(`${fullRunPath}/99/stop`))
    const result = await screen.findByTestId('full-safe-backlog-run-result')
    expect(within(result).getByText('Статус: Остановка запрошена / Остановка запрошена')).toBeTruthy()
  })
})
