import { ExternalLink } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getPlaceBySlug } from '../../api/places/places.api'
import { PlaceDetailSheet } from '../../components/places'
import { Button } from '../../components/ui/Button'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import type { PlaceDetail } from '../../entities/place/model/types'
import { openExternalUrl, twoGisMapLink, yandexMapLink } from '../../shared/map/externalMapLinks'
import { addPlaceToTmaRoute, TmaRouteStartUnavailableError } from './tmaRouteActions'
import { TmaShell } from './TmaShell'

export const TmaPlaceDetailPage = () => {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [place, setPlace] = useState<PlaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [addStatus, setAddStatus] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!slug) { setError('Некорректный адрес места'); setLoading(false); return }
    try {
      setLoading(true)
      setError(null)
      setPlace(await getPlaceBySlug(slug))
    } catch (err) {
      console.error(err)
      setError('Не удалось загрузить место')
    } finally {
      setLoading(false)
    }
  }, [slug])

  useEffect(() => { void load() }, [load])

  const addToRoute = async () => {
    if (!place) return
    setAddStatus('Добавляем в маршрут...')
    try {
      await addPlaceToTmaRoute(place)
      setAddStatus('Место добавлено в маршрут.')
    } catch (err) {
      console.error(err)
      setAddStatus(err instanceof TmaRouteStartUnavailableError ? err.message : 'Не удалось добавить место в маршрут.')
    }
  }

  return <TmaShell title={place?.title} onBack={() => navigate('/telegram/places')}>
    {loading ? <><Skeleton /><Skeleton /></> : null}
    {error && !loading ? <ErrorState title="Место не загрузилось" description={error} retryLabel="Повторить" onRetry={load} /> : null}
    {!loading && !error && place ? (
      <>
        <PlaceDetailSheet place={place} onAddToRoute={() => void addToRoute()} backTo="/telegram/places" />
        {addStatus ? <p role="status">{addStatus}</p> : null}
        {place.lat != null && place.lng != null ? (
          <div className="tma-external-links">
            <Button variant="secondary" size="md" rightIcon={<ExternalLink size={16} />} onClick={() => openExternalUrl(yandexMapLink({ latitude: place.lat!, longitude: place.lng! }))}>Яндекс Карты</Button>
            <Button variant="ghost" size="md" rightIcon={<ExternalLink size={16} />} onClick={() => openExternalUrl(twoGisMapLink({ latitude: place.lat!, longitude: place.lng! }))}>2ГИС</Button>
          </div>
        ) : null}
      </>
    ) : null}
  </TmaShell>
}
