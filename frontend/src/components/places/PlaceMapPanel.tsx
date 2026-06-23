import { ExternalLink, LocateFixed, MapPin } from 'lucide-react'
import type { Place } from '../../entities/place/model/types'
import type { MapCoordinate } from '../../shared/map/yandexMaps'
import { buildYandexMapUrl, buildYandexWidgetUrl, placeCoordinate, placesWithCoordinates } from '../../shared/map/yandexMaps'
import { Button } from '../ui/Button'
import { PlaceMapBottomCard } from './PlaceMapBottomCard'

type PlaceMapPanelProps = {
  places: Place[]
  activePlaceId?: number | null
  userLocation?: MapCoordinate | null
  locationLoading?: boolean
  locationError?: string | null
  onActivePlaceChange?: (placeId: number) => void
  onRequestLocation?: () => void
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const PlaceMapPanel = ({
  activePlaceId,
  className,
  locationError,
  locationLoading = false,
  onActivePlaceChange,
  onRequestLocation,
  places,
  userLocation,
}: PlaceMapPanelProps) => {
  const mappedPlaces = placesWithCoordinates(places)
  const activePlace = mappedPlaces.find((place) => place.id === activePlaceId) ?? mappedPlaces[0] ?? null
  const activeCoordinate = activePlace ? placeCoordinate(activePlace) : null
  const firstCoordinate = mappedPlaces[0] ? placeCoordinate(mappedPlaces[0]) : null
  const center = activeCoordinate ?? userLocation ?? firstCoordinate

  if (!center) {
    return (
      <section className={classNames('place-map-panel place-map-panel--empty', className)} aria-label="Карта мест">
        <div className="place-map-panel__empty-icon" aria-hidden="true"><MapPin size={22} /></div>
        <h2>Карта появится после координат</h2>
        <p>У этих мест пока нет координат. Список можно смотреть без карты.</p>
      </section>
    )
  }

  const widgetUrl = buildYandexWidgetUrl({
    center,
    places: mappedPlaces,
    activePlaceId: activePlace?.id ?? activePlaceId ?? null,
    zoom: activePlace ? 15 : 13,
  })
  const externalUrl = buildYandexMapUrl({
    center,
    places: mappedPlaces,
    activePlaceId: activePlace?.id ?? activePlaceId ?? null,
    zoom: activePlace ? 16 : 13,
  })

  return (
    <section className={classNames('place-map-panel', className)} aria-label="Карта мест">
      <div className="place-map-panel__frame">
        <iframe
          key={widgetUrl}
          title="Карта мест"
          src={widgetUrl}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          allowFullScreen
        />
      </div>

      <div className="place-map-panel__toolbar" aria-label="Действия с картой">
        {onRequestLocation ? (
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<LocateFixed size={16} />}
            loading={locationLoading}
            onClick={onRequestLocation}
          >
            Где я
          </Button>
        ) : null}
        <a href={externalUrl} target="_blank" rel="noreferrer" className="place-map-panel__external">
          <Button variant="ghost" size="sm" rightIcon={<ExternalLink size={15} />}>Открыть</Button>
        </a>
      </div>

      {locationError ? <p className="place-map-panel__error">{locationError}</p> : null}

      {activePlace ? (
        <div className="place-map-panel__bottom">
          <PlaceMapBottomCard place={activePlace} />
        </div>
      ) : null}

      <div className="place-map-panel__pins" aria-label="Быстрый выбор места">
        {mappedPlaces.slice(0, 12).map((place) => (
          <button
            className={classNames('place-map-panel__pin', place.id === activePlace?.id && 'is-active')}
            key={place.id}
            type="button"
            onClick={() => onActivePlaceChange?.(place.id)}
            aria-label={`Показать на карте: ${place.title}`}
          />
        ))}
      </div>
    </section>
  )
}
