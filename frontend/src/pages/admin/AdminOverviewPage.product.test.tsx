/* @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminOverviewPage } from './AdminOverviewPage'
import { clearAdminSession } from './adminSession'

const forbiddenTerms = [
  'published/catalog',
  'route policy',
  'canonical category',
  'taxonomy',
  'enrichment/policy',
  'verification backlog',
  'critical confidence',
  'is_route_eligible',
]

const apiResponse = {
  critical: [],
  operations: [],
  recent_audit_count: 0,
  data_quality: [
    {
      code: 'route_blockers',
      title: 'Проблемы маршрутов',
      count: 12,
      severity: 'yellow',
      link_path: '/admin/places?preset=route_blockers',
      hint: 'Published/catalog places, которые не проходят route policy.',
      action_label: 'Открыть проблемы',
      queue_type: 'route_blocker',
      primary_action: 'open_queue',
      short_hint: 'Эти места сейчас не попадут в маршруты.',
      sample_endpoint: '/admin/places/search?preset=route_blockers',
      owner: 'data',
      is_human_actionable: true,
      mobile_priority: 'high',
    },
  ],
}
const backlogResponse = {
  generated_at: '2026-07-04T00:00:00Z',
  summary: {
    unique_problem_places: 10,
    total_problem_signals: 24,
    route_blocker_places: 3,
    auto_fixable_places: 8,
    manual_places: 2,
    verification_backlog_places: 5,
    content_gap_places: 6,
  },
  queues: [
    {
      code: 'manual_review',
      title: 'Очередь разбора',
      total_count: 12,
      unique_places_count: 12,
      auto_fixable_count: 8,
      manual_count: 2,
      overlap_count: 4,
      recommended_action: 'Разобрать по причинам',
      reasons: [
        { code: 'legacy_needs_review', title: 'Старые элементы проверки', count: 8, auto_fixable: true, manual_required: false },
        { code: 'overlaps_with_verification', title: 'Пересекается с автопроверкой', count: 4, auto_fixable: true, manual_required: false },
      ],
    },
    {
      code: 'needs_verification',
      title: 'Автоперепроверка',
      total_count: 5,
      unique_places_count: 5,
      auto_fixable_count: 5,
      manual_count: 0,
      overlap_count: 1,
      recommended_action: 'Запустить автоматическую проверку данных.',
      reasons: [
        { code: 'needs_recheck', title: 'Нужна повторная проверка', count: 3, auto_fixable: true, manual_required: false },
      ],
    },
  ],
  overlaps: [{ left: 'manual_review', right: 'needs_verification', count: 4 }],
}
const reductionPlanResponse = {
  generated_at: '2026-07-04T00:00:00Z',
  summary: {
    total_auto_fixable: 8,
    manual_review_reclassifiable: 4,
    content_enrichment_queueable: 6,
  },
  queues: [],
  actions: [
    {
      code: 'exclude_service_places_from_routes',
      title: 'Убрать сервисные точки из маршрутов',
      description: 'Оставляет места опубликованными, но выключает их из маршрутов.',
      expected_effect: 'Сервисные места перестают попадать в прогулочные маршруты.',
      enabled: true,
      affected_count: 3,
      max_batch_size: 500,
      risk_level: 'safe',
      disabled_reason: null,
      dry_run_endpoint: '/admin/overview/backlog-reduction/dry-run',
      apply_endpoint: '/admin/overview/backlog-reduction/apply',
      requires_confirmation: true,
      owner: 'data',
      queue_code: 'route_excluded',
      reason_codes: [],
      visible: true,
    },
    {
      code: 'recompute_low_confidence',
      title: 'Пересчитать низкую уверенность',
      description: 'Нет безопасного правила пересчёта для всех источников.',
      expected_effect: 'Будет включено после появления правил пересчёта.',
      enabled: false,
      disabled_reason: 'Нет безопасного локального правила пересчёта без источников.',
      affected_count: 0,
      max_batch_size: 500,
      risk_level: 'safe',
      dry_run_endpoint: '/admin/overview/backlog-reduction/dry-run',
      apply_endpoint: '/admin/overview/backlog-reduction/apply',
      requires_confirmation: true,
      owner: 'automation',
      queue_code: 'low_confidence',
      reason_codes: [],
      visible: true,
    },
  ],
}
const reductionResult = {
  action_code: 'exclude_service_places_from_routes',
  status: 'planned',
  dry_run: true,
  affected_count: 3,
  changed_count: 3,
  skipped_count: 0,
  failed_count: 0,
  queued_count: 0,
  message: 'Пробный запуск: Убрать сервисные точки из маршрутов.',
}

const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

describe('AdminOverviewPage product contract', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_ADMIN_API_TOKEN', 'test-admin-token')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/admin/overview/backlog-reduction-plan')) return response(reductionPlanResponse)
      if (url.includes('/admin/overview/backlog-reduction/dry-run')) return response(reductionResult)
      if (url.includes('/admin/overview/backlog-reduction/apply')) return response({ ...reductionResult, dry_run: false, status: 'applied' })
      if (url.includes('/admin/overview/backlog-breakdown')) return response(backlogResponse)
      if (url.includes('/admin/overview')) return response(apiResponse)
      if (init?.method === 'POST') return response({})
      return response({})
    }))
  })

  afterEach(() => {
    cleanup()
    clearAdminSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('renders operator cards without technical copy_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Проблемы маршрутов')).toBeTruthy())

    const text = document.body.textContent?.toLowerCase() ?? ''
    forbiddenTerms.forEach((term) => expect(text.includes(term)).toBe(false))
    expect(screen.getByText('Эти места сейчас не попадут в маршруты.')).toBeTruthy()
    expect(screen.queryByText(/Published\/catalog/i)).toBeNull()
  })

  it('card click applies expected filter_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByLabelText('Проблемы маршрутов: 12. Открыть проблемы')).toBeTruthy())

    expect(screen.getByLabelText('Проблемы маршрутов: 12. Открыть проблемы').getAttribute('href')).toBe('/admin/places?preset=route_blockers')
  })

  it('mobile overview cards use compact short hints_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    const hint = await screen.findByTestId('overview-card-hint-route_blockers')

    expect(hint.textContent).toBe('Эти места сейчас не попадут в маршруты.')
    expect((hint.textContent ?? '').length).toBeLessThanOrEqual(90)
  })

  it('renders backlog summary without technical copy_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByTestId('admin-backlog-breakdown')).toBeTruthy())

    expect(screen.getByText('Проблемных мест')).toBeTruthy()
    expect(screen.getByText('Сигналов качества')).toBeTruthy()
    expect(screen.getByText('10')).toBeTruthy()
    expect(screen.getByText('24')).toBeTruthy()
    const text = document.body.textContent?.toLowerCase() ?? ''
    forbiddenTerms.forEach((term) => expect(text.includes(term)).toBe(false))
  })

  it('renders queue reason titles in Russian and hides snake case codes_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Очередь разбора')).toBeTruthy())

    expect(screen.getByText(/Старые элементы проверки: 8/)).toBeTruthy()
    expect(screen.getByText(/Пересекается с автопроверкой: 4/)).toBeTruthy()
    expect((document.body.textContent ?? '').includes('legacy_needs_review')).toBe(false)
    expect((document.body.textContent ?? '').includes('overlaps_with_verification')).toBe(false)
  })

  it('shows manual and auto split for large queues_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    const row = await screen.findByTestId('backlog-queue-manual_review')

    expect(row.textContent).toContain('12')
    expect(row.textContent).toContain('8')
    expect(row.textContent).toContain('2')
  })

  it('renders backlog reduction plan without showing action codes_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getByTestId('admin-backlog-reduction')).toBeTruthy())

    expect(screen.getByText('План уменьшения очередей')).toBeTruthy()
    expect(screen.getByText('Убрать сервисные точки из маршрутов')).toBeTruthy()
    expect(screen.getByText('Нет безопасного локального правила пересчёта без источников.')).toBeTruthy()
    expect((document.body.textContent ?? '').includes('exclude_service_places_from_routes')).toBe(false)
  })

  it('runs dry run before enabling safe apply_new', async () => {
    const fetchMock = vi.mocked(fetch)
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await screen.findByText('Пробный запуск')
    expect((screen.getByText('Применить безопасно') as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByText('Пробный запуск'))

    await screen.findByTestId('reduction-result')
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/admin/overview/backlog-reduction/dry-run'), expect.objectContaining({ method: 'POST' }))
    expect(screen.getByText(/Изменено: 3/)).toBeTruthy()
  })

  it('requires confirmation before apply_new', async () => {
    render(<MemoryRouter><AdminOverviewPage /></MemoryRouter>)

    await screen.findByText('Пробный запуск')
    fireEvent.click(screen.getByText('Пробный запуск'))
    await screen.findByTestId('reduction-result')
    fireEvent.change(screen.getByPlaceholderText('Введите APPLY'), { target: { value: 'APPLY' } })

    expect((screen.getByText('Применить безопасно') as HTMLButtonElement).disabled).toBe(false)
  })
})
