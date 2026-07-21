import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const source = readFileSync(fileURLToPath(new URL('./useTelegramMiniApp.ts', import.meta.url)), 'utf-8')


describe('Telegram Mini App lifecycle contract', () => {
  it('uses Telegram theme colors instead of forcing dark chrome', () => {
    expect(source).toContain("webApp.colorScheme !== 'light'")
    expect(source).toContain("themeParams?.bg_color")
    expect(source).toContain("themeParams?.header_bg_color")
    expect(source).not.toContain("setHeaderColor?.('#0F1117')")
    expect(source).not.toContain("setBackgroundColor?.('#0F1117')")
  })

  it('maintains safe areas and viewport dimensions in SDK and fallback mode', () => {
    expect(source).toContain("setPx('--tg-safe-top'")
    expect(source).toContain("setPx('--tg-content-safe-bottom'")
    expect(source).toContain("setPx('--tg-viewport-height'")
    expect(source).toContain("webApp?.viewportHeight ?? window.innerHeight")
    expect(source).toContain("root.dataset.tmaSdk = webApp ? 'available' : 'fallback'")
  })

  it('reacts to Telegram lifecycle, orientation and visibility changes', () => {
    expect(source).toContain("'themeChanged'")
    expect(source).toContain("'activated'")
    expect(source).toContain("'deactivated'")
    expect(source).toContain("window.addEventListener('orientationchange', updateLayout)")
    expect(source).toContain("document.addEventListener('visibilitychange', updateLayout)")
  })

  it('never leaves a stale Telegram MainButton visible', () => {
    expect(source).toContain('webApp.MainButton?.hide?.()')
    expect(source).toContain('webApp.MainButton?.hideProgress?.()')
  })
})
