import { describe, expect, it } from 'vitest'
import { emptyCopy, emptyTitle, statusLabel } from './routeResultStatusText'

describe('statusLabel', () => {
  it('honestly labels a failed/timed-out preview instead of falling back to "ready"', () => {
    expect(statusLabel('preview_failed')).toBe('Не удалось собрать маршрут')
  })

  it('labels a partial route distinctly from a ready route', () => {
    expect(statusLabel('partial_route')).toBe('Маршрут частично готов')
  })

  it('labels a no_route result distinctly from a ready route', () => {
    expect(statusLabel('no_route')).toBe('Маршрут не найден')
  })

  it('labels ready only for a genuinely successful status', () => {
    expect(statusLabel('ready')).toBe('Маршрут готов')
  })

  it('never treats a missing or unrecognized status as ready', () => {
    expect(statusLabel(undefined)).toBe('Статус маршрута неизвестен')
    expect(statusLabel(null)).toBe('Статус маршрута неизвестен')
    expect(statusLabel('some_future_status')).toBe('Статус маршрута неизвестен')
  })
})

describe('emptyTitle/emptyCopy', () => {
  it('never renders a raw technical reason code to the user', () => {
    expect(emptyTitle('route_preview_deadline_exceeded')).not.toContain('route_preview_deadline_exceeded')
    expect(emptyCopy('route_preview_deadline_exceeded')).not.toContain('route_preview_deadline_exceeded')
  })

  it('gives a specific title for a proximity-related empty reason', () => {
    expect(emptyTitle('few_candidates_near_start')).toBe('Не нашли мест поблизости')
  })
})
