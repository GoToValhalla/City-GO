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
  timeline: [
    { timestamp: '2026-07-12T12:32:50Z', severity: 'info', type: 'job_claimed', summary: 'Import worker claiming job #9', payload: { job_id: 9 } },
    { timestamp: '2026-07-12T12:37:01Z', severity: 'error', type: 'failed', summary: 'Import worker failed job #9: boom', payload: { error: 'boom' } },
  ],
  diagnostic_report: 'CITY GO — Import Job Diagnostic Report\nJob #9 — Алматы (almaty)\nStatus: failed',
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
    expect(screen.getByText('Ошибка')).toBeTruthy()
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
})
