/**
 * Admin Bearer token из build-time переменной VITE_ADMIN_API_TOKEN.
 * Не хранить токен в исходниках — только в .env.local / CI secret / Docker build-arg.
 */

const TOKEN_PLACEHOLDER = 'CHANGE_ME_ADMIN_API_TOKEN'

export const getAdminApiToken = (): string => {
  const raw = import.meta.env.VITE_ADMIN_API_TOKEN ?? ''
  if (!raw || raw === TOKEN_PLACEHOLDER) {
    return ''
  }
  return raw
}

export const requireAdminApiToken = (): string => {
  const token = getAdminApiToken()
  if (!token) {
    throw new Error(
      'VITE_ADMIN_API_TOKEN не настроен. Задайте build variable при сборке frontend.',
    )
  }
  return token
}
