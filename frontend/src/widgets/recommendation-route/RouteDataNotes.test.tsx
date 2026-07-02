import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RouteDataNotes } from './RouteDataNotes'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

const route = (notes: string[]): RecommendationRouteResponse => ({
  route_id: 'r1',
  total_places: 1,
  total_minutes: 10,
  total_estimated_minutes: 10,
  estimated_distance: 1,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  warnings: [],
  points: [],
  explanation: { data_notes: notes },
})

describe('RouteDataNotes', () => {
  it('hides raw technical route codes', () => {
    render(<RouteDataNotes route={route(['route_has_long_walk_segments', 'У части мест пока нет фото.'])} />)

    expect(screen.queryByText('route_has_long_walk_segments')).toBeNull()
    expect(screen.getByText('У части мест пока нет фото.')).toBeTruthy()
  })
})
