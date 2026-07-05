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

const renderOverview = () => render(
  <MemoryRouter>
    <AdminOverviewPage />
  </MemoryRouter>,
)

describe('AdminOverviewPage full safe backlog reduction', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    adminGetMock.mockImplementation((path: string) => {
      if (path === '/admin/overview') {
        return Promise.resolve({ critical: [], data_quality: [], operations: [], recent_audit_count: 0 })
      }
      if (path === '/admin/overview/backlog-reduction/report') {
        return Promise.resolve(report)
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
  })

  it('runs only safe queue actions with long POST and renders the final report', async () => {
    const responses = [
      { action_code: safeActions[0], status: 'applied', dry_run: false, affected_count: 10, changed_count: 0, queued_count: 8, skipped_count: 2, failed_count: 0, message: 'photo queued' },
      { action_code: safeActions[1], status: 'applied', dry_run: false, affected_count: 7, changed_count: 0, queued_count: 4, skipped_count: 3, failed_count: 0, message: 'address queued' },
      { action_code: safeActions[2], status: 'applied', dry_run: false, affected_count: 5, changed_count: 0, queued_count: 5, skipped_count: 0, failed_count: 0, message: 'description queued' },
      { action_code: safeActions[3], status: 'applied', dry_run: false, affected_count: 3, changed_count: 0, queued_count: 2, skipped_count: 1, failed_count: 1, message: 'verification queued' },
    ]
    let resolveFirst: (value: unknown) => void = () => {}
    adminPostLongMock
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve }))
      .mockResolvedValueOnce(responses[1])
      .mockResolvedValueOnce(responses[2])
      .mockResolvedValueOnce(responses[3])

    renderOverview()

    const startButton = await screen.findByRole('button', { name: 'Запустить полный безопасный прогон' })
    fireEvent.click(startButton)

    const runningButton = await screen.findByRole('button', { name: 'Запускаем полный прогон…' })
    expect((runningButton as HTMLButtonElement).disabled).toBe(true)

    resolveFirst(responses[0])

    await waitFor(() => expect(adminPostLongMock).toHaveBeenCalledTimes(4))
    const calls = adminPostLongMock.mock.calls
    expect(calls.map(([path]) => path)).toEqual(safeActions.map(() => '/admin/overview/backlog-reduction/apply'))
    expect(calls.map(([, body]) => (body as { action_code: string }).action_code)).toEqual(safeActions)
    calls.forEach(([, body]) => {
      expect(body).toMatchObject({ confirmation_text: 'APPLY', limit: 500, include_samples: true })
    })
    forbiddenActions.forEach((action) => {
      expect(calls.map(([, body]) => (body as { action_code: string }).action_code)).not.toContain(action)
    })
    expect(adminPostMock).not.toHaveBeenCalled()

    const result = await screen.findByTestId('full-safe-backlog-run-result')
    expect(within(result).getByText('Всего кандидатов')).toBeTruthy()
    expect(within(result).getByText('25')).toBeTruthy()
    expect(within(result).getByText('Всего поставлено в очередь')).toBeTruthy()
    expect(within(result).getByText('19')).toBeTruthy()
    expect(within(result).getByText('Всего пропущено')).toBeTruthy()
    expect(within(result).getByText('6')).toBeTruthy()
    expect(within(result).getByText('Всего ошибок')).toBeTruthy()
    expect(within(result).getAllByText('1').length).toBeGreaterThan(0)
    safeActions.forEach((action) => {
      expect(within(result).getByText(action)).toBeTruthy()
    })
    await waitFor(() => expect(adminGetMock.mock.calls.filter(([path]) => path === '/admin/overview/backlog-reduction/report').length).toBeGreaterThanOrEqual(2))
  })
})
