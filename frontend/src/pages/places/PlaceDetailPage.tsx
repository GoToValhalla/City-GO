import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPlaceBySlug } from '../../api/places/places.api'
import { PlaceDetailSheet } from '../../components/places'
import { AppHeader } from '../../components/ui/AppHeader'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import type { PlaceDetail } from '../../entities/place/model/types'
import './PlaceDetailPage.css'

export const PlaceDetailPage = () => {
  const { slug } = useParams<{ slug: string }>()
  const [place, setPlace] = useState<PlaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadPlace = useCallback(async () => {
    if (!slug) {
      setError('Некорректный адрес места')
      setLoading(false)
      return
    }

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

  useEffect(() => {
    void loadPlace()
  }, [loadPlace])

  useEffect(() => {
    if (!place || error) return undefined
    const timer = window.setInterval(() => { void loadPlace() }, 45_000)
    return () => window.clearInterval(timer)
  }, [error, loadPlace, place])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        {loading ? (
          <main className="place-detail-loading">
            <Skeleton />
            <Skeleton />
          </main>
        ) : null}

        {error && !loading ? (
          <ErrorState
            title="Место не загрузилось"
            description={error}
            retryLabel="Повторить"
            onRetry={loadPlace}
          />
        ) : null}

        {!loading && !error && place ? <PlaceDetailSheet place={place} /> : null}
      </div>
    </div>
  )
}
