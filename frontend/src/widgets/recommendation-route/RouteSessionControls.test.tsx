/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { startActiveRouteSession, updateActiveRouteSession } from '../../api/recommendations/recommendationRoute.api'
import { RouteResultPanel } from './RouteResultPanel'

vi.mock('../../api/recommendations/recommendationRoute.api', () => ({
  sendRouteFeedback: vi.fn(),
  startActiveRouteSession: vi.fn(),
  updateActiveRouteSession: vi.fn(),
}))

vi.mock('../../shared/map/MapLibreMap', () => ({ MapLibreMap: () => <div>map</div> }))
vi.mock('../../shared/config/debug', () => ({ isDebugEnabled: () => false }))
vi.mock('./RouteInsights', () => ({ RouteInsights: () => null }))
vi.mock('./RouteWarnings', () => ({ RouteWarnings: () => null }))
vi.mock('./RouteDataNotes', () => ({ RouteDataNotes: () => null }))
vi.mock('./RoutePointList', () => ({ RoutePointList: () => null }))
vi.mock('./RouteCandidateOptions', () => ({ RouteCandidateOptions: () => null }))

const route: RecommendationRouteResponse = {
  route_id: 'route-1',
  status: 'ready',
  total_places: 2,
  total_minutes: 60,
  total_estimated_minutes: 60,
  estimated_distance: 1,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  warnings: [],
  points: [
    { place_id: '1', title: 'Первая', lat: 54, lng: 20, category: 'museum', visit_minutes: 30 },
    { place_id: '2', title: 'Вторая', lat: 54.1, lng: 20.1, category: 'park', visit_minutes: 30 },
  ],
  explanation: {},
}

const session = (status: ActiveRouteSession['status']): ActiveRouteSession => ({
  session_id: 7,
  route_id: route.route_id,
  ownership_token: 'owner-token',
  status,
  current_point_index: 0,
  current_place_id: '1',
  next_place_id: '2',
  point_completed_at: {},
  skipped_place_ids: [],
  points: [],
})

const renderPanel = (initialSession: ActiveRouteSession | null = null) => render(
  <RouteResultPanel
    route={route}
    loading={false}
    initialSession={initialSession}
    onAddCandidate={vi.fn()}
    onCorrect={vi.fn()}
  />,
)

describe('RouteResultPanel active session controls', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('does not reinterpret transition controls as start before a session exists', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: /начать маршрут/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /я на месте/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /пропустить/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^пауза$/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /завершить маршрут/i })).toBeDisabled()
  })

  it('exposes only valid active-session transitions and locks route edits', () => {
    renderPanel(session('active'))
    expect(screen.queryByRole('button', { name: /начать маршрут/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /пересобрать/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /добавить место/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /я на месте/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /пропустить/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /^пауза$/i })).toBeEnabled()
    expect(screen.queryByRole('button', { name: /продолжить/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /завершить маршрут/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /закрыть прогулку/i })).toBeEnabled()
  })

  it('uses resume rather than pause for a paused session', async () => {
    vi.mocked(updateActiveRouteSession).mockResolvedValue(session('active'))
    renderPanel(session('paused'))
    expect(screen.queryByRole('button', { name: /^пауза$/i })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /продолжить/i }))
    await waitFor(() => expect(updateActiveRouteSession).toHaveBeenCalledWith(expect.objectContaining({ status: 'paused' }), 'resume', undefined))
  })

  it('blocks terminal mutations and starts a new session without reclaiming the terminal token', async () => {
    const restarted = session('active')
    vi.mocked(startActiveRouteSession).mockResolvedValue(restarted)
    renderPanel(session('completed'))
    expect(screen.getByRole('button', { name: /я на месте/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /пропустить/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /завершить маршрут/i })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: /начать заново/i }))
    await waitFor(() => expect(startActiveRouteSession).toHaveBeenCalledWith(route))
  })
})
