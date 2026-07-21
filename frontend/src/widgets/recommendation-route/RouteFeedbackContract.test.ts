import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const panelSource = readFileSync(fileURLToPath(new URL('./RouteResultPanel.tsx', import.meta.url)), 'utf-8')
const apiSource = readFileSync(fileURLToPath(new URL('../../api/recommendations/recommendationRoute.api.ts', import.meta.url)), 'utf-8')


describe('route feedback public/TMA contract', () => {
  it('prevents duplicate submit after a successful request but keeps retry after failure', () => {
    expect(panelSource).toContain('const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)')
    expect(panelSource).toContain('feedbackPending || feedbackSubmitted || feedbackReasonRequired')
    expect(panelSource).toContain('setFeedbackSubmitted(true)')
    expect(panelSource).not.toMatch(/catch \(error\)[\s\S]*?setFeedbackSubmitted\(true\)/)
  })

  it('requires a concrete reason for a low route rating', () => {
    expect(panelSource).toContain('rating <= 3 && feedbackProblems.length === 0')
    expect(panelSource).toContain('Выберите, что именно не подошло.')
  })

  it('uses the same sanitized feedback UI on public web and TMA', () => {
    expect(panelSource).toContain("await sendRouteFeedback(route, rating, feedbackComment, feedbackProblems)")
    expect(apiSource).toContain("window.location.pathname.startsWith('/telegram')")
    expect(apiSource).toContain("? 'telegram' : 'web'")
    expect(apiSource).toContain("comment?.trim().slice(0, 1000) || null")
  })

  it('keeps technical diagnostics behind the explicit debug gate', () => {
    expect(panelSource).toContain('{debug ? <DiagnosticsPanel')
    expect(panelSource).toContain('{debug ? <RouteDebugTrace')
    expect(panelSource).not.toContain('responseBody')
    expect(panelSource).not.toContain('stack_trace')
  })
})
