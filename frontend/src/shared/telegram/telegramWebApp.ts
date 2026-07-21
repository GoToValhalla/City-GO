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

export type TelegramBackButton = {
  isVisible?: boolean
  show?: () => void
  hide?: () => void
  onClick?: (callback: () => void) => void
  offClick?: (callback: () => void) => void
}

export type TelegramMainButton = {
  isVisible?: boolean
  isActive?: boolean
  isProgressVisible?: boolean
  show?: () => void
  hide?: () => void
  enable?: () => void
  disable?: () => void
  showProgress?: (leaveActive?: boolean) => void
  hideProgress?: () => void
  setText?: (text: string) => void
  onClick?: (callback: () => void) => void
  offClick?: (callback: () => void) => void
}

export type TelegramWebApp = {
  version?: string
  platform?: string
  colorScheme?: 'light' | 'dark'
  themeParams?: Record<string, string | undefined>
  initData?: string
  viewportHeight?: number
  viewportStableHeight?: number
  isActive?: boolean
  isVersionAtLeast?: (version: string) => boolean
  LocationManager?: TelegramLocationManager
  BackButton?: TelegramBackButton
  MainButton?: TelegramMainButton
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
  close?: () => void
  setHeaderColor?: (color: string) => void
  setBackgroundColor?: (color: string) => void
  openLink?: (url: string, options?: { try_instant_view?: boolean }) => void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}
