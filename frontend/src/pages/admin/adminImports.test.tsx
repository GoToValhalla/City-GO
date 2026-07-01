/* @vitest-environment jsdom */
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminImportJobsPage } from './AdminImportJobsPage'
import { clearAdminSession } from './adminSession'

const baseCoverage = { places_total: 10, places_published: 8, places_unpublished: 2, without_address: 1, without_photo: 2, without_description: 3, address_coverage_pct: 90, photo_coverage_pct: 80, description_coverage_pct: 70, pending_photos: 0 }
const queueSummary = { total: 4, active_total: 2, queued: 1, running: 1, stalled_running: 0, oldest_queued_seconds: 12, next_job_ids: [9], by_source: { admin_city_import: 2 } }

const job = (overrides: Record<string, unknown> = {}) => ({
  id: 'city-import-1', city_id: 1, city_slug: 'almaty', city_name: 'Алматы', status: 'success',
  launch_status: 'review_required', current_step: 'ready_for_review', current_step_label: 'Завершён',
  source: 'admin_city_import', places_total: 10, places_published: 8, places_unpublished: 2,
  pending_photos: 0, next_step: 'Проверьте изменения', job_id: 9, scopes_total: 3,
  scopes_succeeded: 3, places_found: 10, places_saved: 8, total_items: 10, processed_items: 10,
  successful_items: 10, failed_items: 0, retry_count: 0, can_run: false, can_retry: true,
  can_cancel: false, can_publish: true, data_coverage: baseCoverage,
  step_details: { data_coverage: baseCoverage, change_summary: {}, admin_pipeline_contract: {} },
  ...overrides,
})

const runningJob = job({
  id: 'city-import-1', city_id: 1, city_slug: 'almaty', city_name: 'Алматы', status: 'running',
  launch_status: 'published', current_step: 'snapshot_refresh', current_step_label: 'Обновляем snapshot',
  can_retry: false, can_cancel: true, can_publish: false,
})
const completedQueuedJob = job({
  id: 'city-import-2', city_id: 2, city_slug: 'batumi', city_name: 'Батуми', status: 'success',
  launch_status: 'review_required', current_step: 'queued', current_step_label: 'Завершён', job_id: 10,
})
const completedSnapshotJob = job({
  id: 'city-import-3', city_id: 3, city_slug: 'kutaisi', city_name: 'Кутаиси', status: 'success',
  launch_status: 'review_required', current_step: 'snapshot_refresh', current_step_label: 'Завершён', job_id: 11,
})
const snapshotWithLatestPhoto = job({
  id: 'city-import-4', city_id: 4, city_slug: 'erevan', city_name: 'Ереван', status: 'success',
  launch_status: 'review_required', current_step: 'snapshot_ready', current_step_label: 'Snapshot готов',
  source: 'admin_snapshot_refresh', job_id: 12,
  step_details: {
    data_coverage: baseCoverage,
    change_summary: {},
    latest_photo_enrichment: { created: 0, scanned_places: 7, candidates_found: 0, provider_status: 'source_evidence_exhausted', errors: [] },
  },
})

const fetchUrl = (input: RequestInfo | URL) => input instanceof Request ? input.url : String(input)
const fetchCalls = () => (fetch as unknown as { mock: { calls: Array<[RequestInfo | URL, RequestInit?]> } }).mock.calls
const urls = () => fetchCalls().map(([input]) => fetchUrl(input))
const countCalls = (part: string) => urls().filter((url) => url.includes(part)).length
const jsonResponse = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }))
const renderPage = (initialEntry = '/admin/imports') => render(<MemoryRouter initialEntries={[initialEntry]}><AdminImportJobsPage /></MemoryRouter>)

const installFetch = ({
  items = [completedQueuedJob],
  details = {},
  queuePending = false,
  listFactory,
}: {
  items?: Array<Record<string, unknown>>
  details?: Record<number, Record<string, unknown>>
  queuePending?: boolean
  listFactory?: () => Array<Record<string, unknown>>
} = {}) => {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = fetchUrl(input)
    if (url.includes('/admin/import-queue')) {
      if (queuePending) return new Promise(() => undefined)
      return jsonResponse(queueSummary)
    }
    if (url.includes('/admin/import-jobs/') && init?.method === 'POST') return jsonResponse({ city_id: 1, status: 'queued', message: 'ok' })
    const detailMatch = url.match(/\/admin\/import-jobs\/(\d+)$/)
    if (detailMatch) {
      const cityId = Number(detailMatch[1])
      return jsonResponse(details[cityId] ?? items.find((item) => item.city_id === cityId) ?? {})
    }
    if (url.includes('/admin/import-jobs?limit=50')) {
      const nextItems = listFactory ? listFactory() : items
      return jsonResponse({ items: nextItems, total: nextItems.length, limit: 50, offset: 0 })
    }
    return jsonResponse({}, 404)
  }))
}

describe('AdminImportJobsPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('confirm', vi.fn(() => true))
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('renders queue, disables running actions and retries completed job_new', async () => {
    installFetch({ items: [runningJob, completedQueuedJob] })
    renderPage()
    await waitFor(() => expect(screen.getAllByText('Алматы').length).toBeGreaterThan(0))
    expect(screen.getByText(/В очереди:/)).toBeTruthy()
    expect(screen.getAllByText('Действия заблокированы: pipeline выполняется').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Обновить snapshot')[0].hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getAllByText('Повторить сбор')[0])
    await waitFor(() => expect(urls().some((url) => url.includes('/admin/import-jobs/2/retry'))).toBe(true))
    expect(urls().some((url) => url.includes('/admin/import-queue'))).toBe(true)
    expect(urls().every((url) => !url.includes('/admin/import-jobs/queue'))).toBe(true)
  })

  it('Import queue refresh button stays enabled while queue is loading', async () => {
    installFetch({ items: [completedQueuedJob], details: { 2: completedQueuedJob }, queuePending: true })
    renderPage('/admin/imports?city=batumi&job=10&detail=2')
    await screen.findByText('Батуми · запуск #10')

    const button = screen.getByRole('button', { name: 'Обновить очередь' })
    expect(button.hasAttribute('disabled')).toBe(false)
    expect(button.getAttribute('aria-busy')).toBe('true')

    const listCallsBefore = countCalls('/admin/import-jobs?limit=50')
    const detailCallsBefore = countCalls('/admin/import-jobs/2')
    fireEvent.click(button)

    await waitFor(() => expect(countCalls('/admin/import-queue')).toBeGreaterThanOrEqual(2))
    expect(countCalls('/admin/import-jobs?limit=50')).toBe(listCallsBefore)
    expect(countCalls('/admin/import-jobs/2')).toBe(detailCallsBefore)
    expect(screen.getByText('Батуми · запуск #10')).toBeTruthy()
  })

  it('Import queue refresh does not reload import job list', async () => {
    installFetch({ items: [completedQueuedJob] })
    renderPage('/admin/imports?city=batumi&job=10')
    await screen.findByText('Батуми · запуск #10')
    const listCallsBefore = countCalls('/admin/import-jobs?limit=50')

    fireEvent.click(screen.getByRole('button', { name: 'Обновить очередь' }))

    await waitFor(() => expect(countCalls('/admin/import-queue')).toBeGreaterThanOrEqual(2))
    expect(countCalls('/admin/import-jobs?limit=50')).toBe(listCallsBefore)
    expect(screen.getByText('Батуми · запуск #10')).toBeTruthy()
  })

  it('Completed job with legacy current_step queued is not active', async () => {
    installFetch({ items: [completedQueuedJob, completedSnapshotJob] })
    renderPage()
    await waitFor(() => expect(screen.getAllByText('Батуми').length).toBeGreaterThan(0))

    expect(screen.queryByText('pipeline выполняется')).toBeNull()
    for (const label of ['Добрать фото', 'Добрать адреса', 'Обновить snapshot', 'Повторить сбор']) {
      const buttons = screen.getAllByRole('button', { name: label })
      expect(buttons.length).toBeGreaterThan(0)
      expect(buttons.every((button) => !button.hasAttribute('disabled'))).toBe(true)
    }
  })

  it('loads details and keeps them after queue refresh', async () => {
    installFetch({ items: [snapshotWithLatestPhoto], details: { 4: snapshotWithLatestPhoto } })
    renderPage()
    await waitFor(() => expect(screen.getAllByText('Ереван').length).toBeGreaterThan(0))

    fireEvent.click(screen.getByRole('button', { name: '#12 →' }))

    await screen.findByText('Ереван · запуск #12')
    await screen.findByText('Результат добора фото')
    expect(screen.getByText(/source_evidence_exhausted/)).toBeTruthy()
    expect(countCalls('/admin/import-jobs/4')).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Обновить очередь' }))

    await waitFor(() => expect(countCalls('/admin/import-queue')).toBeGreaterThanOrEqual(2))
    expect(screen.getByText('Ереван · запуск #12')).toBeTruthy()
    expect(screen.getByText(/source_evidence_exhausted/)).toBeTruthy()
  })

  it('Snapshot job does not hide latest photo enrichment result', async () => {
    const fallbackPhotoJob = {
      ...snapshotWithLatestPhoto,
      city_id: 5,
      city_slug: 'tbilisi',
      city_name: 'Тбилиси',
      job_id: 13,
      id: 'city-import-5',
      step_details: {
        data_coverage: baseCoverage,
        change_summary: {},
        photo_enrichment: { created: 0, scanned_places: 5, candidates_found: 0, provider_status: 'no_candidates', errors: [] },
      },
    }
    installFetch({ items: [fallbackPhotoJob], details: { 5: fallbackPhotoJob } })
    renderPage()
    await waitFor(() => expect(screen.getAllByText('Тбилиси').length).toBeGreaterThan(0))

    fireEvent.click(screen.getByRole('button', { name: '#13 →' }))

    await screen.findByText('Результат добора фото')
    expect(screen.getByText(/no_candidates/)).toBeTruthy()
  })

  it('Photo blocker warning is shown only when no pending photo candidates exist', async () => {
    const blockedJob = job({
      city_id: 6,
      city_slug: 'photo-blocked',
      city_name: 'Фото-блокер',
      job_id: 14,
      id: 'city-import-6',
      data_coverage: { ...baseCoverage, without_photo: 4, pending_photos: 0 },
      step_details: { data_coverage: { ...baseCoverage, without_photo: 4, pending_photos: 0 }, change_summary: {}, admin_pipeline_contract: {} },
    })
    const pendingJob = job({
      city_id: 7,
      city_slug: 'photo-pending',
      city_name: 'Фото-кандидаты',
      job_id: 15,
      id: 'city-import-7',
      data_coverage: { ...baseCoverage, without_photo: 4, pending_photos: 2 },
      step_details: { data_coverage: { ...baseCoverage, without_photo: 4, pending_photos: 2 }, change_summary: {}, admin_pipeline_contract: {} },
    })
    installFetch({ items: [blockedJob, pendingJob], details: { 6: blockedJob, 7: pendingJob } })
    renderPage()
    await waitFor(() => expect(screen.getAllByText('Фото-блокер').length).toBeGreaterThan(0))

    fireEvent.click(screen.getByRole('button', { name: '#14 →' }))
    await screen.findByText(/Фото остаются блокером/)

    fireEvent.click(screen.getByRole('button', { name: '#15 →' }))
    await screen.findByText('Фото-кандидаты · запуск #15')
    expect(screen.queryByText(/Фото остаются блокером/)).toBeNull()
  })

  it('polling runs only for queued or running jobs and stops after success', async () => {
    vi.useFakeTimers()
    let listRequests = 0
    installFetch({
      listFactory: () => {
        listRequests += 1
        return listRequests === 1 ? [runningJob] : [{ ...runningJob, status: 'success', current_step: 'queued', current_step_label: 'Завершён', can_retry: true, can_cancel: false }]
      },
    })
    renderPage()
    await waitFor(() => expect(listRequests).toBe(1))
    await waitFor(() => expect(screen.getAllByText('Алматы').length).toBeGreaterThan(0))

    await act(async () => {
      vi.advanceTimersByTime(7000)
      await Promise.resolve()
    })
    await waitFor(() => expect(listRequests).toBe(2))

    await act(async () => {
      vi.advanceTimersByTime(14000)
      await Promise.resolve()
    })
    expect(listRequests).toBe(2)
  })
})
