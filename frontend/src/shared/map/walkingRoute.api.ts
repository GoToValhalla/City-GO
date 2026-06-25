import { buildApiUrl } from '../api/http'
import type { MapPoint, MapRouteState } from './mapTypes'

export type WalkingRouteStep = {
  instruction: string
  street_name: string | null
  distance_meters: number
  duration_seconds: number
}

export type WalkingRouteLeg = {
  from_index: number
  to_index: number
  distance_meters: number
  duration_seconds: number
  steps: WalkingRouteStep[]
}

type WalkingRouteResponse = {
  status: 'routed' | 'unavailable'
  provider: string
  geometry: [number, number][]
  distance_meters: number | null
  duration_seconds: number | null
  legs: WalkingRouteLeg[]
  warning: string | null
}

export const loadWalkingRoute = async (points: MapPoint[], signal: AbortSignal): Promise<MapRouteState> => {
  const response = await fetch(buildApiUrl('/routes/walking-geometry'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ points: points.map((point) => ({ lat: point.latitude, lng: point.longitude })) }),
    signal,
  })
  if (!response.ok) throw new Error(`walking route request failed: ${response.status}`)
  const payload = await response.json() as WalkingRouteResponse
  if (payload.status !== 'routed' || payload.geometry.length < 2) {
    return {
      status: 'unavailable', geometry: [], distanceMeters: null, durationSeconds: null,
      legs: [], warning: payload.warning ?? 'Пешеходный путь временно недоступен.',
    }
  }
  return {
    status: 'routed',
    geometry: payload.geometry,
    distanceMeters: payload.distance_meters,
    durationSeconds: payload.duration_seconds,
    legs: payload.legs,
    warning: null,
  }
}
