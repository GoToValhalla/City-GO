import type { Map as MapLibreMap } from 'maplibre-gl'

export const addMapLayers = (map: MapLibreMap): void => {
  map.addLayer({
    id: 'place-clusters', type: 'circle', source: 'places', filter: ['has', 'point_count'],
    paint: { 'circle-color': '#0066cc', 'circle-radius': 20, 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 },
  })
  map.addLayer({
    id: 'cluster-count', type: 'symbol', source: 'places', filter: ['has', 'point_count'],
    layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 13 },
    paint: { 'text-color': '#fff' },
  })
  map.addLayer({
    id: 'route-line', type: 'line', source: 'route',
    paint: { 'line-color': '#0066cc', 'line-opacity': 0.78, 'line-width': 5 },
  })
  map.addLayer({
    id: 'place-points', type: 'circle', source: 'places', filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-color': ['case', ['get', 'closed'], '#b42318', ['get', 'visited'], '#8e8e93', '#0066cc'],
      'circle-radius': ['case', ['get', 'active'], 12, 9],
      'circle-stroke-color': '#fff', 'circle-stroke-width': ['case', ['get', 'active'], 4, 2],
    },
  })
  map.addLayer({
    id: 'point-order', type: 'symbol', source: 'places', filter: ['!', ['has', 'point_count']],
    layout: { 'text-field': ['to-string', ['get', 'order']], 'text-size': 11 },
    paint: { 'text-color': '#fff' },
  })
  map.addLayer({
    id: 'location-accuracy', type: 'circle', source: 'locations', filter: ['==', ['get', 'kind'], 'user'],
    paint: { 'circle-color': '#0066cc', 'circle-opacity': 0.12, 'circle-radius': ['min', 80, ['max', 18, ['/', ['get', 'accuracy'], 3]]] },
  })
  map.addLayer({
    id: 'locations', type: 'circle', source: 'locations',
    paint: {
      'circle-color': ['case', ['==', ['get', 'kind'], 'manual'], '#ff9500', '#0066cc'],
      'circle-radius': 8, 'circle-stroke-color': '#fff', 'circle-stroke-width': 3,
    },
  })
}
