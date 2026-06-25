const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  useBackend: import.meta.env.VITE_USE_BACKEND === 'true',
  debugPanel: import.meta.env.VITE_DEBUG_PANEL === 'true',
}
