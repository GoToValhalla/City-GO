import { buildApiUrl } from './http'

export type BackendVersion = {
  service: string
  version: string
  build_sha: string
  build_sha_short: string
  build_run_id: string
  build_run_number: string
  build_time: string
}

export const fetchBackendVersion = async (): Promise<BackendVersion> => {
  const response = await fetch(buildApiUrl('/version'))
  if (!response.ok) {
    throw new Error(`Backend version request failed: HTTP ${response.status}`)
  }
  return response.json()
}
