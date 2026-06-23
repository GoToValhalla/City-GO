import { useMemo, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import type { GeoPoint } from '../../features/route-navigation/model/geo'
import type { RouteGeolocationStatus } from '../../features/route-navigation/model/useRouteGeolocation'
import type { NavigationPoint } from '../../features/route-navigation/model/types'

const MAP_WIDTH = 720
const MAP_HEIGHT = 420
const TILE_SIZE = 256
const MIN_ZOOM = 4
const MAX_ZOOM = 18

type Camera = {
  lat: number
  lng: number
  zoom: number
}

type ProjectedPoint = {
  worldX: number
  worldY: number
}

type ScreenPoint = {
  x: number
  y: number
}

type MapTile = {
  key: string
  href: string
  x: number
  y: number
}

type Props = {
  points: NavigationPoint[]
  currentPointId?: number
  visitedPointIds: number[]
  userLocation: GeoPoint | null
  locationStatus: RouteGeolocationStatus
  locationError: string | null
  onRequestLocation: () => void
}

const clamp = (value: number, min: number, max: number): number => Math.min(Math.max(value, min), max)

const validCoords = (point: NavigationPoint): point is NavigationPoint & { lat: number; lng: number } =>
  Number.isFinite(point.lat) && Number.isFinite(point.lng)

const lngLatToWorld = (lat: number, lng: number, zoom: number): ProjectedPoint => {
  const scale = TILE_SIZE * 2 ** zoom
  const clampedLat = clamp(lat, -85.05112878, 85.05112878)
  const sinLat = Math.sin((clampedLat * Math.PI) / 180)
  return {
    worldX: ((lng + 180) / 360) * scale,
    worldY: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale,
  }
}

const worldToLngLat = (worldX: number, worldY: number, zoom: number): Pick<Camera, 'lat' | 'lng'> => {
  const scale = TILE_SIZE * 2 ** zoom
  const lng = (worldX / scale) * 360 - 180
  const n = Math.PI - (2 * Math.PI * worldY) / scale
  const lat = (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)))
  return { lat, lng }
}

const pointToScreen = (point: ProjectedPoint, center: ProjectedPoint): ScreenPoint => ({
  x: point.worldX - center.worldX + MAP_WIDTH / 2,
  y: point.worldY - center.worldY + MAP_HEIGHT / 2,
})

const cameraForPoints = (points: NavigationPoint[]): Camera => {
  const coords = points.filter(validCoords)
  if (coords.length === 0) return { lat: 55.751244, lng: 37.618423, zoom: 12 }

  const minLat = Math.min(...coords.map((point) => point.lat))
  const maxLat = Math.max(...coords.map((point) => point.lat))
  const minLng = Math.min(...coords.map((point) => point.lng))
  const maxLng = Math.max(...coords.map((point) => point.lng))
  const lat = (minLat + maxLat) / 2
  const lng = (minLng + maxLng) / 2

  for (let zoom = MAX_ZOOM; zoom >= MIN_ZOOM; zoom -= 1) {
    const projected = coords.map((point) => lngLatToWorld(point.lat, point.lng, zoom))
    const width = Math.max(...projected.map((point) => point.worldX)) - Math.min(...projected.map((point) => point.worldX))
    const height = Math.max(...projected.map((point) => point.worldY)) - Math.min(...projected.map((point) => point.worldY))
    if (width <= MAP_WIDTH * 0.72 && height <= MAP_HEIGHT * 0.62) return { lat, lng, zoom }
  }
  return { lat, lng, zoom: MIN_ZOOM }
}

const tileUrl = (zoom: number, x: number, y: number): string => {
  const count = 2 ** zoom
  const wrappedX = ((x % count) + count) % count
  return `https://tile.openstreetmap.org/${zoom}/${wrappedX}/${y}.png`
}

const locationText: Record<RouteGeolocationStatus, string> = {
  idle: 'GPS выключен. Включите геолокацию, чтобы видеть себя на маршруте.',
  requesting: 'Запрашиваем доступ к геолокации...',
  granted: 'Геолокация включена. Карта показывает ваше положение.',
  denied: 'Геолокация запрещена. Разрешите доступ в настройках браузера.',
  unsupported: 'Этот браузер не поддерживает геолокацию.',
  unavailable: 'Геолокация временно недоступна.',
}

export const RouteMapPreview = ({
  points,
  currentPointId,
  visitedPointIds,
  userLocation,
  locationStatus,
  locationError,
  onRequestLocation,
}: Props) => {
  const routeCamera = useMemo(() => cameraForPoints(points), [points])
  const [manualCamera, setManualCamera] = useState<Camera | null>(null)
  const dragStartRef = useRef<{ x: number; y: number; center: ProjectedPoint } | null>(null)
  const camera = manualCamera ?? routeCamera
  const center = useMemo(() => lngLatToWorld(camera.lat, camera.lng, camera.zoom), [camera])
  const mapPoints = useMemo(() => points.filter(validCoords), [points])

  if (mapPoints.length === 0) {
    return (
      <div className="route-nav-map empty" data-testid="route-map-empty">
        <strong>Карта маршрута недоступна</strong>
        <span>Для карты нужны координаты точек.</span>
      </div>
    )
  }

  const screenPoints = mapPoints.map((point) => ({
    ...point,
    ...pointToScreen(lngLatToWorld(point.lat, point.lng, camera.zoom), center),
  }))
  const userScreenPoint = userLocation
    ? pointToScreen(lngLatToWorld(userLocation.lat, userLocation.lng, camera.zoom), center)
    : null
  const routeLine = screenPoints.map((point) => `${point.x},${point.y}`).join(' ')
  const tileStartX = Math.floor((center.worldX - MAP_WIDTH / 2) / TILE_SIZE)
  const tileEndX = Math.floor((center.worldX + MAP_WIDTH / 2) / TILE_SIZE)
  const tileStartY = Math.floor((center.worldY - MAP_HEIGHT / 2) / TILE_SIZE)
  const tileEndY = Math.floor((center.worldY + MAP_HEIGHT / 2) / TILE_SIZE)
  const tileCount = 2 ** camera.zoom
  const tiles: MapTile[] = []
  for (let x = tileStartX; x <= tileEndX; x += 1) {
    for (let y = tileStartY; y <= tileEndY; y += 1) {
      if (y < 0 || y >= tileCount) continue
      tiles.push({
        key: `${camera.zoom}-${x}-${y}`,
        href: tileUrl(camera.zoom, x, y),
        x: x * TILE_SIZE - (center.worldX - MAP_WIDTH / 2),
        y: y * TILE_SIZE - (center.worldY - MAP_HEIGHT / 2),
      })
    }
  }

  const recenterRoute = () => setManualCamera(null)
  const recenterUser = () => {
    if (userLocation) setManualCamera((current) => ({ ...(current ?? camera), lat: userLocation.lat, lng: userLocation.lng, zoom: Math.max((current ?? camera).zoom, 16) }))
  }
  const zoomBy = (delta: number) => setManualCamera((current) => {
    const base = current ?? camera
    return { ...base, zoom: clamp(base.zoom + delta, MIN_ZOOM, MAX_ZOOM) }
  })

  const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    dragStartRef.current = { x: event.clientX, y: event.clientY, center }
  }
  const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
    const dragStart = dragStartRef.current
    if (!dragStart) return
    setManualCamera((current) => {
      const base = current ?? camera
      const nextCenter = {
        worldX: dragStart.center.worldX - (event.clientX - dragStart.x),
        worldY: dragStart.center.worldY - (event.clientY - dragStart.y),
      }
      return { ...base, ...worldToLngLat(nextCenter.worldX, nextCenter.worldY, base.zoom) }
    })
  }
  const onPointerEnd = (event: PointerEvent<SVGSVGElement>) => {
    event.currentTarget.releasePointerCapture(event.pointerId)
    dragStartRef.current = null
  }

  return (
    <section className="route-nav-map" aria-label="Интерактивная карта маршрута" data-testid="route-map">
      <div className="route-nav-map-toolbar">
        <div>
          <strong>Карта маршрута</strong>
          <span>{mapPoints.length} точек, OSM-подложка, ручное управление и GPS.</span>
        </div>
        <div className="route-nav-map-controls" aria-label="Управление картой">
          <button type="button" onClick={() => zoomBy(1)} aria-label="Приблизить карту">+</button>
          <button type="button" onClick={() => zoomBy(-1)} aria-label="Отдалить карту">-</button>
          <button type="button" onClick={recenterRoute}>Маршрут</button>
          <button type="button" onClick={userLocation ? recenterUser : onRequestLocation}>Я на карте</button>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
        role="img"
        aria-label="Карта с точками маршрута"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerEnd}
        onPointerCancel={onPointerEnd}
      >
        <rect width={MAP_WIDTH} height={MAP_HEIGHT} className="route-nav-map-bg" />
        {tiles.map((tile) => (
          <image
            key={tile.key}
            href={tile.href}
            x={tile.x}
            y={tile.y}
            width={TILE_SIZE}
            height={TILE_SIZE}
            preserveAspectRatio="none"
          />
        ))}
        <polyline className="route-nav-line-shadow" points={routeLine} />
        <polyline className="route-nav-line" points={routeLine} data-testid="route-polyline" />
        {screenPoints.map((point) => {
          const current = currentPointId === point.place_id
          const visited = visitedPointIds.includes(point.place_id)
          return (
            <g
              key={point.place_id}
              className={`route-nav-marker${current ? ' current' : ''}${visited ? ' visited' : ''}`}
              transform={`translate(${point.x} ${point.y})`}
              data-testid={`route-marker-${point.place_id}`}
            >
              <circle r={current ? 16 : 13} />
              <text textAnchor="middle" dominantBaseline="central">{visited ? '✓' : point.navigationIndex + 1}</text>
            </g>
          )
        })}
        {userScreenPoint ? (
          <g className="route-nav-user-marker" transform={`translate(${userScreenPoint.x} ${userScreenPoint.y})`} data-testid="route-user-marker">
            {userLocation?.accuracy ? <circle r={Math.min(Math.max(userLocation.accuracy / 3, 18), 80)} className="accuracy" /> : null}
            <circle r="9" className="dot" />
          </g>
        ) : null}
      </svg>

      <div className={`route-nav-location-status ${locationStatus}`}>
        <span>{locationError || locationText[locationStatus]}</span>
        {locationStatus !== 'granted' ? <button type="button" onClick={onRequestLocation}>Включить геолокацию</button> : null}
      </div>
    </section>
  )
}
