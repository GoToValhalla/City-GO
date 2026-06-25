import { useEffect, useMemo, useRef, useState } from 'react'
import type { GeoJSONSource, Map as MapInstance, MapMouseEvent } from 'maplibre-gl'
import { addMapLayers } from './mapLayers'
import { locationCollection, pointCollection, routeCollection } from './mapGeoJson'
import { mapStyle } from './mapConfig'
import type { MapManualPoint, MapPoint, MapRouteState, MapUserLocation } from './mapTypes'
import { loadWalkingRoute } from './walkingRoute.api'

type Props = {
  points: MapPoint[]
  activePointId?: number | null
  userLocation?: MapUserLocation | null
  manualPoint?: MapManualPoint | null
  routeLine?: boolean
  interactiveSelection?: boolean
  onPointSelect?: (id: number) => void
  onManualPoint?: (point: MapManualPoint) => void
  onRouteStateChange?: (state: MapRouteState) => void
  className?: string
}

const EMPTY_ROUTE: MapRouteState = {
  status: 'idle', geometry: [], distanceMeters: null, durationSeconds: null, legs: [], warning: null,
}

const source = (map: MapInstance, id: string): GeoJSONSource | null =>
  (map.getSource(id) as GeoJSONSource | undefined) ?? null

const boundsCoordinates = (points: MapPoint[], user?: MapUserLocation | null): [number, number][] => [
  ...points.map((point): [number, number] => [point.longitude, point.latitude]),
  ...(user ? [[user.longitude, user.latitude] as [number, number]] : []),
]

const cssColor = (property: string, fallback: string): string => {
  const value = getComputedStyle(document.documentElement).getPropertyValue(property).trim()
  return value || fallback
}

export const MapLibreMap = ({
  activePointId = null, className, interactiveSelection = true, manualPoint = null,
  onManualPoint, onPointSelect, onRouteStateChange, points, routeLine = false, userLocation = null,
}: Props) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapInstance | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [routeState, setRouteState] = useState<MapRouteState>(EMPTY_ROUTE)
  const routeKey = useMemo(
    () => points.map((point) => `${point.id}:${point.latitude.toFixed(6)},${point.longitude.toFixed(6)}`).join('|'),
    [points],
  )
  const dataRef = useRef({ activePointId, manualPoint, points, routeState, userLocation })
  const callbacksRef = useRef({ interactiveSelection, onManualPoint, onPointSelect, onRouteStateChange })
  dataRef.current = { activePointId, manualPoint, points, routeState, userLocation }
  callbacksRef.current = { interactiveSelection, onManualPoint, onPointSelect, onRouteStateChange }

  useEffect(() => {
    const currentPoints = dataRef.current.points
    if (!routeLine || currentPoints.length < 2) {
      setRouteState(EMPTY_ROUTE)
      callbacksRef.current.onRouteStateChange?.(EMPTY_ROUTE)
      return
    }
    const controller = new AbortController()
    const loading: MapRouteState = { ...EMPTY_ROUTE, status: 'loading' }
    setRouteState(loading)
    callbacksRef.current.onRouteStateChange?.(loading)
    loadWalkingRoute(currentPoints, controller.signal)
      .then((next) => {
        setRouteState(next)
        callbacksRef.current.onRouteStateChange?.(next)
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') return
        const unavailable: MapRouteState = {
          ...EMPTY_ROUTE,
          status: 'unavailable',
          warning: 'Пешеходный путь временно недоступен. Точки показаны без неверной прямой линии.',
        }
        setRouteState(unavailable)
        callbacksRef.current.onRouteStateChange?.(unavailable)
      })
    return () => controller.abort()
  }, [routeKey, routeLine])

  useEffect(() => {
    let disposed = false
    void import('maplibre-gl').then(({ LngLatBounds, Map, NavigationControl }) => {
      if (disposed || !containerRef.current) return
      const first = dataRef.current.points[0]
      const map = new Map({
        container: containerRef.current, style: mapStyle(),
        center: first ? [first.longitude, first.latitude] : [37.618423, 55.751244],
        zoom: first ? 12 : 4, attributionControl: { compact: true },
      })
      mapRef.current = map
      map.addControl(new NavigationControl({ showCompass: false }), 'bottom-right')
      map.on('error', () => setError('Карта временно недоступна. Список мест продолжает работать.'))
      map.on('load', () => {
        const current = dataRef.current
        map.addSource('places', { type: 'geojson', data: pointCollection(current.points, current.activePointId), cluster: true, clusterRadius: 48 })
        map.addSource('route', { type: 'geojson', data: routeCollection(current.routeState.geometry) })
        map.addSource('locations', { type: 'geojson', data: locationCollection(current.userLocation, current.manualPoint) })
        addMapLayers(map, {
          primary: cssColor('--cg-primary', '#7C4DFF'),
          closed: cssColor('--cg-closed', '#EF4444'),
          muted: cssColor('--cg-text-soft', '#6F778A'),
          text: cssColor('--cg-text-main', '#F5F7FA'),
        })
        const coords = boundsCoordinates(current.points, current.userLocation)
        if (coords.length > 1) map.fitBounds(coords.reduce((box, item) => box.extend(item), new LngLatBounds(coords[0], coords[0])), { padding: 54, maxZoom: 15 })
      })
      map.on('click', 'place-clusters', (event) => {
        const feature = event.features?.[0]
        const clusterId = Number(feature?.properties?.cluster_id)
        const coordinates = feature?.geometry.type === 'Point' ? feature.geometry.coordinates : null
        const placesSource = source(map, 'places')
        if (!Number.isFinite(clusterId) || !placesSource || !coordinates) return
        void placesSource.getClusterExpansionZoom(clusterId).then((zoom) => {
          map.easeTo({ center: [Number(coordinates[0]), Number(coordinates[1])], zoom: Math.min(zoom, 16) })
        })
      })
      map.on('click', 'place-points', (event) => {
        const id = Number(event.features?.[0]?.properties?.id)
        if (Number.isFinite(id)) callbacksRef.current.onPointSelect?.(id)
      })
      map.on('click', (event: MapMouseEvent) => {
        const callbacks = callbacksRef.current
        const hits = map.queryRenderedFeatures(event.point, { layers: ['place-points', 'place-clusters'] })
        if (callbacks.interactiveSelection && callbacks.onManualPoint && hits.length === 0) {
          callbacks.onManualPoint({ latitude: event.lngLat.lat, longitude: event.lngLat.lng })
        }
      })
      for (const layer of ['place-points', 'place-clusters']) {
        map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = '' })
      }
      const resize = () => map.resize()
      window.addEventListener('citygo:map-resize', resize)
      map.once('remove', () => window.removeEventListener('citygo:map-resize', resize))
    }).catch(() => setError('Карта недоступна на этом устройстве. Список мест продолжает работать.'))
    return () => {
      disposed = true
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map?.isStyleLoaded()) return
    source(map, 'places')?.setData(pointCollection(points, activePointId))
    source(map, 'route')?.setData(routeCollection(routeState.geometry))
    source(map, 'locations')?.setData(locationCollection(userLocation, manualPoint))
    const active = points.find((point) => point.id === activePointId)
    if (active) map.easeTo({ center: [active.longitude, active.latitude], zoom: Math.max(map.getZoom(), 14) })
  }, [activePointId, manualPoint, points, routeState, userLocation])

  return <div className={className}>
    <div className="maplibre-map" ref={containerRef} data-testid="maplibre-map" />
    {routeState.status === 'loading' ? <p className="maplibre-route-status">Строим пешеходный путь по улицам...</p> : null}
    {routeState.warning ? <p className="maplibre-route-status maplibre-route-status-warning">{routeState.warning}</p> : null}
    {error ? <p className="maplibre-map-error">{error}</p> : null}
  </div>
}
