/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { RouteResultPanel } from './RouteResultPanel'

vi.mock('../../shared/map/MapLibreMap', () => ({
  MapLibreMap: () => <div data-testid="map-shell" />,
}))

vi.mock('../../shared/config/debug', () => ({
  isDebugEnabled: () => false,
}))

vi.mock('../../api/recommendations/recommendationRoute.api', () => ({
  sendRouteFeedback: vi.fn(),
  startActiveRouteSession: vi.fn(),
  updateActiveRouteSession: vi.fn(),
}))

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
