import type { TelegramLocationManager, TelegramWebApp } from '../telegram/telegramWebApp'
import { locationState } from './messages'
import { createSnapshot, validCoordinate } from './snapshot'
import type { LocationSnapshot, LocationState } from './types'

const managerFor = (webApp?: TelegramWebApp): TelegramLocationManager | null => {
  if (!webApp?.isVersionAtLeast?.('8.0')) return null
  return webApp.LocationManager ?? null
}

const initManager = (manager: TelegramLocationManager): Promise<void> => {
  if (manager.isInited) return Promise.resolve()
  return new Promise((resolve) => manager.init(resolve))
}

export const requestTelegramLocation = async (
  webApp = window.Telegram?.WebApp,
): Promise<LocationSnapshot | LocationState> => {
  const manager = managerFor(webApp)
  if (!manager) return locationState('unavailable', 'unsupported')
  await initManager(manager)
  if (!manager.isLocationAvailable) return locationState('unavailable', 'unsupported')
  return new Promise((resolve) => manager.getLocation((location) => {
    if (!location) {
      webApp?.HapticFeedback?.notificationOccurred?.('error')
      resolve(locationState(
        manager.isAccessRequested && !manager.isAccessGranted ? 'denied' : 'unavailable',
        manager.isAccessGranted ? 'granted' : 'denied',
        manager.isAccessGranted
          ? 'Геопозиция сейчас недоступна'
          : 'Геопозиция отключена в настройках Telegram',
      ))
      return
    }
    if (!validCoordinate(location.latitude, location.longitude)) {
      resolve(locationState('error'))
      return
    }
    webApp?.HapticFeedback?.notificationOccurred?.('success')
    resolve(createSnapshot({
      accuracy: location.horizontal_accuracy,
      altitude: location.altitude,
      course: location.course,
      latitude: location.latitude,
      longitude: location.longitude,
      speed: location.speed,
    }, 'telegram_native'))
  }))
}

export const openTelegramLocationSettings = (): boolean => {
  const manager = managerFor(window.Telegram?.WebApp)
  if (!manager?.isInited || !manager.isLocationAvailable) return false
  manager.openSettings()
  return true
}
