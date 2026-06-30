/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminImportJobsPage } from './AdminImportJobsPage'
import { clearAdminSession } from './adminSession'

const job = {
  id: 'city-import-1', city_id: 1, city_slug: 'almaty', city_name: 'Алматы', status: 'queued',
  launch_status: 'importing', current_step: 'queued', current_step_label: 'В очереди',
  source: 'admin_city_import', places_total: 0, places_published: 0, places_unpublished: 0,
  pending_photos: 0, next_step: 'Ожидается backend-сбор', job_id: 9, scopes_total: 3,
  scopes_succeeded: 0, can_run: true, can_retry: false, can_cancel: false, can_publish: false,
  step_details: { data_coverage: {}, change_summary: {}, admin_pipeline_contract: {} },
}

const fetchUrl = (input: RequestInfo | URL) => input instanceof Request ? input.url : String(input)

describe('AdminImportJobsPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('confirm', vi.fn(() => true))
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = fetchUrl(input)
      if (url.includes('/admin/import-jobs/1/run') && init?.method === 'POST') {
        return Promise.resolve(new Response(JSON.stringify({ city_id: 1, status: 'running', message: 'ok' }), { status: 200 }))
      }
      if (url.endsWith('/admin/import-jobs/1')) {
        return Promise.resolve(new Response(JSON.stringify({ ...job, status: 'running', current_step: 'running', can_run: false, can_cancel: true }), { status: 200 }))
      }
      if (url.includes('/admin/import-jobs')) {
        return Promise.resolve(new Response(JSON.stringify({ items: [job], total: 1, limit: 50, offset: 0 }), { status: 200 }))
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

  it('shows run button and triggers import_new', async () => {
    render(<MemoryRouter><AdminImportJobsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Алматы')).toBeTruthy())
    fireEvent.click(screen.getByText('Запустить сбор'))
    await waitFor(() => expect(screen.getByText('ok')).toBeTruthy())
  })
})
