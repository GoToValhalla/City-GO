import { ExternalLink } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getPlaceBySlug } from '../../api/places/places.api'
import { PlaceDetailSheet } from '../../components/places'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import type { PlaceDetail } from '../../entities/place/model/types'
import { openExternalUrl, twoGisMapLink, yandexMapLink } from '../../shared/map/externalMapLinks'
import { addPlaceToTmaRoute, TmaRouteAddInFlightError, TmaRouteStartUnavailableError } from './tmaRouteActions'
import { TmaShell } from './TmaShell'

export const TmaPlaceDetailPage = () => {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [place, setPlace] = useState<PlaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [addStatus, setAddStatus] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const load = useCallback(async () => {
    if (!slug) { setError('Некорректный адрес места'); setLoading(false); return }
    try {
      setLoading(true)
      setError(null)
      setPlace(await getPlaceBySlug(slug))
    } catch (err) {
      console.error(err)
      setPlace(null)
      setError('Не удалось загрузить место')
    } finally {
      setLoading(false)
    }
  }, [slug])

  useEffect(() => { void load() }, [load])

  const addToRoute = async () => {
    if (!place || adding) return
    setAdding(true)
    setAddStatus('Добавляем в маршрут…')
    try {
      await addPlaceToTmaRoute(place)
      setAddStatus('Место добавлено в маршрут.')
    } catch (err) {
      // A second concurrent tap that lost the synchronous lock in
      // addPlaceToTmaRoute -- the first call is still in flight and will
      // report its own result, so this one must not surface a false error.
      if (err instanceof TmaRouteAddInFlightError) return
      console.error(err)
      setAddStatus(err instanceof TmaRouteStartUnavailableError ? err.message : 'Не удалось добавить место в маршрут.')
    } finally {
      setAdding(false)
    }
  }

  return <TmaShell title={place?.title} onBack={() => navigate('/telegram/places')}>
    {loading ? <div role="status" aria-live="polite" aria-busy="true"><p>Загружаем место…</p><Skeleton /><Skeleton /></div> : null}
    {error && !loading ? <ErrorState title="Место не загрузилось" description={error} retryLabel="Повторить" onRetry={load} /> : null}
    {!loading && !error && !place ? <EmptyState title="Место не найдено" description="Возможно, оно было скрыто или удалено." actionLabel="К списку мест" onAction={() => navigate('/telegram/places')} /> : null}
    {!loading && !error && place ? (
      <>
        <div aria-busy={adding}>
          <PlaceDetailSheet place={place} onAddToRoute={() => void addToRoute()} backTo="/telegram/places" />
        </div>
        {addStatus ? <p role="status" aria-live="polite">{addStatus}</p> : null}
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
