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
