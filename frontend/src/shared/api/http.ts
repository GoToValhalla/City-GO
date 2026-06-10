import { env } from '../config/env'

export const buildApiUrl = (path: string): string => {
  return `${env.apiBaseUrl}${path}`
}
