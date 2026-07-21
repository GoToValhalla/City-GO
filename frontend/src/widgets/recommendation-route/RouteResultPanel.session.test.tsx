/* @vitest-environment jsdom */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { RouteResultPanel } from './RouteResultPanel'

vi.mock('../../shared/map/MapLibreMap', () => ({
  MapLibreMap: () => <div data-testid="route-map" />,
}))

vi.mock('../../api/recommendations/recommendationRoute.api', () => ({
  sendRouteFeedback: vi.fn(),
  startActiveRouteSession: vi.fn(),
  updateActiveRouteSession: vi.fn(),
}))

const route: RecommendationRouteResponse = {
  route_id: 'route-1',
  status: 'ready',
  total_places: 2,
  total_minutes: 60,
  total_estimated_minutes: 60,
  estimated_distance: 1.2,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  warnings: [],
  explanation: {},
  points: [
    { place_id: '1', position: 1, title: 'Первая точка', lat: 54.9, lng: 20.4, category: 'museum', visit_minutes: 30 },
    { place_id: '2', position: 2, title: 'Вторая точка', lat: 54.91, lng: 20.41, category: 'park', visit_minutes: 30 },
  ],
}

const session = (status: ActiveRouteSession['status']): ActiveRouteSession => ({
  session_id: 10,
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
    onMovePoint={vi.fn()}
    onRemovePoint={vi.fn()}
    onReplacePoint={vi.fn()}
  />,
)

describe('RouteResultPanel active session controls', () => {
  it('requires an explicit start before progress actions_new', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: /Начать маршрут/ })).toBeEnabled()
    expect(screen.getByRole('button', { name: /Я на месте/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Пропустить/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Пауза/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Завершить маршрут/ })).toBeDisabled()
  })

  it('locks route editing and enables valid active transitions_new', () => {
    renderPanel(session('active'))
    expect(screen.queryByRole('button', { name: /Начать маршрут/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Пересобрать/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Добавить место/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Я на месте/ })).toBeEnabled()
    expect(screen.getByRole('button', { name: /Пауза/ })).toBeEnabled()
    expect(screen.getByRole('button', { name: /Закрыть прогулку/ })).toBeEnabled()
  })

  it('offers resume instead of pause for a paused session_new', () => {
    renderPanel(session('paused'))
    expect(screen.getByRole('button', { name: /Продолжить/ })).toBeEnabled()
    expect(screen.queryByRole('button', { name: /^Пауза$/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Начать маршрут/ })).not.toBeInTheDocument()
  })
})
