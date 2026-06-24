export type LocationStatus =
  | 'idle' | 'initializing' | 'requesting' | 'granted' | 'denied'
  | 'unavailable' | 'timeout' | 'insecure' | 'error'

export type LocationSource =
  | 'telegram_native' | 'browser' | 'bot_shared' | 'manual_map' | 'city_center'

export type LocationPermissionState = PermissionState | 'unsupported' | 'unknown'

export type LocationCoordinates = {
  latitude: number
  longitude: number
  accuracy: number | null
  altitude: number | null
  course: number | null
  speed: number | null
}

export type LocationSnapshot = {
  coordinates: LocationCoordinates
  source: LocationSource
  capturedAt: number
  stale: boolean
}

export type LocationState = {
  status: LocationStatus
  snapshot: LocationSnapshot | null
  permissionState: LocationPermissionState
  retryable: boolean
  message: string
}

export type LocationScenario = 'nearby' | 'places' | 'route_navigation' | 'route_build'

export type LocationRequest = {
  scenario: LocationScenario
  allowBrowserFallback?: boolean
}

export type LocationPoint = {
  latitude: number
  longitude: number
}

export type WatchCallbacks = {
  onLocation: (snapshot: LocationSnapshot) => void
  onError: (state: LocationState) => void
}
