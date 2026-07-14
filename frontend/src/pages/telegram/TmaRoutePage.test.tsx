/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as featuresApi from '../../api/features/publicFeatures.api'
import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { DEFAULT_CITY, setCurrentCity } from '../../shared/city/currentCity'
import { saveTmaRoute, saveTmaRouteSession } from './tmaRouteStorage'
import { TmaRoutePage } from './TmaRoutePage'

vi.mock('../../api/features/publicFeatures.api', () => ({ getPublicFeatures: vi.fn() }))
vi.mock('../../shared/map/MapLibreMap', () => ({ MapLibreMap: () => <div /> }))
vi.mock('../../shared/config/debug', () => ({ isDebugEnabled: () => false }))
vi.mock('../../api/recommendations/recommendationRoute.api', () => ({
  addPlaceToUserRoute: vi.fn(),
  correctUserRoute: vi.fn(),
  replacePlaceInUserRoute: vi.fn(),
  updateUserRouteOrder: vi.fn(),
  sendRouteFeedback: vi.fn(),
  startActiveRouteSession: vi.fn(),
  updateActiveRouteSession: vi.fn(),
  ApiRequestError: class ApiRequestError extends Error {
    status: number
    constructor(params: { status: number }) { super('HTTP error'); this.status = params.status }
  },
}))

const routeFixture = (): RecommendationRouteResponse => ({
  route_id: 'r1',
  city_slug: DEFAULT_CITY.slug,
  status: 'ready',
  total_places: 2,
  total_minutes: 60,
  total_estimated_minutes: 60,
  estimated_distance: 1,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  quality_score: 0.8,
  quality_status: 'good',
  warnings: [],
  user_warnings: [],
  points: [
    { place_id: '1', title: 'Кафе', category: 'cafe', address: 'ул. Первая', lat: 54.9, lng: 20.4, visit_minutes: 30, estimated_walk_minutes: 5 },
    { place_id: '2', title: 'Музей', category: 'museum', address: 'ул. Вторая', lat: 54.91, lng: 20.41, visit_minutes: 30, estimated_walk_minutes: 5 },
  ],
  candidate_options: [],
  explanation: { summary: 'Хороший маршрут', points: [] },
})

const sessionFixture = (): ActiveRouteSession => ({
  session_id: 1,
  route_id: 'r1',
  status: 'active',
  current_point_index: 0,
  current_place_id: '1',
  next_place_id: '2',
  point_completed_at: {},
  skipped_place_ids: [],
  points: [],
})

const renderPage = () => render(<MemoryRouter initialEntries={['/telegram/route']}><TmaRoutePage /></MemoryRouter>)

describe('TmaRoutePage', () => {
  afterEach(() => {
    cleanup()
    window.localStorage.clear()
    vi.clearAllMocks()
    setCurrentCity(DEFAULT_CITY)
  })

  it('shows the empty state when nothing is stored_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('Маршрут пока пуст')).toBeInTheDocument())
  })

  it('reopen during an active route restores both the route and the in-progress session_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    saveTmaRoute(routeFixture())
    saveTmaRouteSession(sessionFixture())

    renderPage()

    await waitFor(() => expect(screen.getByText(/Текущая точка: Кафе/)).toBeInTheDocument())
  })

  it('a route for a different city than the current one is not restored, and its session is cleared as stale_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    saveTmaRoute({ ...routeFixture(), city_slug: 'some-other-city' })
    saveTmaRouteSession(sessionFixture())

    renderPage()

    await waitFor(() => expect(screen.getByText('Маршрут пока пуст')).toBeInTheDocument())
    expect(window.localStorage.getItem('citygo:tma:activeRouteSession')).toBeNull()
  })

  it('a session for a stale/mismatched route_id is not shown as active progress_new', async () => {
    vi.mocked(featuresApi.getPublicFeatures).mockResolvedValue({ tma_enabled: true })
    saveTmaRoute(routeFixture())
    saveTmaRouteSession({ ...sessionFixture(), route_id: 'a-different-route' })

    renderPage()

    await waitFor(() => expect(screen.getByText('Маршрут ещё не начат.')).toBeInTheDocument())
  })
})
