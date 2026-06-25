import type { WalkingRouteLeg } from './walkingRoute.api'

export type MapPoint = {
  id: number
  latitude: number
  longitude: number
  title: string
  category?: string | null
  closed?: boolean
  visited?: boolean
  order?: number
}

export type MapUserLocation = {
  latitude: number
  longitude: number
  accuracy: number | null
}

export type MapManualPoint = {
  latitude: number
  longitude: number
}

export type MapRouteState = {
  status: 'idle' | 'loading' | 'routed' | 'unavailable'
  geometry: [number, number][]
  distanceMeters: number | null
  durationSeconds: number | null
  legs: WalkingRouteLeg[]
  warning: string | null
}
