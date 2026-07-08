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
const flushPromises = async () => { await Promise.resolve(); await Promise.resolve() }

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
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
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
    expect(screen.getAllByText(/source_evidence_exhausted/).length).toBeGreaterThan(0)
    expect(countCalls('/admin/import-jobs/4')).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Обновить очередь' }))

    await waitFor(() => expect(countCalls('/admin/import-queue')).toBeGreaterThanOrEqual(2))
    expect(screen.getByText('Ереван · запуск #12')).toBeTruthy()
    expect(screen.getAllByText(/source_evidence_exhausted/).length).toBeGreaterThan(0)
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
    expect(screen.getAllByText(/no_candidates/).length).toBeGreaterThan(0)
  })

  it('Photo blocker warning is shown only when no pending photo candidates exist', async () => {
    const blockedJob = job({
      city_id: 6,
      city_slug: 'photo-blocked',
      city_name: 'Фото-блокер',
      job_id: 14,
      id: 'city-import-6',
      data_coverage: { ...baseCoverage, without_photo: 4, pending_photos: 0 },
      photo_diagnostics: { admin_hint: 'Фото-блокер: источники не нашли кандидатов.', provider_status: 'no_candidates_from_provider', zero_result_reason: 'no_candidates_from_provider' },
      step_details: { data_coverage: { ...baseCoverage, without_photo: 4, pending_photos: 0 }, change_summary: {}, admin_pipeline_contract: {}, photo_diagnostics: { admin_hint: 'Фото-блокер: источники не нашли кандидатов.', provider_status: 'no_candidates_from_provider', zero_result_reason: 'no_candidates_from_provider' } },
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
    await screen.findByText('Фото-блокер · запуск #14')
    const hint = await screen.findByTestId('photo-blocker-hint')
    expect(hint.textContent).toMatch(/Фото-блокер|Фото остаются блокером/)
    const statusLine = screen.queryByTestId('photo-diagnostics-status')
    if (statusLine) expect(statusLine.textContent).toMatch(/no_candidates_from_provider/)

    fireEvent.click(screen.getByRole('button', { name: 'Показать все города' }))
    await waitFor(() => expect(screen.getByRole('button', { name: '#15 →' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: '#15 →' }))

    await screen.findByText('Фото-кандидаты · запуск #15')
    expect(screen.queryByText(/Фото остаются блокером/)).toBeNull()
  })

  it('shows failed import and published destination as separate states', async () => {
    const failedPublishedJob = job({
      city_id: 8,
      city_slug: 'zelenogradsk',
      city_name: 'Зеленоградск',
      job_id: 9,
      id: 'city-import-8',
      status: 'stalled',
      job_execution_status: 'stalled',
      destination_publication_status: 'published',
      launch_status: 'published',
      is_city_active: true,
      job_execution_failed: true,
      current_step: 'collecting_places',
      current_step_label: 'Завис',
      total_items: 466,
      processed_items: 466,
      failed_items: 1,
      import_error_summary: { failed_step: 'collecting_places', error_message: 'tourist_core: psycopg.errors.UndefinedTable' },
      snapshot_warning: { code: 'SNAPSHOT_MISSING', message: 'Snapshot не создан.' },
      import_execution_summary: { raw_collected: 0, raw_saved: 0, published: 26, scopes_total: 3, scopes_succeeded: 0, scopes_failed: 3 },
      step_details: { data_coverage: baseCoverage, change_summary: {}, admin_pipeline_contract: {}, snapshot_stale: true },
    })
    installFetch({ items: [failedPublishedJob], details: { 8: failedPublishedJob } })
    renderPage('/admin/imports?city=zelenogradsk&job=9')
    await screen.findByText('Зеленоградск · запуск #9')
    const statusBadges = screen.getAllByTestId('import-job-status-badge')
    expect(statusBadges.some((el) => el.textContent?.includes('Завис'))).toBe(true)
    expect(screen.getAllByTestId('destination-publication-badge').length).toBeGreaterThan(0)
    expect(screen.getByTestId('import-error-summary').textContent).toContain('psycopg')
    expect(screen.getByTestId('import-error-summary').textContent).toContain('Текущие ошибки')
    expect(screen.getByTestId('snapshot-missing-warning')).toBeTruthy()
    expect(screen.getByTestId('import-execution-summary').textContent).toContain('0')
    expect(screen.queryByText('100%')).toBeNull()
  })

  it('shows current run warnings separately from current errors', async () => {
    const warnedJob = job({
      city_id: 20, city_slug: 'warn-city', city_name: 'Ворн Сити', job_id: 20, id: 'city-import-20',
      status: 'success_with_warnings', job_execution_status: 'success_with_warnings', job_execution_failed: false,
      current_warnings: [{ step: 'finding_images', error: 'photo provider timeout' }],
    })
    installFetch({ items: [warnedJob], details: { 20: warnedJob } })
    renderPage('/admin/imports?city=warn-city&job=20')
    await screen.findByText('Ворн Сити · запуск #20')
    expect(screen.queryByTestId('import-error-summary')).toBeNull()
    const warningsSection = screen.getByTestId('current-run-warnings')
    expect(warningsSection.textContent).toContain('Предупреждения текущего запуска')
    expect(warningsSection.textContent).toContain('photo provider timeout')
    expect(screen.queryByTestId('stale-import-error')).toBeNull()
  })

  it('shows a stale saved error only under its own section, not as a current blocker', async () => {
    const staleJob = job({
      city_id: 21, city_slug: 'stale-city', city_name: 'Стейл Сити', job_id: 21, id: 'city-import-21',
      status: 'success', job_execution_status: 'success', job_execution_failed: false,
      stale_error: 'tourist_core: psycopg.errors.UndefinedColumn: column source_observations.source_license does not exist',
    })
    installFetch({ items: [staleJob], details: { 21: staleJob } })
    renderPage('/admin/imports?city=stale-city&job=21')
    await screen.findByText('Стейл Сити · запуск #21')
    expect(screen.queryByTestId('import-error-summary')).toBeNull()
    const staleSection = screen.getByTestId('stale-import-error')
    expect(staleSection.textContent).toContain('Старая сохранённая ошибка')
    expect(staleSection.textContent).toContain('UndefinedColumn')
  })

  it('renders no stale section when there is no stale error', async () => {
    const cleanJob = job({
      city_id: 22, city_slug: 'clean-city', city_name: 'Клин Сити', job_id: 22, id: 'city-import-22',
      status: 'success', job_execution_status: 'success', job_execution_failed: false,
    })
    installFetch({ items: [cleanJob], details: { 22: cleanJob } })
    renderPage('/admin/imports?city=clean-city&job=22')
    await screen.findByText('Клин Сити · запуск #22')
    expect(screen.queryByTestId('stale-import-error')).toBeNull()
    expect(screen.queryByTestId('current-run-warnings')).toBeNull()
    expect(screen.queryByTestId('import-error-summary')).toBeNull()
  })

  it('shows worker progress as alive with heartbeat details when not stale', async () => {
    const aliveJob = job({
      city_id: 23, city_slug: 'alive-city', city_name: 'Алайв Сити', job_id: 23, id: 'city-import-23',
      status: 'running', job_execution_status: 'running', job_execution_failed: false,
      worker_progress: {
        current_step: 'collecting_places',
        current_scope_code: 'tourist_core',
        current_scope_name: 'Туристическое ядро',
        running_for_seconds: 120,
        current_step_running_for_seconds: 60,
        is_stale: false,
        admin_hint: 'Воркер активен: шаг «collecting_places», скоуп «tourist_core».',
      },
    })
    installFetch({ items: [aliveJob], details: { 23: aliveJob } })
    renderPage('/admin/imports?city=alive-city&job=23')
    await screen.findByText('Алайв Сити · запуск #23')
    const progressSection = screen.getByTestId('worker-progress')
    expect(progressSection.textContent).toContain('Воркер активен')
    expect(progressSection.textContent).toContain('tourist_core')
    expect(progressSection.textContent).not.toContain('возможен стопор')
  })

  it('shows worker progress as stale when heartbeat is older than the threshold', async () => {
    const staleWorkerJob = job({
      city_id: 24, city_slug: 'stale-worker-city', city_name: 'Стейл Воркер Сити', job_id: 24, id: 'city-import-24',
      status: 'running', job_execution_status: 'running', job_execution_failed: false,
      worker_progress: {
        current_step: 'collecting_places',
        current_scope_code: null,
        running_for_seconds: 6300,
        current_step_running_for_seconds: 6300,
        is_stale: true,
        admin_hint: 'Воркер не обновлял прогресс дольше порога — возможен стопор, проверьте логи backend.',
      },
    })
    installFetch({ items: [staleWorkerJob], details: { 24: staleWorkerJob } })
    renderPage('/admin/imports?city=stale-worker-city&job=24')
    await screen.findByText('Стейл Воркер Сити · запуск #24')
    const progressSection = screen.getByTestId('worker-progress')
    expect(progressSection.textContent).toContain('возможен стопор')
  })

  it('renders no worker progress section when the job has finished', async () => {
    const finishedJob = job({
      city_id: 25, city_slug: 'finished-city', city_name: 'Финишед Сити', job_id: 25, id: 'city-import-25',
      status: 'success', job_execution_status: 'success', job_execution_failed: false,
      worker_progress: null,
    })
    installFetch({ items: [finishedJob], details: { 25: finishedJob } })
    renderPage('/admin/imports?city=finished-city&job=25')
    await screen.findByText('Финишед Сити · запуск #25')
    expect(screen.queryByTestId('worker-progress')).toBeNull()
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

    await act(async () => { await flushPromises() })
    expect(listRequests).toBe(1)
    expect(screen.getAllByText('Алматы').length).toBeGreaterThan(0)

    await act(async () => {
      vi.advanceTimersByTime(7000)
      await flushPromises()
    })
    expect(listRequests).toBe(2)

    await act(async () => {
      vi.advanceTimersByTime(14000)
      await flushPromises()
    })
    expect(listRequests).toBe(2)
  })
})
