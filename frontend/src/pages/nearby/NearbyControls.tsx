import { Badge } from '../../components/ui/Badge'

type Props = {
  lat: number | null
  lng: number | null
  locating: boolean
  locationLabel: string
  radiusKm: number
  radiusOptions: number[]
  onRadius: (value: number) => void
  onUseLocation: () => void
}

export const NearbyControls = ({
  lat,
  lng,
  locating,
  locationLabel,
  radiusKm,
  radiusOptions,
  onRadius,
  onUseLocation,
}: Props) => (
  <>
    <div className="discovery-stats">
      <Badge variant="brand">{locationLabel}</Badge>
      <span>{lat !== null && lng !== null ? `${lat}, ${lng}` : 'координаты не заданы'}</span>
      <span>радиус {radiusKm} км</span>
    </div>
    <div className="nearby-controls">
      {radiusOptions.map((value) => (
        <button className={value === radiusKm ? 'is-active' : ''}
          key={value} type="button" onClick={() => onRadius(value)}>
          {value} км
        </button>
      ))}
      <button type="button" onClick={onUseLocation} disabled={locating}>
        {locating ? 'Определяем...' : 'Моя геолокация'}
      </button>
    </div>
  </>
)
