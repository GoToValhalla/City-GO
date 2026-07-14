import '../telegram/telegramWebApp'
import type { MapManualPoint } from './mapTypes'

export const yandexMapLink = ({ latitude, longitude }: MapManualPoint): string =>
  `https://yandex.ru/maps/?pt=${longitude},${latitude}&z=16&l=map`

export const twoGisMapLink = ({ latitude, longitude }: MapManualPoint): string =>
  `https://2gis.ru/geo/${longitude}%2C${latitude}?m=${longitude}%2C${latitude}%2F16`

/** Opens an external URL safely from inside the Telegram WebApp (via
 * Telegram.WebApp.openLink so it doesn't get trapped in the in-app
 * browser), falling back to a normal new tab outside Telegram. */
export const openExternalUrl = (url: string): void => {
  const telegram = window.Telegram?.WebApp
  if (telegram?.openLink) {
    telegram.openLink(url, { try_instant_view: false })
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}
