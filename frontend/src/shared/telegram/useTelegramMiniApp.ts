import { useEffect } from 'react'

type TelegramWebApp = {
  ready?: () => void
  expand?: () => void
  setHeaderColor?: (color: string) => void
  setBackgroundColor?: (color: string) => void
  MainButton?: {
    hide?: () => void
  }
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp
    }
  }
}

export const useTelegramMiniApp = () => {
  useEffect(() => {
    const webApp = window.Telegram?.WebApp
    if (!webApp) return

    webApp.ready?.()
    webApp.expand?.()
    webApp.setHeaderColor?.('#0F1117')
    webApp.setBackgroundColor?.('#0F1117')
    webApp.MainButton?.hide?.()
  }, [])
}
