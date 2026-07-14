import { buildApiUrl } from '../../shared/api/http'

export type PublicFeatures = {
  tma_enabled: boolean
}

export const getPublicFeatures = async (): Promise<PublicFeatures> => {
  const response = await fetch(buildApiUrl('/features/public'))
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
