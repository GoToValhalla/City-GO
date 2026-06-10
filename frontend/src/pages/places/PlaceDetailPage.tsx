import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPlaceBySlug } from '../../api/places/places.api'
import { buildApiUrl } from '../../shared/api/http'
import { AppHeader } from '../../components/ui/AppHeader'
import type { PlaceDetail } from '../../entities/place/model/types'
import {
  categoryLabel,
  priceLabel,
  sourceLabel,
  timeLabel,
} from '../../shared/demo/categoryLabels'
import { imageConfidenceLabel } from '../../shared/demo/imageLabels'
import { cleanPlaceDescription, photoStateLabel, verifiedImageUrl } from '../../shared/demo/placePresentation'
import { PlaceAddressLine } from '../../shared/place/PlaceAddressLine'
import './PlaceDetailPage.css'

const boolLabel = (value: boolean | undefined): string => (value ? 'да' : 'нет')

const coordinatesLabel = (place: PlaceDetail): string => (
  place.lat && place.lng ? `${place.lat.toFixed(4)}, ${place.lng.toFixed(4)}` : 'не указаны'
)

const postJson = async (path: string, body?: Record<string, unknown>) => {
  const response = await fetch(buildApiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export const PlaceDetailPage = () => {
  const { slug } = useParams<{ slug: string }>()
  const [place, setPlace] = useState<PlaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionStatus, setActionStatus] = useState<string | null>(null)

  const loadPlace = async () => {
    if (!slug) {
      setError('Некорректный slug места')
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
  }

  useEffect(() => {
    void loadPlace()
  }, [slug])

  const runPhotoAction = async (action: 'approve' | 'reject') => {
    if (!place?.image_id) return
    try {
      setActionStatus('Сохраняю оценку фото...')
      await postJson(`/admin/place-images/${place.image_id}/${action}`, { reviewer: 'local-ui' })
      await loadPlace()
      setActionStatus(action === 'approve' ? 'Фото подтверждено' : 'Фото отклонено')
    } catch (err) {
      console.error(err)
      setActionStatus('Не удалось сохранить оценку фото')
    }
  }

  const runPlaceAction = async (action: 'exists' | 'not_found' | 'closed' | 'needs_recheck') => {
    if (!place?.id) return
    try {
      setActionStatus('Сохраняю оценку места...')
      await postJson(`/admin/place-verifications/places/${place.id}/verify`, {
        action,
        verifier: 'local-ui',
      })
      await loadPlace()
      setActionStatus('Оценка места сохранена')
    } catch (err) {
      console.error(err)
      setActionStatus('Не удалось сохранить оценку места')
    }
  }

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />
        {loading ? <section className="state-panel">Загрузка места...</section> : null}
        {error && !loading ? <section className="state-panel state-panel-error">{error}</section> : null}
        {!loading && !error && place ? (
          <main className="place-detail">
            {verifiedImageUrl(place) ? (
              <img className="place-detail-photo" src={verifiedImageUrl(place) ?? ''} alt={place.title} />
            ) : (
              <div className="place-detail-photo place-detail-photo-fallback">
                <span>{photoStateLabel(place)}</span>
                <strong>{place.title}</strong>
              </div>
            )}
            <section className="place-detail-copy">
              <Link className="section-link" to="/places">Все места</Link>
              <span className="place-chip">{categoryLabel(place.category)}</span>
              <h1>{place.title}</h1>
              <PlaceAddressLine place={place} className="place-detail-address" />
              <p className="place-detail-text">{cleanPlaceDescription(place)}</p>
              <div className="place-detail-summary">
                <strong>{timeLabel(place.open_time, place.close_time)}</strong>
                <span>{place.visit_minutes ? `${place.visit_minutes} минут на визит` : 'длительность уточняется'}</span>
                <span>{priceLabel(place.price_level)}</span>
              </div>
              <div className="place-detail-facts">
                <span>С собакой: {boolLabel(place.dog_friendly)}</span>
                <span>С семьей: {boolLabel(place.family_friendly)}</span>
                <span>В помещении: {boolLabel(place.indoor)}</span>
                <span>На улице: {boolLabel(place.outdoor)}</span>
              </div>
              <dl className="place-detail-data">
                <div><dt>Координаты</dt><dd>{coordinatesLabel(place)}</dd></div>
                <div><dt>Данные</dt><dd>{sourceLabel(place.source, place.confidence)}</dd></div>
                <div><dt>Фото</dt><dd>{photoStateLabel(place)}</dd></div>
                <div><dt>Уверенность фото</dt><dd>{imageConfidenceLabel(place.image)} / {place.image_confidence ?? '—'}</dd></div>
                <div><dt>Достоверность места</dt><dd>{place.existence_confidence_score ?? 0}% · {place.existence_confidence_level ?? 'unknown'} · {place.verification_status ?? 'unverified'}</dd></div>
              </dl>
              <div className="place-detail-actions">
                {place.image_id ? (
                  <>
                    <button type="button" onClick={() => void runPhotoAction('approve')}>Фото верное</button>
                    <button type="button" onClick={() => void runPhotoAction('reject')}>Фото неверное</button>
                  </>
                ) : null}
                <button type="button" onClick={() => void runPlaceAction('exists')}>Место есть</button>
                <button type="button" onClick={() => void runPlaceAction('not_found')}>Не нашёл</button>
                <button type="button" onClick={() => void runPlaceAction('closed')}>Закрыто</button>
                <button type="button" onClick={() => void runPlaceAction('needs_recheck')}>Проверить позже</button>
              </div>
              {actionStatus ? <p className="place-detail-action-status">{actionStatus}</p> : null}
              <Link className="hero-cta-link place-route-link" to="/routes/generate">
                Собрать маршрут
              </Link>
            </section>
          </main>
        ) : null}
      </div>
    </div>
  )
}
