// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { Mock } from 'vitest'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { adminGet, adminPost } from './adminApi'
import { AdminImportJobsPage } from './AdminImportJobsPage'

vi.mock('./adminApi', () => ({
  adminGet: vi.fn(),
  adminPost: vi.fn(),
}))

const queueIdle = {
  total: 1,
  active_total: 1,
  queued: 1,
  running: 0,
  stalled_running: 0,
  next_job_ids: [9],
  by_source: { admin_city_import: 1 },
}

const emptyImportJobs = { items: [], total: 0, limit: 50, offset: 0 }

const runningJob = {
  id: 'running-job',
  city_id: 301,
  city_slug: 'running-city',
  city_name: 'Running City',
  status: 'running',
  current_step: 'collecting_places',
  current_step_label: 'Собираем места',
  source: 'admin_city_import',
  places_total: 5,
  places_published: 0,
  places_unpublished: 5,
  pending_photos: 0,
  next_step: 'Ожидаем завершения сбора',
  failed_items: 0,
  job_id: 42,
  started_at: '2026-07-20T10:00:00Z',
  created_at: '2026-07-20T10:00:00Z',
  step_details: {},
}

const failedJob = {
  id: 'failed-job',
  city_id: 302,
  city_slug: 'failed-city',
  city_name: 'Failed City',
  status: 'failed',
  current_step: 'error',
  current_step_label: 'Ошибка',
  source: 'admin_city_import',
  places_total: 12,
  places_published: 0,
  places_unpublished: 12,
  pending_photos: 0,
  next_step: 'Разобрать ошибку импорта',
  failed_items: 1,
  job_id: 43,
  job_execution_failed: true,
  last_error: 'Не удалось получить данные OSM: timeout',
  started_at: '2026-07-20T09:00:00Z',
  finished_at: '2026-07-20T09:05:00Z',
  created_at: '2026-07-20T09:00:00Z',
  step_details: {},
}

const mockedAdminGet = adminGet as unknown as Mock
const mockedAdminPost = adminPost as unknown as Mock

const mockAdminGet = (queue = queueIdle, importJobs: unknown = emptyImportJobs) => {
  mockedAdminGet.mockImplementation((path: string) => {
    if (path === '/admin/import-queue') return Promise.resolve(queue)
    if (path.startsWith('/admin/import-jobs')) return Promise.resolve(importJobs)
    return Promise.reject(new Error(`Unexpected GET ${path}`))
  })
}

const renderPage = () => render(<MemoryRouter><AdminImportJobsPage /></MemoryRouter>)

describe('AdminImportJobsPage mobile card list', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAdminGet()
    mockedAdminPost.mockResolvedValue({ scheduled: true, limit: 1, queue: queueIdle })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders mobile cards with city name, job id, status, step, start time and duration', async () => {
    mockAdminGet(queueIdle, { items: [runningJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const card = await screen.findByTestId('mobile-import-job-card')
    expect(card.textContent).toContain('Running City')
    expect(card.textContent).toContain('#42')
    expect(card.textContent).toContain('Собираем места')
    expect(card.textContent).toContain('начало:')
    expect(card.textContent).toContain('длительность:')
    const badge = screen.getByTestId('mobile-import-job-status-badge')
    expect(badge.textContent).toBeTruthy()
  })

  it('shows the failure reason on a failed job mobile card', async () => {
    mockAdminGet(queueIdle, { items: [failedJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    await waitFor(() => expect(screen.getByTestId('mobile-import-job-failure-reason')).toBeTruthy())
    expect(screen.getByTestId('mobile-import-job-failure-reason').textContent).toContain('Не удалось получить данные OSM: timeout')
  })

  it('links the whole card to the existing diagnostic route for that job', async () => {
    mockAdminGet(queueIdle, { items: [runningJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const card = await screen.findByTestId('mobile-import-job-card')
    expect(card.tagName).toBe('A')
    expect(card.getAttribute('href')).toBe('/admin/imports/jobs/42/diagnostic')
  })

  it('keeps the desktop table present in the markup', async () => {
    mockAdminGet(queueIdle, { items: [runningJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    await waitFor(() => expect(screen.getByTestId('mobile-import-job-card')).toBeTruthy())
    expect(document.querySelector('.admin-import-table table')).toBeTruthy()
    expect(screen.getAllByText('Running City').length).toBeGreaterThanOrEqual(2)
  })

  it('renders the mobile card list without a table wrapper or horizontal-scroll container', async () => {
    mockAdminGet(queueIdle, { items: [runningJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const cardList = await screen.findByTestId('mobile-import-job-card')
    const mobileContainer = cardList.closest('.admin-import-mobile-card-list')
    expect(mobileContainer).toBeTruthy()
    expect(mobileContainer?.querySelector('table')).toBeNull()
    expect(mobileContainer?.closest('.admin-table-wrap')).toBeNull()
  })
})
