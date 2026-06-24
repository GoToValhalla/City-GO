export type TelegramLocation = {
  latitude: number
  longitude: number
  horizontal_accuracy: number
  altitude: number | null
  course: number | null
  speed: number | null
}

export type TelegramLocationManager = {
  isInited: boolean
  isLocationAvailable: boolean
  isAccessRequested: boolean
  isAccessGranted: boolean
  init: (callback?: () => void) => void
  getLocation: (callback: (location: TelegramLocation | null) => void) => void
  openSettings: () => void
}

export type TelegramWebApp = {
  version?: string
  platform?: string
  isVersionAtLeast?: (version: string) => boolean
  LocationManager?: TelegramLocationManager
  onEvent?: (event: string, callback: () => void) => void
  offEvent?: (event: string, callback: () => void) => void
  safeAreaInset?: Record<string, number>
  contentSafeAreaInset?: Record<string, number>
  HapticFeedback?: {
    notificationOccurred?: (type: 'error' | 'success' | 'warning') => void
    impactOccurred?: (style: 'light' | 'medium' | 'heavy') => void
  }
  ready?: () => void
  expand?: () => void
  setHeaderColor?: (color: string) => void
  setBackgroundColor?: (color: string) => void
  MainButton?: { hide?: () => void }
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}
