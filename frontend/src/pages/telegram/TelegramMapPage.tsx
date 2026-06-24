import { ExternalLink, MapPin } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { ErrorState } from '../../components/ui/ErrorState'
import { MapLibreMap } from '../../shared/map/MapLibreMap'
import { twoGisMapLink, yandexMapLink } from '../../shared/map/externalMapLinks'
import { useTelegramMiniApp } from '../../shared/telegram/useTelegramMiniApp'

const coordinate = (value: string | null, min: number, max: number): number | null => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= min && parsed <= max ? parsed : null
}

export const TelegramMapPage = () => {
  useTelegramMiniApp()
  const [params] = useSearchParams()
  const lat = coordinate(params.get('lat'), -90, 90)
  const lng = coordinate(params.get('lng'), -180, 180)
  const title = params.get('title') || 'Место'
  const address = params.get('address') || ''

  if (lat === null || lng === null || (lat === 0 && lng === 0)) return <div className="telegram-map-screen">
    <ErrorState title="Карта недоступна"
      description="Не хватает координат места. Вернитесь к списку и выберите другую точку." />
    <Link className="telegram-map-back" to="/places">Смотреть места</Link>
  </div>

  const point = { latitude: lat, longitude: lng }
  return <main className="telegram-map-screen" aria-label="Карта места">
    <section className="telegram-map-frame" aria-label={`Карта: ${title}`}>
      <MapLibreMap points={[{ id: 1, ...point, title }]} interactiveSelection={false} />
    </section>
    <section className="telegram-map-sheet" aria-label="Информация о месте">
      <div className="telegram-map-pin" aria-hidden="true"><MapPin size={18} /></div>
      <div className="telegram-map-content"><h1>{title}</h1>{address ? <p>{address}</p> : null}</div>
      <div className="telegram-map-links">
        <a href={yandexMapLink(point)} target="_blank" rel="noreferrer">
          <Button variant="secondary" size="md" rightIcon={<ExternalLink size={16} />}>Яндекс Карты</Button>
        </a>
        <a href={twoGisMapLink(point)} target="_blank" rel="noreferrer">
          <Button variant="ghost" size="md" rightIcon={<ExternalLink size={16} />}>2ГИС</Button>
        </a>
      </div>
    </section>
  </main>
}
