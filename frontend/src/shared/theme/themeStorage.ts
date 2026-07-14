import '../telegram/telegramWebApp'

export type ThemeMode = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'citygo:themeMode'
const CHANGE_EVENT = 'citygo:theme-changed'
const MODES: ThemeMode[] = ['system', 'light', 'dark']

const isThemeMode = (value: unknown): value is ThemeMode => typeof value === 'string' && (MODES as string[]).includes(value)

export const getStoredThemeMode = (): ThemeMode => {
  if (typeof window === 'undefined') return 'system'

  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    return isThemeMode(saved) ? saved : 'system'
  } catch {
    return 'system'
  }
}

export const setStoredThemeMode = (mode: ThemeMode): void => {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    // localStorage unavailable (private mode, quota, disabled) — theme still
    // applies for this session via in-memory React state, just not persisted.
  }

  window.dispatchEvent(new CustomEvent<ThemeMode>(CHANGE_EVENT, { detail: mode }))
}

export const getSystemPrefersDark = (): boolean => {
  if (typeof window === 'undefined') return false
  const telegramScheme = window.Telegram?.WebApp?.colorScheme
  if (telegramScheme === 'dark' || telegramScheme === 'light') return telegramScheme === 'dark'
  if (typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export const resolveTheme = (mode: ThemeMode, systemPrefersDark: boolean): ResolvedTheme => {
  if (mode === 'system') return systemPrefersDark ? 'dark' : 'light'
  return mode
}

export const THEME_STORAGE_KEY = STORAGE_KEY
export const THEME_CHANGE_EVENT = CHANGE_EVENT
