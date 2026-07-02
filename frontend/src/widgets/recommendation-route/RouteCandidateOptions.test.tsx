import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RouteCandidateOptions } from './RouteCandidateOptions'
import type { RecommendationRoutePoint } from '../../api/recommendations/recommendationRoute.types'

const option = (index: number): RecommendationRoutePoint => ({
  place_id: String(index),
  position: index,
  title: `Place ${index}`,
  lat: 40 + index / 100,
  lng: 44 + index / 100,
  category: 'food',
  visit_minutes: 30,
})

describe('RouteCandidateOptions', () => {
  it('renders only a short visible candidate list', () => {
    render(<RouteCandidateOptions options={Array.from({ length: 20 }, (_, index) => option(index + 1))} onAdd={vi.fn()} />)

    expect(screen.getByText('12 из 20')).toBeTruthy()
    expect(screen.getByText('Place 12')).toBeTruthy()
    expect(screen.queryByText('Place 13')).toBeNull()
  })
})
