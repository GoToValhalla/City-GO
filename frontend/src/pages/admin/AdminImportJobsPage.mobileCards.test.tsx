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

const rawSqlErrorJob = {
  id: 'raw-sql-job',
  city_id: 303,
  city_slug: 'raw-sql-city',
  city_name: 'Raw SQL City',
  status: 'failed',
  current_step: 'error',
  current_step_label: 'Ошибка',
  source: 'admin_city_import',
  places_total: 3,
  places_published: 0,
  places_unpublished: 3,
  pending_photos: 0,
  next_step: 'Разобрать ошибку импорта',
  failed_items: 1,
  job_id: 44,
  job_execution_failed: true,
  last_error: 'Traceback (most recent call last):\n  File "app/services/import.py", line 42, in run\n    cursor.execute("SELECT * FROM places WHERE city_id = %s AND status = %s", (1, "active"))\nsqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedColumn) column "status" does not exist',
  started_at: '2026-07-20T08:00:00Z',
  finished_at: '2026-07-20T08:02:00Z',
  created_at: '2026-07-20T08:00:00Z',
  step_details: {},
}

const duplicatePhotoErrorJob = {
  id: 'duplicate-photo-job',
  city_id: 304,
  city_slug: 'duplicate-photo-city',
  city_name: 'Duplicate Photo City',
  status: 'failed',
  current_step: 'error',
  source: 'admin_photo_enrichment',
  places_total: 1,
  places_published: 0,
  places_unpublished: 1,
  pending_photos: 0,
  next_step: 'Разобрать ошибку добора фото',
  failed_items: 1,
  job_id: 45,
  job_execution_failed: true,
  import_error_summary: {
    failed_step: 'photo_enrichment',
    error_message: 'duplicate key value violates unique constraint "place_images_place_id_image_url_key"',
    job_id: 45,
    primary_error_kind: 'data_integrity',
    scope_errors: [{ error: 'duplicate key value violates unique constraint', kind: 'data_integrity', admin_hint: 'Ошибка связи review queue с import job. Повторите сбор после деплоя фикса.' }],
  },
  started_at: '2026-07-20T07:00:00Z',
  finished_at: '2026-07-20T07:01:00Z',
  created_at: '2026-07-20T07:00:00Z',
  step_details: {},
}

const fkErrorJob = {
  id: 'fk-error-job',
  city_id: 305,
  city_slug: 'fk-error-city',
  city_name: 'FK Error City',
  status: 'failed',
  current_step: 'error',
  source: 'admin_city_import',
  places_total: 2,
  places_published: 0,
  places_unpublished: 2,
  pending_photos: 0,
  next_step: 'Разобрать ошибку импорта',
  failed_items: 1,
  job_id: 46,
  job_execution_failed: true,
  last_error: 'psycopg.errors.ForeignKeyViolation: insert or update on table "review_queue_items" violates foreign key constraint "review_queue_items_job_id_fkey"',
  started_at: '2026-07-20T06:00:00Z',
  finished_at: '2026-07-20T06:01:00Z',
  created_at: '2026-07-20T06:00:00Z',
  step_details: {},
}

const queuedJobWithStaleError = {
  id: 'queued-stale-error-job',
  city_id: 306,
  city_slug: 'queued-stale-city',
  city_name: 'Queued Stale City',
  status: 'queued',
  current_step: 'queued',
  source: 'admin_city_import',
  places_total: 0,
  places_published: 0,
  places_unpublished: 0,
  pending_photos: 0,
  next_step: 'Ожидаем запуск worker',
  failed_items: 0,
  job_id: 47,
  // Stale flags left over from the previous run's failure — the current
  // status is queued, so the badge must not say "Ошибка".
  is_stalled: true,
  last_error: 'previous run failed: connection reset',
  created_at: '2026-07-19T00:00:00Z',
  step_details: {},
}

const inactiveJobWithoutFinishedAt = {
  id: 'inactive-no-finish-job',
  city_id: 307,
  city_slug: 'inactive-no-finish-city',
  city_name: 'Inactive No Finish City',
  status: 'stalled',
  current_step: 'error',
  source: 'admin_city_import',
  places_total: 0,
  places_published: 0,
  places_unpublished: 0,
  pending_photos: 0,
  next_step: 'Проверить зависшую задачу',
  failed_items: 0,
  job_id: 48,
  is_stalled: true,
  started_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
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

  it('is not a clickable container, and exposes a diagnostics link as an independent action', async () => {
    mockAdminGet(queueIdle, { items: [runningJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const card = await screen.findByTestId('mobile-import-job-card')
    expect(card.tagName).not.toBe('A')
    expect(card.getAttribute('href')).toBeNull()
    const diagnostic = screen.getByTestId('mobile-import-job-action-diagnostic')
    expect(diagnostic.tagName).toBe('A')
    expect(diagnostic.getAttribute('href')).toBe('/admin/imports/jobs/42/diagnostic')
  })

  it('exposes independent Queue/Retry/Diagnostics/Refresh actions on the mobile card', async () => {
    mockAdminGet(queueIdle, { items: [{ ...failedJob, can_run: true, can_retry: true }], total: 1, limit: 50, offset: 0 })

    renderPage()

    await screen.findByTestId('mobile-import-job-card')
    expect(screen.getByTestId('mobile-import-job-action-run')).toBeTruthy()
    expect(screen.getByTestId('mobile-import-job-action-retry')).toBeTruthy()
    expect(screen.getByTestId('mobile-import-job-action-diagnostic')).toBeTruthy()
    expect(screen.getByTestId('mobile-import-job-action-refresh')).toBeTruthy()
  })

  const mockAdminGetWithDetail = (items: unknown[], detail: unknown) => {
    mockedAdminGet.mockImplementation((path: string) => {
      if (path === '/admin/import-queue') return Promise.resolve(queueIdle)
      if (/^\/admin\/import-jobs\/\d+$/.test(path)) return Promise.resolve(detail)
      if (path.startsWith('/admin/import-jobs')) return Promise.resolve({ items, total: items.length, limit: 50, offset: 0 })
      return Promise.reject(new Error(`Unexpected GET ${path}`))
    })
  }

  it('Queue action posts to the existing /run endpoint for that city only', async () => {
    const job = { ...failedJob, can_run: true, can_retry: false }
    mockAdminGetWithDetail([job], job)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderPage()

    const runButton = await screen.findByTestId('mobile-import-job-action-run')
    runButton.click()

    await waitFor(() => expect(mockedAdminPost).toHaveBeenCalledWith('/admin/import-jobs/302/run', {}))
  })

  it('Retry action posts to the existing /retry endpoint for that city only', async () => {
    const job = { ...failedJob, can_run: false, can_retry: true }
    mockAdminGetWithDetail([job], job)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderPage()

    const retryButton = await screen.findByTestId('mobile-import-job-action-retry')
    retryButton.click()

    await waitFor(() => expect(mockedAdminPost).toHaveBeenCalledWith('/admin/import-jobs/302/retry', {}))
  })

  it('Refresh action reloads only this city status via GET /admin/import-jobs/{city_id}, not the worker queue', async () => {
    mockAdminGetWithDetail([failedJob], failedJob)

    renderPage()

    const refreshButton = await screen.findByTestId('mobile-import-job-action-refresh')
    mockedAdminGet.mockClear()
    refreshButton.click()

    await waitFor(() => expect(mockedAdminGet).toHaveBeenCalledWith('/admin/import-jobs/302', { cache: false }))
    expect(mockedAdminGet).not.toHaveBeenCalledWith('/admin/import-queue', expect.anything())
    expect(mockedAdminPost).not.toHaveBeenCalled()
  })

  it('Queue and Retry never call a worker-run endpoint directly', async () => {
    const job = { ...failedJob, can_run: true, can_retry: true }
    mockAdminGetWithDetail([job], job)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderPage()

    const runButton = await screen.findByTestId('mobile-import-job-action-run')
    runButton.click()
    await waitFor(() => expect(mockedAdminPost).toHaveBeenCalled())
    const retryButton = screen.getByTestId('mobile-import-job-action-retry')
    retryButton.click()
    await waitFor(() => expect(mockedAdminPost).toHaveBeenCalledTimes(2))

    const calledPaths = mockedAdminPost.mock.calls.map((call) => call[0])
    expect(calledPaths).not.toContain('/admin/import-queue/run-once')
  })

  it('does not show Queue/Retry for an active (queued/running) job', async () => {
    mockAdminGet(queueIdle, { items: [runningJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    await screen.findByTestId('mobile-import-job-card')
    expect(screen.queryByTestId('mobile-import-job-action-run')).toBeNull()
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

  it('never renders raw SQL/traceback text in the mobile card failure summary', async () => {
    mockAdminGet(queueIdle, { items: [rawSqlErrorJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const reason = await screen.findByTestId('mobile-import-job-failure-reason')
    expect(reason.textContent).not.toContain('Traceback')
    expect(reason.textContent).not.toContain('SELECT')
    expect(reason.textContent).not.toContain('sqlalchemy.exc')
    expect(reason.textContent).not.toContain('File "')
    expect(reason.textContent).toBe('Импорт завершился с ошибкой')
  })

  it('turns a duplicate-photo constraint error into a short summary', async () => {
    mockAdminGet(queueIdle, { items: [duplicatePhotoErrorJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const reason = await screen.findByTestId('mobile-import-job-failure-reason')
    expect(reason.textContent).not.toContain('duplicate key value violates unique constraint')
    expect(reason.textContent).toBe('Ошибка связи review queue с import job. Повторите сбор после деплоя фикса.')
  })

  it('turns a foreign key violation error into a short summary', async () => {
    mockAdminGet(queueIdle, { items: [fkErrorJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const reason = await screen.findByTestId('mobile-import-job-failure-reason')
    expect(reason.textContent).not.toContain('ForeignKeyViolation')
    expect(reason.textContent).not.toContain('review_queue_items_job_id_fkey')
    expect(reason.textContent).toBe('Импорт завершился с ошибкой')
  })

  it('does not show a generic error badge for a queued job carrying a stale error from a previous run', async () => {
    mockAdminGet(queueIdle, { items: [queuedJobWithStaleError], total: 1, limit: 50, offset: 0 })

    renderPage()

    const badge = await screen.findByTestId('mobile-import-job-status-badge')
    expect(badge.textContent).toBe('В очереди')
    expect(screen.queryByTestId('mobile-import-job-failure-reason')).toBeNull()
  })

  it('hides duration for an inactive job that never recorded finished_at', async () => {
    mockAdminGet(queueIdle, { items: [inactiveJobWithoutFinishedAt], total: 1, limit: 50, offset: 0 })

    renderPage()

    const card = await screen.findByTestId('mobile-import-job-card')
    expect(card.textContent).not.toContain('длительность:')
  })

  it('shows duration for a running job with started_at (no finished_at yet)', async () => {
    mockAdminGet(queueIdle, { items: [runningJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const card = await screen.findByTestId('mobile-import-job-card')
    expect(card.textContent).toContain('длительность:')
  })

  it('shows duration for a completed job with both started_at and finished_at', async () => {
    mockAdminGet(queueIdle, { items: [failedJob], total: 1, limit: 50, offset: 0 })

    renderPage()

    const card = await screen.findByTestId('mobile-import-job-card')
    expect(card.textContent).toContain('длительность: 5 мин')
  })

  it('lets the current queued status win over a stale failed-looking error payload', async () => {
    mockAdminGet(queueIdle, { items: [queuedJobWithStaleError], total: 1, limit: 50, offset: 0 })

    renderPage()

    const badge = await screen.findByTestId('mobile-import-job-status-badge')
    expect(badge.textContent).not.toBe('Ошибка')
    const card = screen.getByTestId('mobile-import-job-card')
    expect(card.textContent).not.toContain('connection reset')
  })
})
