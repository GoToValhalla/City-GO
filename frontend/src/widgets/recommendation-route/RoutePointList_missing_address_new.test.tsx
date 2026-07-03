/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { RecommendationRoutePoint } from '../../api/recommendations/recommendationRoute.types'
import { RoutePointList } from './RoutePointList'

const point: RecommendationRoutePoint = {
  place_id: '1',
  title: 'Музей',
  category: 'museum',
  lat: 61.0,
  lng: 69.0,
  visit_minutes: 30,
  address: 'Адрес не указан',
  has_address: false,
  display_location: 'Адрес уточняется · открыть на карте',
  navigation_url_google: 'https://www.google.com/maps/search/?api=1&query=61,69',
  navigation_url_yandex: 'https://yandex.com/maps/?pt=69,61&z=17&l=map',
  navigation_url_osm: 'https://www.openstreetmap.org/?mlat=61&mlon=69#map=17/61/69',
  scoring_breakdown: {},
}

describe('RoutePointList missing address', () => {
  it('test_route_point_missing_address_has_map_link_new', () => {
    render(<RoutePointList points={[point]} />)
    expect(screen.getByText('Адрес уточняется')).toBeInTheDocument()
    expect(screen.getByText('Открыть на карте')).toHaveAttribute('href', point.navigation_url_yandex)
  })
})
