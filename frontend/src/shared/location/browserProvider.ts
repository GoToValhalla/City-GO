import { isSecureLocationContext, ONE_SHOT_OPTIONS, WATCH_OPTIONS } from './config'
import { browserErrorState, locationState } from './messages'
import { browserSnapshot } from './snapshot'
import type { LocationPermissionState, LocationSnapshot, LocationState, WatchCallbacks } from './types'

export const browserPermission = async (): Promise<LocationPermissionState> => {
  if (!navigator.permissions?.query) return 'unsupported'
  try {
    return (await navigator.permissions.query({ name: 'geolocation' })).state
  } catch {
    return 'unsupported'
  }
}

export const requestBrowserLocation = async (): Promise<LocationSnapshot | LocationState> => {
  if (!isSecureLocationContext()) return locationState('insecure')
  if (!navigator.geolocation) return locationState('unavailable', 'unsupported')
  const permission = await browserPermission()
  return new Promise<LocationSnapshot | LocationState>((resolve) => navigator.geolocation.getCurrentPosition(
    (position) => resolve(browserSnapshot(position)),
    (error) => resolve(browserErrorState(error)),
    ONE_SHOT_OPTIONS,
  )).then((result) => (
    'coordinates' in result ? result : { ...result, permissionState: permission }
  ))
}

export const startBrowserWatch = (callbacks: WatchCallbacks): number | null => {
  if (!isSecureLocationContext()) {
    callbacks.onError(locationState('insecure'))
    return null
  }
  if (!navigator.geolocation) {
    callbacks.onError(locationState('unavailable', 'unsupported'))
    return null
  }
  return navigator.geolocation.watchPosition(
    (position) => callbacks.onLocation(browserSnapshot(position)),
    (error) => callbacks.onError(browserErrorState(error)),
    WATCH_OPTIONS,
  )
}

export const stopBrowserWatch = (watchId: number | null): void => {
  if (watchId !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId)
}
