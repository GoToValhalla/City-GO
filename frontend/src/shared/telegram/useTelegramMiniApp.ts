import { useEffect } from 'react'
import type { TelegramWebApp } from './telegramWebApp'

const EVENTS = [
  'locationManagerUpdated',
  'locationRequested',
  'viewportChanged',
  'safeAreaChanged',
  'contentSafeAreaChanged',
] as const

const applyInsets = (webApp: TelegramWebApp): void => {
  const root = document.documentElement
  const safe = webApp.safeAreaInset
  const content = webApp.contentSafeAreaInset
  if (safe) {
    root.style.setProperty('--tg-safe-top', `${safe.top ?? 0}px`)
    root.style.setProperty('--tg-safe-right', `${safe.right ?? 0}px`)
    root.style.setProperty('--tg-safe-bottom', `${safe.bottom ?? 0}px`)
    root.style.setProperty('--tg-safe-left', `${safe.left ?? 0}px`)
  }
  if (content) {
    root.style.setProperty('--tg-content-safe-top', `${content.top ?? 0}px`)
    root.style.setProperty('--tg-content-safe-bottom', `${content.bottom ?? 0}px`)
  }
}

export const useTelegramMiniApp = (): void => {
  useEffect(() => {
    const webApp = window.Telegram?.WebApp
    if (!webApp) return
    const updateLayout = () => {
      applyInsets(webApp)
      window.dispatchEvent(new Event('citygo:map-resize'))
    }
    webApp.ready?.()
    webApp.expand?.()
    webApp.setHeaderColor?.('#0F1117')
    webApp.setBackgroundColor?.('#0F1117')
    webApp.MainButton?.hide?.()
    applyInsets(webApp)
    EVENTS.forEach((event) => webApp.onEvent?.(event, updateLayout))
    return () => EVENTS.forEach((event) => webApp.offEvent?.(event, updateLayout))
  }, [])
}
