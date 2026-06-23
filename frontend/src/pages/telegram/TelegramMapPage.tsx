import { ExternalLink, MapPin } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { ErrorState } from '../../components/ui/ErrorState'
import { buildYandexMapUrl, buildYandexWidgetUrl, type MapCoordinate } from '../../shared/map/yandexMaps'
import { useTelegramMiniApp } from '../../shared/telegram/useTelegramMiniApp'

const parseCoordinate = (value: string | null) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export const TelegramMapPage = () => {
  useTelegramMiniApp()
  const [params] = useSearchParams()
  const lat = parseCoordinate(params.get('lat'))
  const lng = parseCoordinate(params.get('lng'))
  const title = params.get('title') || 'Место'
  const address = params.get('address') || ''

  if (lat === null || lng === null) {
    return (
      <div className="telegram-map-screen">
        <ErrorState
          title="Карта недоступна"
          description="Не хватает координат места. Вернитесь к списку и выберите другую точку."
        />
        <Link className="telegram-map-back" to="/places">Смотреть места</Link>
      </div>
    )
  }

  const center: MapCoordinate = { lat, lng }

  return (
    <main className="telegram-map-screen" aria-label="Карта места">
      <section className="telegram-map-frame" aria-label={`Карта: ${title}`}>
        <iframe
          title={`Карта: ${title}`}
          src={buildYandexWidgetUrl({ center, zoom: 16 })}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          allowFullScreen
        />
      </section>

      <section className="telegram-map-sheet" aria-label="Информация о месте">
        <div className="telegram-map-pin" aria-hidden="true"><MapPin size={18} /></div>
        <div className="telegram-map-content">
          <h1>{title}</h1>
          {address ? <p>{address}</p> : null}
        </div>
        <a className="telegram-map-link" href={buildYandexMapUrl({ center, zoom: 16 })} target="_blank" rel="noreferrer">
          <Button variant="secondary" size="md" rightIcon={<ExternalLink size={16} />}>Открыть в картах</Button>
        </a>
      </section>
    </main>
  )
}