import { useEffect } from 'react'
import type { TelegramWebApp } from './telegramWebApp'

const EVENTS = [
  'locationManagerUpdated',
  'locationRequested',
  'viewportChanged',
  'safeAreaChanged',
  'contentSafeAreaChanged',
  'themeChanged',
  'activated',
  'deactivated',
] as const

const setPx = (name: string, value?: number): void => {
  document.documentElement.style.setProperty(name, `${Number.isFinite(value) ? value : 0}px`)
}

const applyInsets = (webApp?: TelegramWebApp): void => {
  const safe = webApp?.safeAreaInset
  const content = webApp?.contentSafeAreaInset
  setPx('--tg-safe-top', safe?.top)
  setPx('--tg-safe-right', safe?.right)
  setPx('--tg-safe-bottom', safe?.bottom)
  setPx('--tg-safe-left', safe?.left)
  setPx('--tg-content-safe-top', content?.top)
  setPx('--tg-content-safe-bottom', content?.bottom)
  setPx('--tg-viewport-height', webApp?.viewportHeight ?? window.innerHeight)
  setPx('--tg-viewport-stable-height', webApp?.viewportStableHeight ?? window.innerHeight)
}

const applyTheme = (webApp: TelegramWebApp): void => {
  const dark = webApp.colorScheme !== 'light'
  const fallback = dark ? '#0F1117' : '#F7F8FA'
  const background = webApp.themeParams?.bg_color || fallback
  const header = webApp.themeParams?.header_bg_color || background
  webApp.setHeaderColor?.(header)
  webApp.setBackgroundColor?.(background)
  document.documentElement.dataset.tmaColorScheme = dark ? 'dark' : 'light'
}

export const useTelegramMiniApp = (): void => {
  useEffect(() => {
    const root = document.documentElement
    const webApp = window.Telegram?.WebApp
    root.dataset.tmaSdk = webApp ? 'available' : 'fallback'
    root.dataset.tmaPlatform = webApp?.platform || 'web'

    const updateLayout = () => {
      applyInsets(webApp)
      if (webApp) applyTheme(webApp)
      window.dispatchEvent(new Event('citygo:map-resize'))
    }

    applyInsets(webApp)
    if (!webApp) {
      window.addEventListener('resize', updateLayout)
      window.addEventListener('orientationchange', updateLayout)
      return () => {
        window.removeEventListener('resize', updateLayout)
        window.removeEventListener('orientationchange', updateLayout)
      }
    }

    webApp.ready?.()
    webApp.expand?.()
    webApp.MainButton?.hide?.()
    webApp.MainButton?.hideProgress?.()
    updateLayout()
    EVENTS.forEach((event) => webApp.onEvent?.(event, updateLayout))
    window.addEventListener('resize', updateLayout)
    window.addEventListener('orientationchange', updateLayout)
    document.addEventListener('visibilitychange', updateLayout)

    return () => {
      EVENTS.forEach((event) => webApp.offEvent?.(event, updateLayout))
      window.removeEventListener('resize', updateLayout)
      window.removeEventListener('orientationchange', updateLayout)
      document.removeEventListener('visibilitychange', updateLayout)
    }
  }, [])
}
