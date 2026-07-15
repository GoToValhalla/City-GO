/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminImportJobDiagnosticPage } from './AdminImportJobDiagnosticPage'
import { clearAdminSession } from './adminSession'

const diagnostic = {
  job_id: 9,
  city_id: 1,
  city_slug: 'almaty',
  city_name: 'Алматы',
  status: 'failed',
  current_step: 'error',
  last_completed_step: 'error',
  failure_reason: 'import-worker safety guard: available host memory (532 MB) is below the configured minimum (550 MB)',
  partial_success_reason: null,
  failed_steps: [],
  started_at: '2026-07-12T12:32:48Z',
  finished_at: '2026-07-12T12:37:03Z',
  duration_seconds: 255,
  worker_state: null,
  worker_run_id: null,
  stop_reason: null,
  stop_source: null,
  exit_code: null,
  oom_killed: null,
  workflow_name: null,
  workflow_run_id: null,
  workflow_run_url: null,
  workflow_outcome: null,
  timeline: [
    { timestamp: '2026-07-12T12:32:50Z', severity: 'info', type: 'job_claimed', summary: 'Import worker claiming job #9', payload: { job_id: 9 } },
    { timestamp: '2026-07-12T12:37:01Z', severity: 'error', type: 'failed', summary: 'Import worker failed job #9: boom', payload: { error: 'boom' } },
  ],
  attempts: [
    { attempt_number: 1, started_at: '2026-07-12T12:32:50Z', ended_at: '2026-07-12T12:37:01Z', result: 'worker_job_failed', retry_count_at_claim: 0 },
  ],
  diagnostic_report: 'CITY GO — Import Job Diagnostic Report\nJob #9 — Алматы (almaty)\nStatus: failed',
}

const diagnosticWithWorkerData = {
  ...diagnostic,
  job_id: 10,
  status: 'stalled',
  worker_state: 'stopped',
  worker_run_id: '29192806410',
  stop_reason: 'public_health_degraded',
  stop_source: 'monitor_loop',
  exit_code: 0,
  oom_killed: false,
  workflow_name: 'CITY GO · OPS · Run Import Worker Safely',
  workflow_run_id: '29192806410',
  workflow_run_url: 'https://github.com/GoToValhalla/City-GO/actions/runs/29192806410',
  workflow_outcome: { succeeded: false, reasons: ['safety_guard_public_health_degraded'] },
}

const diagnosticPartialSuccess = {
  ...diagnostic,
  job_id: 11,
  status: 'partial_success',
  failure_reason: null,
  partial_success_reason: 'Добор фото: провайдер фото не ответил вовремя',
  failed_steps: [
    { step_name: 'fetch_photo_candidates', step_label: 'Добор фото', error_message: 'провайдер фото не ответил вовремя', finished_at: '2026-07-12T12:36:00Z' },
  ],
  attempts: [],
}

const diagnosticWorkflowOomDespiteSuccess = {
  ...diagnostic,
  job_id: 12,
  status: 'success',
  failure_reason: null,
  exit_code: 137,
  oom_killed: true,
  workflow_outcome: { succeeded: false, reasons: ['worker_oom_killed'] },
}

const diagnosticNoAttempts = {
  ...diagnostic,
  job_id: 13,
  status: 'queued',
  failure_reason: null,
  attempts: [],
  timeline: [],
}

const renderPage = (jobId = '9') =>
  render(
    <MemoryRouter initialEntries={[`/admin/imports/jobs/${jobId}/diagnostic`]}>
      <Routes>
        <Route path="/admin/imports/jobs/:jobId/diagnostic" element={<AdminImportJobDiagnosticPage />} />
      </Routes>
    </MemoryRouter>,
  )

describe('AdminImportJobDiagnosticPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/import-jobs/9/diagnostic')) return Promise.resolve(new Response(JSON.stringify(diagnostic), { status: 200 }))
        if (url.includes('/import-jobs/10/diagnostic')) return Promise.resolve(new Response(JSON.stringify(diagnosticWithWorkerData), { status: 200 }))
        if (url.includes('/import-jobs/11/diagnostic')) return Promise.resolve(new Response(JSON.stringify(diagnosticPartialSuccess), { status: 200 }))
        if (url.includes('/import-jobs/12/diagnostic')) return Promise.resolve(new Response(JSON.stringify(diagnosticWorkflowOomDespiteSuccess), { status: 200 }))
        if (url.includes('/import-jobs/13/diagnostic')) return Promise.resolve(new Response(JSON.stringify(diagnosticNoAttempts), { status: 200 }))
        if (url.includes('/import-jobs/999/diagnostic')) return Promise.resolve(new Response('{}', { status: 404 }))
        return Promise.resolve(new Response('{}', { status: 404 }))
      }),
    )
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('renders job summary with status, step, failure reason and timing', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Алматы')).toBeTruthy())
    expect(screen.getByTestId('diagnostic-status-badge').textContent).toBe('Ошибка')
    expect(screen.getByTestId('diagnostic-failure-reason').textContent).toContain('532 MB')
  })

  it('renders timeline events as vertical cards in chronological order', async () => {
    renderPage()
    await waitFor(() => expect(screen.getAllByTestId('diagnostic-timeline-event').length).toBe(2))
    const events = screen.getAllByTestId('diagnostic-timeline-event')
    expect(events[0].textContent).toContain('claiming job #9')
    expect(events[1].textContent).toContain('failed job #9')
  })

  it('copies the diagnostic report to clipboard on button click', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByTestId('copy-diagnostic-report')).toBeTruthy())
    fireEvent.click(screen.getByTestId('copy-diagnostic-report'))
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(diagnostic.diagnostic_report))
  })

  it('renders raw JSON collapsed by default', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Полные данные (JSON)')).toBeTruthy())
    const details = screen.getByText('Полные данные (JSON)').closest('details')
    expect(details?.open).toBeFalsy()
  })

  it('shows an empty state for a missing job', async () => {
    renderPage('999')
    await waitFor(() => expect(screen.getByText('Задача не найдена')).toBeTruthy())
  })

  it('renders without introducing horizontal overflow markup (no tables, no nowrap wrappers)', async () => {
    const { container } = renderPage()
    await waitFor(() => expect(screen.getByText('Алматы')).toBeTruthy())
    expect(container.querySelector('table')).toBeNull()
    expect(container.querySelector('.admin-table-wrap')).toBeNull()
  })

  it('renders persisted worker/workflow fields when available (stop reason, exit code, workflow link)', async () => {
    renderPage('10')
    await waitFor(() => expect(screen.getByTestId('diagnostic-stop-reason')).toBeTruthy())
    expect(screen.getByTestId('diagnostic-stop-reason').textContent).toContain('public_health_degraded')
    expect(screen.getByTestId('diagnostic-stop-reason').textContent).toContain('monitor_loop')
    expect(screen.getByText(/Код завершения: 0/)).toBeTruthy()
    const workflowLink = screen.getByText('CITY GO · OPS · Run Import Worker Safely').closest('a')
    expect(workflowLink?.getAttribute('href')).toBe('https://github.com/GoToValhalla/City-GO/actions/runs/29192806410')
    expect(screen.getByTestId('diagnostic-workflow-outcome').textContent).toContain('workflow сообщил бы об ошибке')
  })

  it('renders the partial_success badge as a distinct warning tone, never as success or failure', async () => {
    renderPage('11')
    await waitFor(() => expect(screen.getByTestId('diagnostic-status-badge')).toBeTruthy())
    const badge = screen.getByTestId('diagnostic-status-badge')
    expect(badge.textContent).toBe('Частично завершён')
    expect(badge.className).not.toContain('pub-published')
    expect(badge.className).not.toContain('pub-hidden')
  })

  it('renders the exact partial_success reason and the failed step behind it', async () => {
    renderPage('11')
    await waitFor(() => expect(screen.getByTestId('diagnostic-partial-success-reason')).toBeTruthy())
    expect(screen.getByTestId('diagnostic-partial-success-reason').textContent).toContain('провайдер фото не ответил вовремя')
    expect(screen.getByTestId('diagnostic-failed-steps').textContent).toContain('Добор фото')
    expect(screen.getByTestId('diagnostic-failed-steps').textContent).toContain('провайдер фото не ответил вовремя')
  })

  it('distinguishes job status (success) from workflow_outcome (failed due to OOM) — never conflates the two', async () => {
    renderPage('12')
    await waitFor(() => expect(screen.getByTestId('diagnostic-status-badge')).toBeTruthy())
    expect(screen.getByTestId('diagnostic-status-badge').textContent).toBe('Завершён')
    expect(screen.getByText(/Код завершения: 137/)).toBeTruthy()
    expect(screen.getByTestId('diagnostic-workflow-outcome').textContent).toContain('workflow сообщил бы об ошибке')
    expect(screen.getByTestId('diagnostic-workflow-outcome').textContent).toContain('worker_oom_killed')
  })

  it('shows "нет данных" for workflow outcome when no worker_run_finished event was ever reported (never fabricates a verdict)', async () => {
    renderPage('9')
    await waitFor(() => expect(screen.getByTestId('diagnostic-workflow-outcome')).toBeTruthy())
    expect(screen.getByTestId('diagnostic-workflow-outcome').textContent).toContain('нет данных')
  })

  it('renders zero attempts distinctly from missing/unavailable data, with an explicit "0 attempts" message', async () => {
    renderPage('13')
    await waitFor(() => expect(screen.getByTestId('diagnostic-attempts')).toBeTruthy())
    expect(screen.getByTestId('diagnostic-attempts').textContent).toContain('попыток пока 0')
    expect(screen.queryAllByTestId('diagnostic-attempt-card')).toHaveLength(0)
  })

  it('renders attempt history as immutable cards, separate from the current job status/timeline sections', async () => {
    renderPage('9')
    await waitFor(() => expect(screen.getAllByTestId('diagnostic-attempt-card').length).toBe(1))
    const attemptCard = screen.getAllByTestId('diagnostic-attempt-card')[0]
    expect(attemptCard.textContent).toContain('Попытка №1')
    expect(attemptCard.textContent).toContain('Ошибка')
    // Attempts section must be a sibling of, not nested inside, the summary
    // and timeline sections — active job state and immutable history stay
    // visually and structurally separate.
    const summary = screen.getByTestId('diagnostic-summary')
    expect(summary.contains(attemptCard)).toBe(false)
  })

  it('renders correctly at the iPhone 12 Pro Max primary viewport (428px) without horizontal overflow', async () => {
    const originalWidth = window.innerWidth
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 428 })
    window.dispatchEvent(new Event('resize'))
    const { container } = renderPage('11')
    await waitFor(() => expect(screen.getByText('Алматы')).toBeTruthy())
    expect(container.querySelector('table')).toBeNull()
    expect(container.querySelector('.admin-table-wrap')).toBeNull()
    expect(screen.getByTestId('diagnostic-partial-success-reason')).toBeTruthy()
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: originalWidth })
  })

  it('desktop regression: full diagnostic layout (summary, failed steps, attempts, timeline, raw JSON) renders unchanged at desktop width', async () => {
    const originalWidth = window.innerWidth
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1280 })
    const { container } = renderPage('11')
    await waitFor(() => expect(screen.getByText('Алматы')).toBeTruthy())
    expect(screen.getByTestId('diagnostic-summary')).toBeTruthy()
    expect(screen.getByTestId('diagnostic-failed-steps')).toBeTruthy()
    expect(screen.getByTestId('diagnostic-attempts')).toBeTruthy()
    expect(screen.getByTestId('diagnostic-timeline')).toBeTruthy()
    expect(container.querySelector('.admin-import-diagnostic-raw')).toBeTruthy()
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: originalWidth })
  })
})
