import { ArrowRight, MapPin } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Place } from '../../entities/place/model/types'
import { cityPlacePath } from '../../features/city-routing/cityPaths'
import { cityLocation } from '../../features/city-search/model/citySearch'
import { getCurrentCityCoordinates, type CityOption } from '../../shared/city/currentCity'
import { MapLibreMap } from '../../shared/map/MapLibreMap'
import type { MapManualPoint, MapPoint } from '../../shared/map/mapTypes'

type Props = { city: CityOption; places: Place[] }

const placePoints = (places: Place[]): MapPoint[] => places.flatMap((place) => {
  const latitude = Number(place.lat)
  const longitude = Number(place.lng)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return []
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || (!latitude && !longitude)) return []
  return [{ id: place.id, latitude, longitude, title: place.title, category: place.category }]
})

const cityCenter = (city: CityOption): MapManualPoint | null => {
  try {
    const coordinates = getCurrentCityCoordinates(city.slug)
    return { latitude: Number(coordinates.lat), longitude: Number(coordinates.lng) }
  } catch {
    return null
  }
}

export const HomeCityMap = ({ city, places }: Props) => {
  const points = useMemo(() => placePoints(places), [places])
  const [activePointId, setActivePointId] = useState<number | null>(points[0]?.id ?? null)
  const firstPlace = places.find((place) => place.id === (activePointId ?? points[0]?.id))

  return <aside aria-label={`Карта города ${city.name}`} className="home-hero-map">
    <MapLibreMap activePointId={activePointId} interactiveSelection={false} manualPoint={points.length ? null : cityCenter(city)} onPointSelect={setActivePointId} points={points} />
    <div className="home-map-status"><span /><b>Живая карта</b><small>{points.length} точек в кадре</small></div>
    <div className="home-map-card"><span><MapPin size={17} /></span><div><small>{cityLocation(city)}</small><strong>{firstPlace?.title ?? city.name}</strong></div>
      {firstPlace ? <Link aria-label={`Открыть ${firstPlace.title}`} to={cityPlacePath(city.slug, firstPlace.slug)}><ArrowRight size={17} /></Link> : null}
    </div>
  </aside>
}
