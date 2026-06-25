import { env } from './env'

const STORAGE_KEY = 'city-go-debug-enabled'

const readStored = (): boolean | null => {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    if (value === null) return null
    return value === '1'
  } catch {
    return null
  }
}

const store = (enabled: boolean): void => {
  try { window.localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0') } catch { return }
}

export const syncDebugQueryFlag = (): void => {
  const value = new URLSearchParams(window.location.search).get('debug')
  if (value === '1') store(true)
  if (value === '0') store(false)
}

export const setDebugEnabled = (enabled: boolean): void => store(enabled)

export const isDebugEnabled = (): boolean => {
  syncDebugQueryFlag()
  return readStored() ?? env.debugPanel
}
