import { useCallback, useEffect, useState } from 'react'
import {
  getStoredThemeMode,
  getSystemPrefersDark,
  resolveTheme,
  setStoredThemeMode,
  THEME_CHANGE_EVENT,
  type ThemeMode,
} from './themeStorage'

const applyResolvedTheme = (mode: ThemeMode): void => {
  if (typeof document === 'undefined') return
  const resolved = resolveTheme(mode, getSystemPrefersDark())
  document.documentElement.setAttribute('data-theme', resolved)
}

export const useTheme = () => {
  const [mode, setMode] = useState<ThemeMode>(() => getStoredThemeMode())

  useEffect(() => {
    applyResolvedTheme(mode)
  }, [mode])

  useEffect(() => {
    const sync = (event: Event) => {
      const detail = (event as CustomEvent<ThemeMode>).detail
      if (detail) setMode(detail)
    }
    window.addEventListener(THEME_CHANGE_EVENT, sync)
    return () => window.removeEventListener(THEME_CHANGE_EVENT, sync)
  }, [])

  useEffect(() => {
    if (mode !== 'system' || typeof window.matchMedia !== 'function') return
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => applyResolvedTheme('system')
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [mode])

  const setThemeMode = useCallback((next: ThemeMode) => {
    setMode(next)
    setStoredThemeMode(next)
  }, [])

  return { mode, setThemeMode }
}
