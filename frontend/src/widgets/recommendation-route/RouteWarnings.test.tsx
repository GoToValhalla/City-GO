// @vitest-environment jsdom

import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { RouteWarnings } from './RouteWarnings'
import type { RecommendationRouteResponse, RouteUserWarning } from '../../api/recommendations/recommendationRoute.types'

const route = (warnings: string[], userWarnings?: RouteUserWarning[]): RecommendationRouteResponse => ({
  route_id: 'route-1',
  total_places: 3,
  total_minutes: 100,
  total_estimated_minutes: 120,
  estimated_distance: 2.4,
  has_warnings: true,
  warning_count: userWarnings?.length ?? warnings.length,
  places_with_warnings: [],
  warnings,
  ...(userWarnings ? { user_warnings: userWarnings } : {}),
  points: [],
  explanation: {},
})

const userWarning = (type: string, userMessage: string, actionHint?: string): RouteUserWarning => ({
  type,
  severity: 'warning',
  user_message: userMessage,
  affected_place_ids: [],
  ...(actionHint ? { action_hint: actionHint } : {}),
})

afterEach(() => {
  cleanup()
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

  it('prefers structured user warnings over legacy raw warnings', () => {
    render(<RouteWarnings route={route(
      ['route_builder_v2_insufficient_points'],
      [userWarning('route', 'После проверки осталось мало подходящих точек.', 'Добавьте место вручную.')],
    )} />)

    expect(screen.getByText('После проверки осталось мало подходящих точек.')).toBeTruthy()
    expect(screen.getByText('Добавьте место вручную.')).toBeTruthy()
    expect(screen.queryByText('route_builder_v2_insufficient_points')).toBeNull()
  })

  it('sanitizes raw structured warning messages and raw action hints', () => {
    render(<RouteWarnings route={route(
      [],
      [userWarning('route_builder_v2_insufficient_points', 'route_builder_v2_insufficient_points', 'unknown_internal_code')],
    )} />)

    expect(screen.getByText('Маршрут пока короткий из-за качества доступных данных.')).toBeTruthy()
    expect(screen.getByText('Проверь детали мест перед прогулкой.')).toBeTruthy()
    expect(screen.queryByText('route_builder_v2_insufficient_points')).toBeNull()
    expect(screen.queryByText('unknown_internal_code')).toBeNull()
  })

  it('deduplicates repeated warning cards by message and hint', () => {
    const { container } = render(<RouteWarnings route={route(
      [],
      [
        userWarning('route', 'После проверки осталось мало подходящих точек.', 'Добавьте место вручную.'),
        userWarning('data', 'После проверки осталось мало подходящих точек.', 'Добавьте место вручную.'),
      ],
    )} />)

    const cards = container.querySelectorAll('.route-warning-card')
    expect(cards).toHaveLength(1)
    expect(within(cards[0] as HTMLElement).getByText('После проверки осталось мало подходящих точек.')).toBeTruthy()
  })

  it('limits warning cards to five items to keep mobile route UI readable', () => {
    const { container } = render(<RouteWarnings route={route(
      [],
      [
        userWarning('route', 'Предупреждение 1'),
        userWarning('data', 'Предупреждение 2'),
        userWarning('budget', 'Предупреждение 3'),
        userWarning('walk', 'Предупреждение 4'),
        userWarning('interest', 'Предупреждение 5'),
        userWarning('route', 'Предупреждение 6'),
      ],
    )} />)

    expect(container.querySelectorAll('.route-warning-card')).toHaveLength(5)
    expect(screen.getByText('Предупреждение 1')).toBeTruthy()
    expect(screen.getByText('Предупреждение 5')).toBeTruthy()
    expect(screen.queryByText('Предупреждение 6')).toBeNull()
  })

  it('renders nothing when route has no warnings', () => {
    const { container } = render(<RouteWarnings route={route([])} />)

    expect(container.textContent).toBe('')
  })
})
