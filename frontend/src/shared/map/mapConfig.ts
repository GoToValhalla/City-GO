import type { StyleSpecification } from 'maplibre-gl'

const DEFAULT_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const DEFAULT_ATTRIBUTION = '© OpenStreetMap contributors'

export const mapStyle = (): string | StyleSpecification => {
  const styleUrl = import.meta.env.VITE_MAP_STYLE_URL?.trim()
  if (styleUrl) return styleUrl
  return {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: [import.meta.env.VITE_MAP_TILE_URL?.trim() || DEFAULT_TILE_URL],
        tileSize: 256,
        attribution: import.meta.env.VITE_MAP_ATTRIBUTION?.trim() || DEFAULT_ATTRIBUTION,
      },
    },
    layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
  }
}
