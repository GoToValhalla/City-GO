const numberFromEnv = (value: string | undefined, fallback: number): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export const LOCATION_TTL_MS = numberFromEnv(
  import.meta.env.VITE_LOCATION_TTL_SECONDS,
  900,
) * 1000

export const LOCATION_STALE_MS = Math.min(120_000, LOCATION_TTL_MS)

export const ONE_SHOT_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  maximumAge: 60_000,
  timeout: 10_000,
}

export const WATCH_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  maximumAge: 5_000,
  timeout: 12_000,
}

export const isSecureLocationContext = (): boolean => {
  if (window.isSecureContext) return true
  return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
}
