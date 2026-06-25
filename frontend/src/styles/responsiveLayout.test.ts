import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readStyle = (name: string) => readFileSync(new URL(name, import.meta.url), 'utf-8')

describe('Адаптивная верстка для Safari и узких экранов', () => {
  it('запрещает автоматическое увеличение текста и горизонтальное расширение страницы', () => {
    const css = readStyle('../index.css')

    expect(css).toContain('-webkit-text-size-adjust: 100%')
    expect(css).toContain('overflow-x: clip')
    expect(css).toMatch(/body,\s*#root[\s\S]*min-width: 0/)
    expect(css).toMatch(/@media \(max-width: 720px\)[\s\S]*input,[\s\S]*font-size: 16px/)
  })

  it('использует safe-area и прокручиваемое меню вместо пяти сжатых колонок', () => {
    const css = readStyle('./responsive.css')

    expect(css).toContain('env(safe-area-inset-left')
    expect(css).toContain('env(safe-area-inset-right')
    expect(css).toContain('-webkit-overflow-scrolling: touch')
    expect(css).not.toContain('grid-template-columns: repeat(5')
    expect(css).toMatch(/\.nav-link\s*\{[\s\S]*min-width: 72px/)
  })

  it('ограничивает detail sheet, карты и sticky actions шириной viewport', () => {
    const css = readStyle('./mobile-safari.css')

    expect(css).toContain('@supports (-webkit-touch-callout: none)')
    expect(css).toMatch(/\.place-detail-sheet--refined[\s\S]*max-width: 100%/)
    expect(css).toMatch(/\.place-detail-sheet__footer[\s\S]*safe-area-inset-bottom/)
    expect(css).toMatch(/\.maplibre-map,[\s\S]*max-width: 100%/)
  })
})
