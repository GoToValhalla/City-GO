/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import * as recommendationApi from '../../api/recommendations/recommendationRoute.api'
import { RouteResultPanel } from './RouteResultPanel'

vi.mock('../../shared/map/MapLibreMap', () => ({
  MapLibreMap: () => <div data-testid="map-shell" />,
}))

vi.mock('../../shared/config/debug', () => ({
  isDebugEnabled: () => false,
}))

vi.mock('../../api/recommendations/recommendationRoute.api', async () => {
  const actual = await vi.importActual<typeof import('../../api/recommendations/recommendationRoute.api')>('../../api/recommendations/recommendationRoute.api')
  return {
    ApiRequestError: actual.ApiRequestError,
    sendRouteFeedback: vi.fn(),
    startActiveRouteSession: vi.fn(),
    updateActiveRouteSession: vi.fn(),
  }
})

describe('route result panel smoke', () => {
  afterEach(() => cleanup())

  it('keeps route result test target active', () => {
    expect(1 + 1).toBe(2)
  })

  it('shows weak partial explanation and hides raw technical warning codes_new', () => {
    render(
      <RouteResultPanel
        route={route()}
        loading={false}
        onAddCandidate={vi.fn()}
        onCorrect={vi.fn()}
        onMovePoint={vi.fn()}
        onRemovePoint={vi.fn()}
        onReplacePoint={vi.fn()}
      />,
    )

    expect(screen.getByText(/Маршрут частично готов/)).toBeTruthy()
    expect(screen.getAllByText(/Маршрут слабый/).length).toBeGreaterThan(0)
    expect(screen.getByText('Маршрут пока короткий из-за качества доступных данных.')).toBeTruthy()
    expect(screen.queryByText('route_short_due_to_low_place_density')).toBeNull()
    expect(screen.getByRole('button', { name: /Начать маршрут/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Сообщить о проблеме' })).toBeTruthy()
    expect(screen.queryByText('Техническая диагностика')).toBeNull()
  })
})

const route = (): RecommendationRouteResponse => ({
  route_id: 'citygo171',
  status: 'partial_route',
  partial_reason: 'route_short_due_to_low_place_density',
  total_places: 1,
  total_minutes: 65,
  total_estimated_minutes: 65,
  estimated_distance: 1.2,
  total_walk_distance_meters: 1200,
  has_warnings: true,
  warning_count: 1,
  places_with_warnings: [],
  quality_score: 0.42,
  quality_status: 'weak',
  warnings: ['route_short_due_to_low_place_density'],
  user_warnings: [],
  points: [{
    place_id: '1',
    title: 'Парк',
    category: 'park',
    address: 'адрес уточняется',
    lat: 40.1,
    lng: 44.1,
    visit_minutes: 35,
    estimated_walk_minutes: 10,
  }],
  candidate_options: [],
  explanation: {
    summary: 'Короткий маршрут',
    points: [{ place_id: '1', reason: 'safe_candidate' }],
  },
})

const twoPointRoute = (overrides: Partial<RecommendationRouteResponse> = {}): RecommendationRouteResponse => ({
  route_id: 'citygo200',
  status: 'ready',
  total_places: 2,
  total_minutes: 90,
  total_estimated_minutes: 90,
  estimated_distance: 1.5,
  total_walk_distance_meters: 1500,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  quality_score: 0.8,
  quality_status: 'good',
  warnings: [],
  user_warnings: [],
  points: [
    { place_id: '1', title: 'Кафе', category: 'cafe', address: 'ул. Первая', lat: 40.1, lng: 44.1, visit_minutes: 30, estimated_walk_minutes: 5 },
    { place_id: '2', title: 'Музей', category: 'museum', address: 'ул. Вторая', lat: 40.2, lng: 44.2, visit_minutes: 40, estimated_walk_minutes: 8 },
  ],
  candidate_options: [],
  explanation: { summary: 'Хороший маршрут', points: [] },
  ...overrides,
})

const activeSession = (overrides: Partial<ActiveRouteSession> = {}): ActiveRouteSession => ({
  session_id: 501,
  route_id: 'citygo200',
  status: 'active',
  current_point_index: 0,
  current_place_id: '1',
  next_place_id: '2',
  point_completed_at: {},
  skipped_place_ids: [],
  points: [],
  ...overrides,
})

const renderPanel = (props: Partial<Parameters<typeof RouteResultPanel>[0]> = {}) => render(
  <RouteResultPanel
    route={twoPointRoute()}
    loading={false}
    onAddCandidate={vi.fn()}
    onCorrect={vi.fn()}
    onMovePoint={vi.fn()}
    onRemovePoint={vi.fn()}
    onReplacePoint={vi.fn()}
    {...props}
  />,
)

describe('active route session restoration', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('reopen during an active route shows the restored current point immediately, without calling the backend_new', () => {
    renderPanel({ initialSession: activeSession() })

    expect(screen.getByText(/Текущая точка: Кафе/)).toBeInTheDocument()
    expect(screen.getByText(/Дальше: Музей/)).toBeInTheDocument()
    expect(recommendationApi.startActiveRouteSession).not.toHaveBeenCalled()
    expect(recommendationApi.updateActiveRouteSession).not.toHaveBeenCalled()
  })

  it('restored progress (paused mid-route) is shown as paused, not reset to not-started_new', () => {
    renderPanel({ initialSession: activeSession({ status: 'paused' }) })

    expect(screen.getByText('Маршрут на паузе.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Продолжить/ })).toBeInTheDocument()
  })

  it('a completed restored route shows a completed message, not "not started"_new', () => {
    renderPanel({ initialSession: activeSession({ status: 'completed' }) })

    expect(screen.getByText('Маршрут завершён.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Я на месте/ })).toBeDisabled()
  })

  it('missing session (never started) shows the not-started state, not fabricated progress_new', () => {
    renderPanel({ initialSession: null })

    expect(screen.getByText('Маршрут ещё не начат.')).toBeInTheDocument()
  })

  it('an expired/invalid restored session surfaces a truthful recovery message and clears local session state_new', async () => {
    const onSessionChange = vi.fn()
    vi.mocked(recommendationApi.updateActiveRouteSession).mockRejectedValue(new recommendationApi.ApiRequestError({ status: 404, url: 'x', method: 'POST', responseBody: { detail: 'Route session not found' } }))
    renderPanel({ initialSession: activeSession(), onSessionChange })

    fireEvent.click(screen.getByRole('button', { name: /Я на месте/ }))

    await waitFor(() => expect(screen.getByText(/сессия больше не действует/)).toBeInTheDocument())
    expect(onSessionChange).toHaveBeenCalledWith(null)
    expect(screen.getByRole('button', { name: /Начать маршрут/ })).not.toBeDisabled()
  })

  it('rebuild/restart is possible after an invalid session by starting a fresh one_new', async () => {
    const freshSession = activeSession({ session_id: 999 })
    vi.mocked(recommendationApi.updateActiveRouteSession).mockRejectedValue(new recommendationApi.ApiRequestError({ status: 404, url: 'x', method: 'POST', responseBody: {} }))
    vi.mocked(recommendationApi.startActiveRouteSession).mockResolvedValue(freshSession)
    const onSessionChange = vi.fn()
    renderPanel({ initialSession: activeSession(), onSessionChange })

    fireEvent.click(screen.getByRole('button', { name: /Я на месте/ }))
    await waitFor(() => expect(screen.getByRole('button', { name: /Начать маршрут/ })).not.toBeDisabled())

    fireEvent.click(screen.getByRole('button', { name: /Начать маршрут/ }))

    await waitFor(() => expect(recommendationApi.startActiveRouteSession).toHaveBeenCalled())
    expect(onSessionChange).toHaveBeenCalledWith(freshSession)
  })

  it('does not fabricate progress locally: a network error (not a 4xx) keeps the prior session and shows a generic retry message_new', async () => {
    vi.mocked(recommendationApi.updateActiveRouteSession).mockRejectedValue(new Error('network down'))
    renderPanel({ initialSession: activeSession() })

    fireEvent.click(screen.getByRole('button', { name: /Пропустить/ }))

    await waitFor(() => expect(screen.getByText('Не удалось обновить прогулку.')).toBeInTheDocument())
    // Still shows the restored point — a transient error must not silently
    // clear or advance state that was never confirmed by the backend.
    expect(screen.getByText(/Текущая точка: Кафе/)).toBeInTheDocument()
  })
})

describe('defect #5/#6 regression: route start eligibility by status', () => {
  afterEach(() => cleanup())

  it('a ready route can start_new', () => {
    renderPanel({ route: twoPointRoute({ status: 'ready' }) })
    expect(screen.getByRole('button', { name: /Начать маршрут/ })).toBeInTheDocument()
  })

  it('a partial_route can still start -- pre-existing contract, not narrowed by the status fix_new', () => {
    renderPanel({ route: twoPointRoute({ status: 'partial_route' }) })
    expect(screen.getByRole('button', { name: /Начать маршрут/ })).toBeInTheDocument()
  })

  it('a missing status can never start -- the actual defect fix, no optimistic ready fallback_new', () => {
    renderPanel({ route: twoPointRoute({ status: undefined }) })
    expect(screen.queryByRole('button', { name: /Начать маршрут/ })).toBeNull()
    expect(screen.getByText(/Статус маршрута неизвестен/)).toBeInTheDocument()
  })

  it('an unrecognized/future status can never start_new', () => {
    renderPanel({ route: twoPointRoute({ status: 'some_future_status' }) })
    expect(screen.queryByRole('button', { name: /Начать маршрут/ })).toBeNull()
    expect(screen.getByText(/Статус маршрута неизвестен/)).toBeInTheDocument()
  })

  it('a failed route can never start_new', () => {
    renderPanel({ route: twoPointRoute({ status: 'failed' }) })
    expect(screen.queryByRole('button', { name: /Начать маршрут/ })).toBeNull()
  })
})
