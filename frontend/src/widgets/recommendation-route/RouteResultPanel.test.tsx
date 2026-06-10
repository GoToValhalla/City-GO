/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RouteResultPanel } from './RouteResultPanel'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

const route: RecommendationRouteResponse = {
  route_id: 'r1',
  status: 'ready',
  total_places: 1,
  total_minutes: 90,
  total_estimated_minutes: 90,
  estimated_distance: 1.4,
  has_warnings: true,
  warning_count: 1,
  places_with_warnings: ['1'],
  quality_score: 0.83,
  total_walk_distance_meters: 1400,
  time_breakdown: { walk_time_minutes: 12, visit_time_minutes: 60, budget_utilization: 0.8 },
  category_distribution: { walk: 1 },
  warnings: [],
  user_warnings: [{
    type: 'unknown_hours',
    severity: 'info',
    user_message: 'Часы указаны приблизительно.',
    affected_place_ids: ['1'],
    action_hint: 'Уточните перед визитом.',
  }],
  points: [{
    place_id: '1',
    title: 'Променад',
    address: 'Набережная',
    image_url: 'https://example.com/public-route-photo.jpg',
    lat: 54.96,
    lng: 20.48,
    category: 'walk',
    visit_minutes: 45,
  }],
  explanation: {
    summary: 'Прогулка у моря',
    points: [{ place_id: '1', reason: 'Подходит под интерес прогулка' }],
  },
}

describe('RouteResultPanel', () => {
  afterEach(() => cleanup())

  it('renders route summary, warnings and correction actions', () => {
    render(<RouteResultPanel route={route} loading={false} onAddCandidate={vi.fn()} onCorrect={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Прогулка у моря' })).toBeInTheDocument()
    expect(screen.getByText('83%')).toBeInTheDocument()
    expect(screen.getByText('Часы указаны приблизительно.')).toBeInTheDocument()
    expect(screen.getByText('Подходит под интерес прогулка')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Променад' })).toHaveAttribute(
      'src',
      'https://example.com/public-route-photo.jpg',
    )
    expect(screen.getByRole('button', { name: /Добавить место/ })).toBeInTheDocument()
  })

  it('renders no-route state without correction actions', () => {
    render(<RouteResultPanel route={{ ...route, status: 'no_route', total_places: 0, points: [] }}
      loading={false} onAddCandidate={vi.fn()} onCorrect={vi.fn()} />)
    expect(screen.getByText(/Маршрут не найден/)).toBeInTheDocument()
    expect(screen.getByText('Не удалось собрать маршрут')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Добавить место/ })).not.toBeInTheDocument()
  })
})
