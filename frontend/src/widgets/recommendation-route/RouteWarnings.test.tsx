// @vitest-environment jsdom

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RouteWarnings } from './RouteWarnings'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

const route = (warnings: string[]): RecommendationRouteResponse => ({
  route_id: 'route-1',
  total_places: 3,
  total_minutes: 100,
  total_estimated_minutes: 120,
  estimated_distance: 2.4,
  has_warnings: true,
  warning_count: warnings.length,
  places_with_warnings: [],
  warnings,
  points: [],
  explanation: {},
})

describe('RouteWarnings', () => {
  it('shows one collapsed data nuance block without raw warning codes', () => {
    render(<RouteWarnings route={route(['route_short_due_to_low_place_density', 'some_places_have_no_photo'])} />)

    expect(screen.getByText('Есть нюансы данных')).toBeTruthy()
    expect(screen.queryByText('route_short_due_to_low_place_density')).toBeNull()
    expect(screen.queryByText('some_places_have_no_photo')).toBeNull()
    expect(screen.getByText('Маршрут пока короткий из-за качества доступных данных.')).toBeTruthy()
    expect(screen.getByText('У части мест пока нет фото.')).toBeTruthy()
  })
})
