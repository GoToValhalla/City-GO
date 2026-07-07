import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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

const mockedAdminGet = vi.mocked(adminGet)
const mockedAdminPost = vi.mocked(adminPost)

const mockAdminGet = (queue = queueIdle) => {
  mockedAdminGet.mockImplementation((path: string) => {
    if (path === '/admin/import-queue') return Promise.resolve(queue)
    if (path.startsWith('/admin/import-jobs')) return Promise.resolve(emptyImportJobs)
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
})
