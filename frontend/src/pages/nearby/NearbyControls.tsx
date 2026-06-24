import { Badge } from '../../components/ui/Badge'
import type { LocationStatus } from '../../shared/location/types'

type Props = {
  status: LocationStatus
  message: string
  source: 'city_center' | 'device' | 'manual'
  radiusKm: number
  radiusOptions: number[]
  onRadius: (value: number) => void
  onUseLocation: () => void
  onUseCenter: () => void
  onOpenSettings: () => void
}

const SOURCE_LABELS = {
  city_center: 'Используем центр города',
  device: 'Текущее местоположение',
  manual: 'Точка выбрана на карте',
}

export const NearbyControls = ({
  message, onOpenSettings, onRadius, onUseCenter, onUseLocation,
  radiusKm, radiusOptions, source, status,
}: Props) => <div className="nearby-location-panel">
  <div className="discovery-stats">
    <Badge variant="brand">{SOURCE_LABELS[source]}</Badge>
    <span>Радиус {radiusKm} км</span>
    {status !== 'idle' && status !== 'granted' ? <span>{message}</span> : null}
  </div>
  <p>Координаты нужны только для поиска рядом и временно хранятся на этом устройстве.</p>
  <div className="nearby-controls">
    {radiusOptions.map((value) => <button className={value === radiusKm ? 'is-active' : ''}
      key={value} type="button" onClick={() => onRadius(value)}>{value} км</button>)}
    <button type="button" onClick={onUseLocation} disabled={status === 'requesting'}>
      {status === 'requesting' ? 'Определяем...' : 'Моя геопозиция'}
    </button>
    <button type="button" onClick={onUseCenter}>Центр города</button>
    {status === 'denied' ? <button type="button" onClick={onOpenSettings}>Открыть настройки Telegram</button> : null}
  </div>
  <p className="places-muted">Чтобы выбрать точку вручную, нажмите на свободное место карты.</p>
</div>
