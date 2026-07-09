// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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

const queueRunning = {
  ...queueIdle,
  queued: 0,
  running: 1,
  running_job_ids: [9],
  next_job_ids: [],
}

const emptyImportJobs = { items: [], total: 0, limit: 50, offset: 0 }

const failedStalledImportJobs = {
  items: [
    {
      id: 'failed-job',
      city_id: 101,
      city_slug: 'failed-city',
      city_name: 'Failed City',
      status: 'failed',
      source: 'admin_city_import',
      places_total: 12,
      places_published: 0,
      places_unpublished: 12,
      pending_photos: 0,
      next_step: 'Разобрать ошибку импорта',
      failed_items: 1,
      step_details: {},
    },
    {
      id: 'stalled-job',
      city_id: 102,
      city_slug: 'stalled-city',
      city_name: 'Stalled City',
      status: 'stalled',
      source: 'admin_city_import',
      places_total: 8,
      places_published: 0,
      places_unpublished: 8,
      pending_photos: 0,
      next_step: 'Проверить зависшую задачу',
      is_stalled: true,
      failed_items: 0,
      step_details: {},
    },
  ],
  total: 2,
  limit: 50,
  offset: 0,
}

const mockedAdminGet = adminGet as unknown as Mock
const mockedAdminPost = adminPost as unknown as Mock

const mockAdminGet = (queue = queueIdle, importJobs = emptyImportJobs, detail: unknown = null) => {
  mockedAdminGet.mockImplementation((path: string) => {
    if (path === '/admin/import-queue') return Promise.resolve(queue)
    if (/^\/admin\/import-jobs\/\d+$/.test(path) && detail) return Promise.resolve(detail)
    if (path.startsWith('/admin/import-jobs')) return Promise.resolve(importJobs)
    return Promise.reject(new Error(`Unexpected GET ${path}`))
  })
}

const renderPage = () => render(<MemoryRouter><AdminImportJobsPage /></MemoryRouter>)

describe('AdminImportJobsPage import-worker queue controls', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAdminGet()
    mockedAdminPost.mockResolvedValue({ scheduled: true, limit: 1, queue: queueIdle })
  })

  afterEach(() => {
    cleanup()
  })

  it('refreshes queue through GET without triggering run-once', async () => {
    renderPage()

    const refreshButton = await screen.findByRole('button', { name: 'Обновить очередь' })
    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect(mockedAdminGet).toHaveBeenCalledWith('/admin/import-queue', expect.objectContaining({ cache: false, timeoutMs: 8000 }))
    })
    expect(mockedAdminPost).not.toHaveBeenCalled()
  })

  it('starts worker only through POST run-once and refreshes queue after success', async () => {
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Запустить worker один раз' }))

    await waitFor(() => {
      expect(mockedAdminPost).toHaveBeenCalledWith('/admin/import-queue/run-once', {})
    })
    await waitFor(() => {
      expect(mockedAdminGet.mock.calls.filter(([path]) => path === '/admin/import-queue').length).toBeGreaterThanOrEqual(2)
    })
    expect(await screen.findByText('Worker запущен один раз. Лимит: 1.')).toBeTruthy()
  })

  it('disables run-once while worker is already running', async () => {
    mockAdminGet(queueRunning)

    renderPage()

    expect((await screen.findByRole('button', { name: 'Запустить worker один раз' })).hasAttribute('disabled')).toBe(true)
  })

  it('shows failed and stalled import statuses without masking them as empty or neutral states', async () => {
    mockAdminGet(queueIdle, failedStalledImportJobs)

    renderPage()

    expect((await screen.findAllByText('Failed City')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Stalled City')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Ошибка')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Завис')).length).toBeGreaterThan(0)
    expect(screen.queryByText('Задач по выбранному фильтру нет')).toBeNull()
  })

  it('shows a stalled background photo task without hiding the healthy main import status', async () => {
    const publishedCityImportJob = {
      id: 'kaliningrad-like',
      city_id: 201,
      city_slug: 'kaliningrad-like',
      city_name: 'Kaliningrad Like',
      status: 'success',
      status_group: 'published',
      source: 'admin_city_import',
      places_total: 3095,
      places_published: 1324,
      places_unpublished: 1771,
      pending_photos: 0,
      next_step: 'Город опубликован и доступен на сайте.',
      failed_items: 0,
      job_id: 4,
      step_details: {},
      background_task: {
        job_id: 5,
        source: 'admin_photo_enrichment',
        status: 'stalled',
        current_step: 'error',
        last_error: 'Import job stalled: no heartbeat before timeout',
        is_stalled: true,
        job_execution_failed: true,
      },
    }
    mockAdminGet(queueIdle, { items: [publishedCityImportJob], total: 1, limit: 50, offset: 0 }, publishedCityImportJob)

    renderPage()

    fireEvent.click((await screen.findAllByRole('button', { name: 'Детали' }))[0])

    const backgroundSection = await screen.findByTestId('background-task-status')
    expect(backgroundSection.textContent).toContain('фото')
    expect(backgroundSection.textContent).toContain('#5')
    expect(backgroundSection.textContent).toContain('stalled')
    expect(backgroundSection.textContent).toContain('Import job stalled: no heartbeat before timeout')
    expect(screen.queryByTestId('snapshot-missing-warning')).toBeNull()
  })

  it('explains why run-once was blocked instead of a generic "not started" message', async () => {
    mockedAdminPost.mockResolvedValue({
      scheduled: false,
      result: 'blocked',
      reason: 'manual in-web worker execution disabled; queued jobs are processed by import-worker',
      queue: queueIdle,
    })

    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Запустить worker один раз' }))

    const notice = await screen.findByText(/заблокирован намеренно/)
    expect(notice.textContent).toContain('import-worker')
  })
})
