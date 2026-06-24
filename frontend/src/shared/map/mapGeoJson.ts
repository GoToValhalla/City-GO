import type { Feature, FeatureCollection, LineString, Point } from 'geojson'
import type { MapManualPoint, MapPoint, MapUserLocation } from './mapTypes'

export const pointCollection = (points: MapPoint[], activeId: number | null): FeatureCollection<Point> => ({
  type: 'FeatureCollection',
  features: points.map((point): Feature<Point> => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [point.longitude, point.latitude] },
    properties: {
      active: point.id === activeId,
      category: point.category ?? 'place',
      closed: Boolean(point.closed),
      id: point.id,
      order: point.order ?? '',
      title: point.title,
      visited: Boolean(point.visited),
    },
  })),
})

export const routeCollection = (points: MapPoint[]): FeatureCollection<LineString> => ({
  type: 'FeatureCollection',
  features: points.length > 1 ? [{
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'LineString',
      coordinates: points.map((point) => [point.longitude, point.latitude]),
    },
  }] : [],
})

export const locationCollection = (
  user: MapUserLocation | null,
  manual: MapManualPoint | null,
): FeatureCollection<Point> => ({
  type: 'FeatureCollection',
  features: [
    ...(user ? [{
      type: 'Feature' as const,
      properties: { accuracy: user.accuracy ?? 0, kind: 'user' },
      geometry: { type: 'Point' as const, coordinates: [user.longitude, user.latitude] },
    }] : []),
    ...(manual ? [{
      type: 'Feature' as const,
      properties: { accuracy: 0, kind: 'manual' },
      geometry: { type: 'Point' as const, coordinates: [manual.longitude, manual.latitude] },
    }] : []),
  ],
})
