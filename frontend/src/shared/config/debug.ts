import { env } from './env'

const STORAGE_KEY = 'citygo.debug'
const LEGACY_STORAGE_KEY = 'city-go-debug-enabled'

const readStored = (): boolean | null => {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    const fallback = value ?? window.localStorage.getItem(LEGACY_STORAGE_KEY)
    if (fallback === null) return null
    return fallback === '1' || fallback === 'true'
  } catch { return null }
}

const store = (enabled: boolean): void => {
  try { window.localStorage.setItem(STORAGE_KEY, enabled ? 'true' : 'false') } catch { return }
}

export const syncDebugQueryFlag = (): void => {
  const url = new URL(window.location.href)
  const value = url.searchParams.get('debug')
  if (value !== '1' && value !== '0') return
  store(value === '1')
  url.searchParams.delete('debug')
  window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`)
}

export const setDebugEnabled = (enabled: boolean): void => store(enabled)

export const isDebugEnabled = (): boolean => {
  syncDebugQueryFlag()
  return readStored() ?? env.debugPanel
}
