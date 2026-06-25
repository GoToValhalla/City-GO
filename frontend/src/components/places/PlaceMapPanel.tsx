import { ExternalLink, LocateFixed, MapPin } from 'lucide-react'
import type { Place } from '../../entities/place/model/types'
import { MapLibreMap } from '../../shared/map/MapLibreMap'
import { twoGisMapLink, yandexMapLink } from '../../shared/map/externalMapLinks'
import type { MapManualPoint, MapUserLocation } from '../../shared/map/mapTypes'
import { Button } from '../ui/Button'
import { PlaceMapBottomCard } from './PlaceMapBottomCard'
import { placeStatus } from './placeViewModel'

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
  const mapped = places.filter((place) => Number.isFinite(place.lat) && Number.isFinite(place.lng))
  const active = mapped.find((place) => place.id === activePlaceId) ?? null
  const points = mapped.map((place) => ({
    id: place.id, latitude: Number(place.lat), longitude: Number(place.lng),
    title: place.title, category: place.category, closed: placeStatus(place) === 'closed',
  }))
  const center = active
    ? { latitude: Number(active.lat), longitude: Number(active.lng) }
    : userLocation ?? manualPoint ?? (points[0] ?? null)

  if (!center) return (
    <section className={classNames('place-map-panel place-map-panel--empty', className)} aria-label="Карта мест">
      <div className="place-map-panel__empty-icon" aria-hidden="true"><MapPin size={22} /></div>
      <h2>Карта появится после координат</h2>
      <p>У этих мест пока нет координат. Список можно смотреть без карты.</p>
    </section>
  )

  return <section className={classNames('place-map-panel', active && 'place-map-panel--preview-open', className)} aria-label="Карта мест">
    <MapLibreMap className="place-map-panel__frame" points={points}
      activePointId={activePlaceId} userLocation={userLocation} manualPoint={manualPoint}
      onPointSelect={(placeId) => onActivePlaceChange?.(placeId)} onManualPoint={onManualPoint} />
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
    {active ? <div className="place-map-panel__bottom"><PlaceMapBottomCard place={active} onClose={() => onActivePlaceChange?.(null)} /></div> : null}
  </section>
}