import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const source = readFileSync(fileURLToPath(new URL('./TmaRoutePage.tsx', import.meta.url)), 'utf-8')

describe('TMA route mutation orchestration', () => {
  it('uses lazy mutation factories so loading guard runs before the API request starts', () => {
    expect(source).toContain('type RouteMutation = () => Promise<RecommendationRouteResponse>')
    expect(source).toContain('const next = await operation()')
    expect(source).toContain("apply(() => addPlaceToUserRoute")
    expect(source).toContain("apply(() => updateUserRouteOrder")
    expect(source).toContain("apply(() => replacePlaceInUserRoute")
    expect(source).not.toContain('apply(addPlaceToUserRoute')
    expect(source).not.toContain('apply(updateUserRouteOrder')
    expect(source).not.toContain('apply(replacePlaceInUserRoute')
  })

  it('never converts a failed replacement lookup into a destructive remove mutation', () => {
    expect(source).toContain('Для этой точки сейчас нет подходящей замены')
    expect(source).toMatch(/if \(!candidate\) \{[\s\S]*?setError\([\s\S]*?return\s*\}/)
    expect(source).not.toMatch(/if \(!candidate\) \{[\s\S]*?correct\('remove_place'/)
  })

  it('keeps the current session state synchronized with persistence and route changes', () => {
    expect(source).toContain('setActiveSession(session)')
    expect(source).toContain('activeSession.route_id !== next.route_id')
    expect(source).toContain('setActiveSession(null)')
  })

  it('provides explicit pending and success feedback for route mutations', () => {
    expect(source).toContain("'Меняем порядок точек…', 'Порядок точек обновлён.'")
    expect(source).toContain("'Подбираем замену…', 'Точка заменена.'")
    expect(source).toContain("'Добавляем место…', 'Место добавлено в маршрут.'")
  })
})
