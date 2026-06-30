/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminImportJobsPage } from './AdminImportJobsPage'
import { clearAdminSession } from './adminSession'

const runningJob = {
  id: 'city-import-1', city_id: 1, city_slug: 'almaty', city_name: 'Алматы', status: 'running',
  launch_status: 'published', current_step: 'snapshot_refresh', current_step_label: 'Обновляем snapshot',
  source: 'admin_city_import', places_total: 0, places_published: 0, places_unpublished: 0,
  pending_photos: 0, next_step: 'Ожидается backend-сбор', job_id: 9, scopes_total: 3,
  scopes_succeeded: 0, can_run: false, can_retry: false, can_cancel: true, can_publish: false,
  data_coverage: { address_coverage_pct: 50, photo_coverage_pct: 25, description_coverage_pct: 75 },
  step_details: { data_coverage: {}, change_summary: {}, admin_pipeline_contract: {} },
}
const completedJob = {
  ...runningJob,
  id: 'city-import-2', city_id: 2, city_slug: 'batumi', city_name: 'Батуми', status: 'success',
  launch_status: 'review_required', current_step: 'queued', current_step_label: 'Завершён',
  job_id: 10, can_retry: true, can_cancel: false,
}

const fetchUrl = (input: RequestInfo | URL) => input instanceof Request ? input.url : String(input)

describe('AdminImportJobsPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('confirm', vi.fn(() => true))
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = fetchUrl(input)
      if (url.includes('/admin/import-queue')) {
        return Promise.resolve(new Response(JSON.stringify({ total: 4, active_total: 2, queued: 1, running: 1, stalled_running: 0, oldest_queued_seconds: 12, next_job_ids: [9], by_source: { admin_city_import: 2 } }), { status: 200 }))
      }
      if (url.includes('/admin/import-jobs/2/retry') && init?.method === 'POST') {
        return Promise.resolve(new Response(JSON.stringify({ city_id: 1, status: 'running', message: 'ok' }), { status: 200 }))
      }
      if (url.endsWith('/admin/import-jobs/1')) {
        return Promise.resolve(new Response(JSON.stringify(runningJob), { status: 200 }))
      }
      if (url.includes('/admin/import-jobs')) {
        return Promise.resolve(new Response(JSON.stringify({ items: [runningJob, completedJob], total: 2, limit: 50, offset: 0 }), { status: 200 }))
      }
      return Promise.resolve(new Response('{}', { status: 404 }))
    }))
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('renders queue, disables running actions and retries completed job_new', async () => {
    render(<MemoryRouter><AdminImportJobsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('Алматы').length).toBeGreaterThan(0))
    expect(screen.getByText(/В очереди:/)).toBeTruthy()
    expect(screen.getAllByText('Действия заблокированы: pipeline выполняется').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Обновить snapshot')[0].hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getAllByText('Повторить сбор')[0])
    const calls = () => (fetch as unknown as { mock: { calls: Array<[RequestInfo | URL, RequestInit?]> } }).mock.calls
    await waitFor(() => expect(calls().some(([input]) => fetchUrl(input).includes('/admin/import-jobs/2/retry'))).toBe(true))
    const urls = calls().map(([input]) => fetchUrl(input))
    expect(urls.some((url) => url.includes('/admin/import-queue'))).toBe(true)
    expect(urls.every((url) => !url.includes('/admin/import-jobs/queue'))).toBe(true)
  })
})
