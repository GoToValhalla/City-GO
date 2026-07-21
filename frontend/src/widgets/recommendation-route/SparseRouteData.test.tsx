/* @vitest-environment jsdom */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { RecommendationRoutePoint } from '../../api/recommendations/recommendationRoute.types'
import { RouteCandidateOptions } from './RouteCandidateOptions'
import { RoutePointList } from './RoutePointList'

const sparsePoint = {
  place_id: 'p1',
  position: 1,
  title: null,
  address: null,
  display_location: null,
  image_url: null,
  short_description: null,
  lat: Number.NaN,
  lng: Number.NaN,
  category: '',
  visit_minutes: 0,
  scoring_breakdown: {},
} as unknown as RecommendationRoutePoint

describe('sparse route data', () => {
  it('renders route point fallbacks without throwing_new', () => {
    render(<RoutePointList points={[sparsePoint]} />)
    expect(screen.getByText('Категория уточняется')).toBeInTheDocument()
    expect(screen.getByText('Местоположение уточняется')).toBeInTheDocument()
    expect(screen.getByText(/время визита уточняется/)).toBeInTheDocument()
  })

  it('renders candidate fallback values without coordinates_new', () => {
    render(<RouteCandidateOptions options={[sparsePoint]} onAdd={vi.fn()} />)
    expect(screen.getByText('Категория уточняется')).toBeInTheDocument()
    expect(screen.getAllByText('Местоположение уточняется').length).toBeGreaterThan(0)
    expect(screen.getByText(/время уточняется/)).toBeInTheDocument()
  })
})
