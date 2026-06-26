import { useMemo, useState } from 'react'
import { ExternalLink, LocateFixed, MapPin, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Place } from '../../entities/place/model/types'
import { MapLibreMap } from '../../shared/map/MapLibreMap'
import { twoGisMapLink, yandexMapLink } from '../../shared/map/externalMapLinks'
import type { MapManualPoint, MapUserLocation } from '../../shared/map/mapTypes'
import { Button, CategoryBadge } from '../ui'
import { PlaceMapBottomCard } from './PlaceMapBottomCard'
import { placeAddressLabel, placeStatus, placeTitle } from './placeViewModel'

type Props = {
  places: Place[]
  activePlaceId?: number | null
  userLocation?: MapUserLocation | null
  manualPoint?: MapManualPoint | null
  locationLoading?: boolean
  locationError?: string | null
  onActivePlaceChange?: (placeId: number | null) => void
  onManualPoint?: (point: MapManualPoint) => void
  onRequestLocation?: () => void
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const PlaceMapPanel = ({
  activePlaceId = null, className, locationError, locationLoading = false,
  manualPoint = null, onActivePlaceChange, onManualPoint, onRequestLocation,
  places, userLocation = null,
}: Props) => {
  const [clusterPlaceIds, setClusterPlaceIds] = useState<number[]>([])
  const mapped = useMemo(() => places.filter((place) => Number.isFinite(place.lat) && Number.isFinite(place.lng)), [places])
  const active = mapped.find((place) => place.id === activePlaceId) ?? null
  const clusterPlaces = useMemo(() => {
    const idSet = new Set(clusterPlaceIds)
    return mapped.filter((place) => idSet.has(place.id))
  }, [clusterPlaceIds, mapped])
  const points = useMemo(() => mapped.map((place) => ({
    id: place.id, latitude: Number(place.lat), longitude: Number(place.lng),
    title: place.title, category: place.category, closed: placeStatus(place) === 'closed',
  })), [mapped])
  const center = active
    ? { latitude: Number(active.lat), longitude: Number(active.lng) }
    : userLocation ?? manualPoint ?? (points[0] ?? null)

  const selectPlace = (placeId: number | null) => {
    if (placeId !== null) setClusterPlaceIds([])
    onActivePlaceChange?.(placeId)
  }

  const selectCluster = (ids: number[]) => {
    onActivePlaceChange?.(null)
    setClusterPlaceIds(ids)
  }

  if (!center) return (
    <section className={classNames('place-map-panel place-map-panel--empty', className)} aria-label="Карта мест">
      <div className="place-map-panel__empty-icon" aria-hidden="true"><MapPin size={22} /></div>
      <h2>Карта появится после координат</h2>
      <p>У этих мест пока нет координат. Список можно смотреть без карты.</p>
    </section>
  )

  return <section className={classNames('place-map-panel', (active || clusterPlaces.length > 0) && 'place-map-panel--preview-open', className)} aria-label="Карта мест">
    <MapLibreMap className="place-map-panel__frame" points={points}
      activePointId={activePlaceId} userLocation={userLocation} manualPoint={manualPoint}
      onPointSelect={(placeId) => selectPlace(placeId)} onClusterSelect={selectCluster} onManualPoint={onManualPoint} />
    <div className="place-map-panel__toolbar" aria-label="Действия с картой">
      {onRequestLocation ? <Button variant="secondary" size="sm" leftIcon={<LocateFixed size={16} />}
        loading={locationLoading} onClick={onRequestLocation}>Где я</Button> : null}
      <div className="place-map-panel__external-group">
        <a href={yandexMapLink(center)} target="_blank" rel="noreferrer"
          className="cg-button cg-button--ghost cg-button--sm place-map-panel__external">
          <span>Яндекс Карты</span><ExternalLink size={15} aria-hidden="true" />
        </a>
        <a href={twoGisMapLink(center)} target="_blank" rel="noreferrer"
          className="cg-button cg-button--ghost cg-button--sm place-map-panel__external">
          <span>2ГИС</span><ExternalLink size={15} aria-hidden="true" />
        </a>
      </div>
    </div>
    {locationError ? <p className="place-map-panel__error">{locationError}</p> : null}
    {manualPoint ? <p className="place-map-panel__manual">Выбрана точка на карте</p> : null}
    {active ? <div className="place-map-panel__bottom"><PlaceMapBottomCard place={active} onClose={() => selectPlace(null)} /></div> : null}
    {clusterPlaces.length > 0 ? (
      <div className="place-map-panel__cluster-sheet" role="dialog" aria-label="Места в выбранной группе">
        <div className="place-map-panel__cluster-head">
          <div>
            <span>Группа на карте</span>
            <strong>{clusterPlaces.length} мест</strong>
          </div>
          <button type="button" onClick={() => setClusterPlaceIds([])} aria-label="Закрыть список мест">
            <X size={18} />
          </button>
        </div>
        <div className="place-map-panel__cluster-list">
          {clusterPlaces.slice(0, 20).map((place) => {
            const title = placeTitle(place)
            const address = placeAddressLabel(place)
            return (
              <Link className="place-map-panel__cluster-item" to={`/places/${place.slug}`} key={place.id}>
                <CategoryBadge category={place.category} />
                <strong className="cg-clamp-2">{title}</strong>
                {address ? <span className="cg-clamp-1">{address}</span> : null}
              </Link>
            )
          })}
        </div>
      </div>
    ) : null}
  </section>
}
