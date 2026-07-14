import { useEffect } from 'react'

export const useTelegramBackButton = (onBack: (() => void) | null): void => {
  useEffect(() => {
    const backButton = window.Telegram?.WebApp?.BackButton
    if (!backButton || !onBack) return undefined
    backButton.show?.()
    backButton.onClick?.(onBack)
    return () => {
      backButton.offClick?.(onBack)
      backButton.hide?.()
    }
  }, [onBack])
}
