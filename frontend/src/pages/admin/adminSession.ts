/**
 * Admin session backed by localStorage.
 * Stores only a boolean flag — API token comes from VITE_ADMIN_API_TOKEN (build variable).
 */

const SESSION_KEY = 'city_go_admin_session'

export const saveAdminSession = (): void => {
  localStorage.setItem(SESSION_KEY, '1')
}

export const clearAdminSession = (): void => {
  localStorage.removeItem(SESSION_KEY)
}

export const hasAdminSession = (): boolean => {
  return localStorage.getItem(SESSION_KEY) === '1'
}
