/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { RouteDetail } from '../../api/routes/routes.api'
import { RouteNavigationView } from './RouteNavigationView'

const baseRoute = (points: RouteDetail['points']): RouteDetail => ({
  id: 42,
  city_id: 1,
  slug: 'route',
  title: 'Длинный маршрут',
  short_description: null,
  duration_minutes: 80,
  distance_km: 3.2,
  route_mode: 'walk',
  is_active: true,
  points,
})

const point = (id: number, title: string, overrides: Partial<RouteDetail['points'][number]> = {}) => ({
  place_id: id,
  position: id,
  place_title: title,
  place_slug: `p-${id}`,
  lat: 54.9 + id / 100,
  lng: 20.4 + id / 100,
  category: 'park',
  address: `Улица ${id}`,
  is_published: true,
  is_route_eligible: true,
  publication_status: 'published',
  is_active: true,
  status: 'active',
  ...overrides,
})

const renderView = (route: RouteDetail) => render(
  <MemoryRouter>
    <RouteNavigationView route={route} />
  </MemoryRouter>,
)

describe('RouteNavigationView', () => {
  const originalGeolocation = navigator.geolocation

  beforeEach(() => window.localStorage.clear())
  afterEach(() => {
    cleanup()
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: originalGeolocation,
    })
  })

  it('renders real map shell, route points and polyline', () => {
    renderView(baseRoute([point(1, 'Парк'), point(2, 'Площадь')]))
    expect(screen.getByTestId('route-map')).toBeInTheDocument()
    expect(screen.getByTestId('route-polyline')).toBeInTheDocument()
    expect(screen.getByText('Карта маршрута')).toBeInTheDocument()
    expect(screen.getByText('Парк')).toBeInTheDocument()
    expect(screen.getByText('Площадь')).toBeInTheDocument()
  })

  it('starts route and highlights current point', () => {
    renderView(baseRoute([point(1, 'Парк'), point(2, 'Площадь')]))
    fireEvent.click(screen.getByRole('button', { name: 'Начать маршрут' }))
    expect(screen.getByTestId('route-active-panel')).toHaveTextContent('Точка 1 из 2')
    expect(screen.getByTestId('route-point-card-1')).toHaveClass('current')
  })

  it('requests browser geolocation and shows user marker with distance', () => {
    const watchPosition = vi.fn((success: PositionCallback) => {
      success({
        coords: {
          latitude: 54.91,
          longitude: 20.41,
          accuracy: 12,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
        },
        timestamp: Date.now(),
      } as GeolocationPosition)
      return 7
    })
    const clearWatch = vi.fn()
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { watchPosition, clearWatch },
    })

    renderView(baseRoute([point(1, 'Парк'), point(2, 'Площадь')]))
    fireEvent.click(screen.getByRole('button', { name: 'Начать маршрут' }))

    expect(watchPosition).toHaveBeenCalled()
    expect(screen.getByTestId('route-user-marker')).toBeInTheDocument()
    expect(screen.getByTestId('route-gps-status')).toHaveTextContent('До текущей точки')
  })

  it('marks visited, moves next and completes after last point', () => {
    renderView(baseRoute([point(1, 'Парк'), point(2, 'Площадь')]))
    fireEvent.click(screen.getByRole('button', { name: 'Начать маршрут' }))
    fireEvent.click(screen.getByRole('button', { name: 'Я на месте' }))
    expect(screen.getByTestId('route-point-card-1')).toHaveClass('visited')
    expect(screen.getByTestId('route-active-panel')).toHaveTextContent('Точка 2 из 2')
    fireEvent.click(screen.getByRole('button', { name: 'Я на месте' }))
    expect(screen.getByTestId('route-completed-panel')).toHaveTextContent('Маршрут завершен')
  })

  it('next point button changes current point', () => {
    renderView(baseRoute([point(1, 'Парк'), point(2, 'Площадь')]))
    fireEvent.click(screen.getByRole('button', { name: 'Начать маршрут' }))
    fireEvent.click(screen.getByRole('button', { name: 'Следующая' }))
    expect(screen.getByTestId('route-active-panel')).toHaveTextContent('Площадь')
  })

  it('reset clears localStorage and returns preview', () => {
    renderView(baseRoute([point(1, 'Парк'), point(2, 'Площадь')]))
    fireEvent.click(screen.getByRole('button', { name: 'Начать маршрут' }))
    fireEvent.click(screen.getByRole('button', { name: 'Завершить' }))
    fireEvent.click(screen.getByRole('button', { name: 'Пройти заново' }))
    expect(screen.getByTestId('route-preview-panel')).toBeInTheDocument()
    expect(window.localStorage.getItem('citygo:route-navigation:42')).toBeNull()
  })

  it('blocks invalid route and reports bad points', () => {
    renderView(baseRoute([point(1, 'Парк'), point(2, 'Без координат', { lat: null })]))
    expect(screen.getByRole('button', { name: 'Начать маршрут' })).toBeDisabled()
    expect(screen.getAllByText(/недостаточно проверенных точек/).length).toBeGreaterThan(0)
    expect(screen.getByText('нет координат: 1')).toBeInTheDocument()
  })

  it('skips route ineligible point and keeps long title visible', () => {
    const longTitle = 'Очень длинное название точки маршрута, которое должно переноситься и оставаться в DOM'
    renderView(baseRoute([point(1, longTitle), point(2, 'Площадь'), point(3, 'Банк', { is_route_eligible: false })]))
    expect(screen.queryByTestId('route-marker-3')).not.toBeInTheDocument()
    expect(screen.getByText('исключены из маршрутов: 1')).toBeInTheDocument()
    expect(screen.getByText(longTitle)).toBeInTheDocument()
  })
})
